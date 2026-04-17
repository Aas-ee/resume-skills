from __future__ import annotations

import argparse
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
    from resume_runtime.runtime.template_store import TemplateStore
except ModuleNotFoundError:  # pragma: no cover - direct script fallback
    _bootstrap_package_for_direct_script()
    from resume_runtime.runtime.template_store import TemplateStore

CLI_VERSION = "resume-template-store-cli/v1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save or promote resume template packages")
    parser.add_argument("--store-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    request = json.loads(sys.stdin.read())
    if request.get("version") != CLI_VERSION:
        raise SystemExit(2)

    store = TemplateStore(args.store_root)
    if request["action"] == "save":
        manifest_path = store.save(
            scope=request["scope"],
            manifest=request["manifest"],
            markdown=request["assets"]["markdown"],
            html=request["assets"]["html"],
            css=request["assets"]["css"],
        )
    elif request["action"] == "promote":
        manifest_path = store.promote(request["template_id"])
    else:
        raise SystemExit(2)

    payload = {
        "ok": True,
        "version": CLI_VERSION,
        "manifest_path": str(manifest_path),
    }
    sys.stdout.write(json.dumps(payload, sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
