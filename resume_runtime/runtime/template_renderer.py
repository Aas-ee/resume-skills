from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_SECTION_RE = re.compile(r"{{#([^}]+)}}(.*?){{/\1}}", re.DOTALL)
_FIELD_RE = re.compile(r"{{([^#/][^}]*)}}")
_HTML_TAG_RE = re.compile(r"<html\b", re.IGNORECASE)

_HTML_DOCUMENT_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
{css}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_asset_path(manifest_path: Path, asset_ref: str) -> Path:
    return (manifest_path.parent / asset_ref).resolve()


def _coerce_list(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    return [value]


def _zip_rows(
    field_values: dict[str, Any],
    prefix: str,
    field_names: tuple[str, ...],
) -> list[dict[str, Any]]:
    columns = {
        field_name: _coerce_list(field_values.get(f"{prefix}[].{field_name}"))
        for field_name in field_names
    }
    populated_lengths = {
        field_name: len(column)
        for field_name, column in columns.items()
        if len(column) > 0
    }
    if populated_lengths:
        expected_length = next(iter(populated_lengths.values()))
        inconsistent = {
            field_name: length
            for field_name, length in populated_lengths.items()
            if length != expected_length
        }
        if inconsistent:
            lengths = ", ".join(
                f"{field_name}={populated_lengths[field_name]}"
                for field_name in field_names
                if field_name in populated_lengths
            )
            raise ValueError(
                f"{prefix} repeatable fields have inconsistent populated lengths: {lengths}"
            )
        row_count = expected_length
    else:
        row_count = 0
    rows: list[dict[str, Any]] = []
    for index in range(row_count):
        row: dict[str, Any] = {}
        for field_name, column in columns.items():
            if index < len(column):
                row[field_name] = column[index]
        rows.append(row)
    return rows


def build_template_context(profile: dict[str, Any]) -> dict[str, Any]:
    field_values = profile["fieldValues"]
    return {
        "basic.name": field_values.get("basic.name", ""),
        "basic.nameEn": field_values.get("basic.nameEn", ""),
        "basic.phone": field_values.get("basic.phone", ""),
        "basic.email": field_values.get("basic.email", ""),
        "required.role": field_values.get("required.role", ""),
        "links.github": field_values.get("links.github", ""),
        "summary.items": _coerce_list(field_values.get("summary.items", [])),
        "skills.items": _coerce_list(field_values.get("skills.items", [])),
        "work": _zip_rows(field_values, "work", ("date", "company", "role", "bullets")),
        "education": _zip_rows(
            field_values,
            "education",
            ("date", "school", "degree", "major"),
        ),
        "project": _zip_rows(
            field_values,
            "project",
            ("date", "name", "role", "techStack", "bullets"),
        ),
    }


def _stringify(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, list):
        return ", ".join(
            _stringify(item)
            for item in value
            if item not in (None, "")
        )
    return str(value)


def render_template_text(template_text: str, context: dict[str, Any]) -> str:
    def replace_section(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        block = match.group(2)
        value = context.get(key)
        if value in (None, "", [], False):
            return ""
        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                nested = dict(context)
                nested["."] = item
                if isinstance(item, dict):
                    nested.update(item)
                parts.append(render_template_text(block, nested))
            return "".join(parts)
        nested = dict(context)
        nested["."] = value
        if isinstance(value, dict):
            nested.update(value)
        return render_template_text(block, nested)

    rendered = _SECTION_RE.sub(replace_section, template_text)
    return _FIELD_RE.sub(
        lambda match: _stringify(context.get(match.group(1).strip(), "")),
        rendered,
    )


def _build_standalone_html(
    html_fragment: str,
    css_text: str,
    *,
    title: str,
) -> str:
    if _HTML_TAG_RE.search(html_fragment):
        return html_fragment
    return _HTML_DOCUMENT_TEMPLATE.format(
        title=title,
        css=css_text,
        body=html_fragment,
    )


def render_template_bundle(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    profile: dict[str, Any],
) -> dict[str, str]:
    context = build_template_context(profile)
    markdown_template = _resolve_asset_path(
        manifest_path,
        manifest["assetRefs"]["markdown"],
    ).read_text(encoding="utf-8")
    html_template = _resolve_asset_path(
        manifest_path,
        manifest["assetRefs"]["html"],
    ).read_text(encoding="utf-8")
    css_text = _resolve_asset_path(
        manifest_path,
        manifest["assetRefs"]["css"],
    ).read_text(encoding="utf-8")
    rendered_html = render_template_text(html_template, context)
    return {
        "markdown": render_template_text(markdown_template, context),
        "html": _build_standalone_html(
            rendered_html,
            css_text,
            title=_stringify(context.get("basic.name")) or manifest.get("name", "Resume"),
        ),
        "css": css_text,
    }


def write_rendered_bundle(bundle: dict[str, str], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "resume.md"
    html_path = output_dir / "resume.html"
    css_path = output_dir / "style.css"
    markdown_path.write_text(bundle["markdown"], encoding="utf-8")
    html_path.write_text(bundle["html"], encoding="utf-8")
    css_path.write_text(bundle["css"], encoding="utf-8")
    return {
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "css_path": str(css_path),
    }
