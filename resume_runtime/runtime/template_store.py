from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

_ALLOWED_SCOPES = {"user", "candidate"}
_TEMPLATE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class TemplateStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _validate_scope(self, scope: str) -> str:
        if scope not in _ALLOWED_SCOPES:
            raise ValueError(f"Unsupported template scope: {scope}")
        return scope

    def _validate_template_id(self, template_id: str) -> str:
        if not isinstance(template_id, str) or not template_id:
            raise ValueError("templateId must be a non-empty string")
        if template_id in {".", ".."} or not _TEMPLATE_ID_PATTERN.fullmatch(template_id):
            raise ValueError(f"Unsafe templateId: {template_id}")
        if Path(template_id).name != template_id:
            raise ValueError(f"Unsafe templateId: {template_id}")
        return template_id

    def _scope_dir(self, scope: str) -> Path:
        return self.root / self._validate_scope(scope)

    def _template_dir(self, scope: str, template_id: str) -> Path:
        return self._scope_dir(scope) / self._validate_template_id(template_id)

    def _write_package(
        self,
        template_dir: Path,
        *,
        manifest: dict[str, Any],
        markdown: str,
        html: str,
        css: str,
    ) -> None:
        (template_dir / "template.md").write_text(markdown, encoding="utf-8")
        (template_dir / "template.html").write_text(html, encoding="utf-8")
        (template_dir / "style.css").write_text(css, encoding="utf-8")
        (template_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    def _install_staged_directory(self, staging_dir: Path, target_dir: Path) -> None:
        backup_dir: Path | None = None
        try:
            if target_dir.exists():
                backup_dir = target_dir.with_name(f".{target_dir.name}.backup")
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
                shutil.move(str(target_dir), str(backup_dir))
            shutil.move(str(staging_dir), str(target_dir))
        except Exception:
            if backup_dir is not None and backup_dir.exists() and not target_dir.exists():
                shutil.move(str(backup_dir), str(target_dir))
            raise
        else:
            if backup_dir is not None and backup_dir.exists():
                shutil.rmtree(backup_dir)

    def save(
        self,
        *,
        scope: str,
        manifest: dict[str, Any],
        markdown: str,
        html: str,
        css: str,
    ) -> Path:
        template_dir = self._template_dir(scope, manifest["templateId"])
        template_dir.parent.mkdir(parents=True, exist_ok=True)

        stored_manifest = dict(manifest)
        stored_manifest["storageScope"] = self._validate_scope(scope)

        with tempfile.TemporaryDirectory(dir=template_dir.parent, prefix=f".{template_dir.name}.") as temp_dir:
            staging_dir = Path(temp_dir) / template_dir.name
            staging_dir.mkdir()
            self._write_package(
                staging_dir,
                manifest=stored_manifest,
                markdown=markdown,
                html=html,
                css=css,
            )
            self._install_staged_directory(staging_dir, template_dir)
        return template_dir / "manifest.json"

    def promote(self, template_id: str) -> Path:
        source_dir = self._template_dir("user", template_id)
        manifest_path = source_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        target_dir = self._template_dir("candidate", template_id)
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        promoted_manifest = dict(manifest)
        promoted_manifest["storageScope"] = "candidate"

        with tempfile.TemporaryDirectory(dir=target_dir.parent, prefix=f".{target_dir.name}.") as temp_dir:
            staging_dir = Path(temp_dir) / target_dir.name
            shutil.copytree(source_dir, staging_dir)
            self._write_package(
                staging_dir,
                manifest=promoted_manifest,
                markdown=(source_dir / "template.md").read_text(encoding="utf-8"),
                html=(source_dir / "template.html").read_text(encoding="utf-8"),
                css=(source_dir / "style.css").read_text(encoding="utf-8"),
            )
            self._install_staged_directory(staging_dir, target_dir)

        shutil.rmtree(source_dir)
        return target_dir / "manifest.json"
