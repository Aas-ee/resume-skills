from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from resume_runtime.runtime.template_renderer import render_template_bundle, write_rendered_bundle

CLI_VERSION = "resume-render-cli/v1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a resume template bundle")
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    request = json.loads(sys.stdin.read())
    if request.get("version") != CLI_VERSION:
        raise SystemExit(2)
    manifest_path = Path(request["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bundle = render_template_bundle(
        manifest=manifest,
        manifest_path=manifest_path,
        profile=request["profile"],
    )
    payload = {
        "ok": True,
        "version": CLI_VERSION,
        "bundle": bundle,
    }
    if args.output_dir is not None:
        payload["written"] = write_rendered_bundle(bundle, args.output_dir)
    sys.stdout.write(json.dumps(payload, sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
