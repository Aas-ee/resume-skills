from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import sys
from pathlib import Path


def _bootstrap_package_for_direct_script() -> None:
    package_root = Path(__file__).resolve().parent
    package_init = package_root / "__init__.py"
    if "resume_runtime" in sys.modules or not package_init.exists():
        return
    spec = importlib.util.spec_from_file_location(
        "resume_runtime",
        package_init,
        submodule_search_locations=[str(package_root)],
    )
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules["resume_runtime"] = module
    spec.loader.exec_module(module)


try:
    from resume_runtime.runtime.template_catalog import load_template_catalog
except ModuleNotFoundError:  # pragma: no cover - direct script fallback
    _bootstrap_package_for_direct_script()
    from resume_runtime.runtime.template_catalog import load_template_catalog

CLI_VERSION = "resume-template-catalog-cli/v1"


def _default_examples_root() -> Path:
    return Path(__file__).resolve().parents[1] / "resume_core" / "examples"


def _default_generated_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List resume templates and derived template_context")
    parser.add_argument(
        "--examples-root",
        type=Path,
        default=_default_examples_root(),
        help="Examples root containing template registry and built-in templates",
    )
    parser.add_argument("--template-store-root", type=Path, default=None)
    parser.add_argument(
        "--generated-at",
        type=str,
        default=_default_generated_at(),
        help="Timestamp used when deriving template checklists",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    entries = load_template_catalog(
        examples_root=args.examples_root,
        template_store_root=args.template_store_root,
        generated_at=args.generated_at,
    )
    payload = {
        "ok": True,
        "version": CLI_VERSION,
        "entries": [
            {
                "manifest_path": str(entry.manifestPath),
                "asset_paths": entry.asset_paths,
                "card": entry.card.to_dict(),
                "template_context": entry.template_context,
            }
            for entry in entries
        ],
    }
    sys.stdout.write(json.dumps(payload, sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
