from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from resume_runtime.runtime.artifact_builders import derive_guided_intake_checklist


@dataclass(frozen=True)
class TemplateCard:
    templateId: str
    version: str
    target: str
    title: str
    styleLabel: str
    useCases: list[str]
    requiredContentSummary: list[str]
    storageScope: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.templateId,
            "version": self.version,
            "target": self.target,
            "title": self.title,
            "style_label": self.styleLabel,
            "use_cases": list(self.useCases),
            "required_content_summary": list(self.requiredContentSummary),
            "storage_scope": self.storageScope,
        }


@dataclass(frozen=True)
class TemplateCatalogEntry:
    templateId: str
    version: str
    manifestPath: Path
    manifest: dict[str, Any]
    checklist: dict[str, Any]
    card: TemplateCard

    @property
    def template_context(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest,
            "checklist": self.checklist,
        }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_card(manifest: dict[str, Any]) -> TemplateCard:
    preview_card = manifest["previewCard"]
    return TemplateCard(
        templateId=manifest["templateId"],
        version=manifest["version"],
        target=manifest["target"],
        title=preview_card["title"],
        styleLabel=preview_card["styleLabel"],
        useCases=list(preview_card["useCases"]),
        requiredContentSummary=list(preview_card["requiredContentSummary"]),
        storageScope=manifest["storageScope"],
    )


def _entry_key(entry: TemplateCatalogEntry) -> tuple[str, str]:
    return (entry.templateId, entry.version)


def _reject_duplicate_entries(entries: list[TemplateCatalogEntry]) -> None:
    seen: dict[tuple[str, str], Path] = {}
    for entry in entries:
        key = _entry_key(entry)
        if key in seen:
            raise ValueError(
                "Duplicate template catalog entry for "
                f"templateId={entry.templateId!r}, version={entry.version!r}: "
                f"{seen[key]} and {entry.manifestPath}"
            )
        seen[key] = entry.manifestPath


def _build_manifest_index(manifest_paths: list[Path]) -> dict[tuple[str, str], tuple[Path, dict[str, Any]]]:
    manifest_index: dict[tuple[str, str], tuple[Path, dict[str, Any]]] = {}
    for path in manifest_paths:
        manifest = load_json(path)
        key = (manifest["templateId"], manifest["version"])
        if key in manifest_index:
            duplicate_path, _ = manifest_index[key]
            raise ValueError(
                "Duplicate example template manifest for "
                f"templateId={manifest['templateId']!r}, version={manifest['version']!r}: "
                f"{duplicate_path} and {path}"
            )
        manifest_index[key] = (path, manifest)
    return manifest_index


def load_template_catalog(
    *,
    examples_root: Path,
    generated_at: str,
    template_store_root: Path | None = None,
) -> list[TemplateCatalogEntry]:
    examples_root = Path(examples_root)
    registry = load_json(examples_root / "template-registry.v1.json")
    manifest_paths = sorted((examples_root / "templates").glob("*.json"))
    manifest_index = _build_manifest_index(manifest_paths)
    entries: list[TemplateCatalogEntry] = []
    for registry_entry in registry["entries"]:
        key = (registry_entry["templateId"], registry_entry["version"])
        manifest_path, manifest = manifest_index[key]
        checklist = derive_guided_intake_checklist(manifest, generated_at=generated_at)
        card = _build_card(manifest)
        entries.append(
            TemplateCatalogEntry(
                templateId=manifest["templateId"],
                version=manifest["version"],
                manifestPath=manifest_path,
                manifest=manifest,
                checklist=checklist,
                card=card,
            )
        )
    if template_store_root is not None:
        entries.extend(
            load_stored_template_entries(
                template_store_root,
                generated_at=generated_at,
            )
        )
    _reject_duplicate_entries(entries)
    return entries


def load_stored_template_entries(
    template_store_root: Path,
    *,
    generated_at: str,
) -> list[TemplateCatalogEntry]:
    entries: list[TemplateCatalogEntry] = []
    for scope in ("user", "candidate"):
        for manifest_path in sorted((Path(template_store_root) / scope).glob("*/manifest.json")):
            manifest = load_json(manifest_path)
            checklist = derive_guided_intake_checklist(manifest, generated_at=generated_at)
            card = _build_card(manifest)
            entries.append(
                TemplateCatalogEntry(
                    templateId=manifest["templateId"],
                    version=manifest["version"],
                    manifestPath=manifest_path,
                    manifest=manifest,
                    checklist=checklist,
                    card=card,
                )
            )
    return entries
