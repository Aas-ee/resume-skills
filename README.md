# resume-skills

[中文说明 / Chinese README](README.zh-CN.md)

A privacy-safe public snapshot of a reusable resume runtime package, public JSON CLIs, schemas, and template artifacts.

## What is in this repo

This repository currently publishes the reusable, non-personal parts of the project:

- `resume_runtime/` — the reusable public runtime package and public JSON CLI entrypoints for host-agnostic resume intake workflows
- `resume_runtime/template_catalog_cli.py` — public JSON CLI for listing template cards and derived template context
- `resume_runtime/render_cli.py` — public JSON CLI for rendering markdown/html/css bundles from a template manifest and profile
- `resume_runtime/template_store_cli.py` — public JSON CLI for saving and promoting reusable template packages
- `skills/resume/SKILL.md` — the shared agent-neutral resume workflow definition
- `.claude/skills/resume/` — the Claude-specific skill prompt layer, prompt rendering helpers, and compatibility wrappers around the public CLIs/runtime
- `resume_core/schema/` — JSON schema contracts for the template, intake, checklist, question, response, and projection layers
- `resume_core/examples/README.md` — guide to the synthetic public examples and recommended reading order
- `resume_core/examples/shared-field-catalog.v1.json` — shared field catalog example
- `resume_core/examples/template-registry.v1.json` — template registry example
- `resume_core/examples/templates/` — public template manifest examples
- `resume_core/examples/template-assets/` — built-in markdown/html/css template asset directories referenced by public manifests
- `resume_core/scripts/validate_resume_core.py` — schema and artifact validator

## What is intentionally not published

Some local files are intentionally excluded from the public repository because they may contain personal resume content, private examples, or internal working notes.

Examples of excluded material:

- personal resume drafts and exports
- private source documents and extracted artifacts
- internal design docs and implementation plans
- local-only test fixtures derived from private resume content

This means the public repository is a safe runtime-and-contract snapshot, not yet a fully reproducible end-to-end example pack.

## Shared skill definition

Non-Claude agents should start from the shared skill definition at `skills/resume/SKILL.md`.

That shared skill describes the public workflow and points to `resume_runtime/` as the supported shared surface.
Claude-specific wrappers under `.claude/skills/resume/` remain available, but they are adapter-layer compatibility helpers rather than the primary cross-agent contract.

## Main entrypoints

### Higher-level agent intake CLI

Use this when a host wants one outer entrypoint that can:

- detect resume intent
- ask for existing material when needed
- parse provided material
- route into structured intake when facts are missing
- hand off to drafting when enough information is available

```bash
python3 resume_runtime/agent_intake_cli.py \
  --session-store resume_runtime/.runtime/host_sessions \
  --input-file request.json
```

The Claude-side wrapper at `.claude/skills/resume/agent_intake_cli.py` remains available for compatibility, but external hosts should treat `resume_runtime/agent_intake_cli.py` as the public entrypoint.

Request version:

- `resume-agent-intake-cli/v1`

### Lower-level host CLI

Use this when a host wants direct control over structured session turns.

```bash
python3 resume_runtime/host_cli.py \
  --session-store resume_runtime/.runtime/host_sessions \
  --input-file request.json
```

The Claude-side wrapper at `.claude/skills/resume/host_cli.py` remains available for compatibility, but hosts integrating the reusable runtime should use `resume_runtime/host_cli.py` directly.

Request version:

- `resume-host-cli/v1`

## Minimal agent intake request example

```json
{
  "version": "resume-agent-intake-cli/v1",
  "turn": {
    "kind": "reply",
    "timestamp": "2026-04-14T10:00:00Z",
    "user_message": "这是我现在的简历"
  },
  "template_context": {
    "manifest": {"templateId": "demo-template", "version": "1.0.0"},
    "checklist": {"checklistId": "guided-intake-demo-template"}
  },
  "materials": [
    {
      "document_id": "source-existing-resume-md",
      "source_label": "existing-resume.md",
      "media_type": "text/markdown",
      "text": "# Alex Example"
    }
  ],
  "drafting_started": false
}
```

## Validation

The validator script checks the published schema and artifact set:

```bash
python3 resume_core/scripts/validate_resume_core.py
```

Note: the private repository contains additional examples and tests that are not part of this public snapshot.

## Current status

This repository is suitable for:

- reading the reusable runtime and CLI design
- reusing the public `resume_runtime` package and JSON contracts
- understanding the host-facing request and response envelopes
- studying the synthetic public examples in `resume_core/examples/README.md`
- building a host adapter around the published host-agnostic runtime while keeping Claude-only prompt rendering in `.claude/skills/resume/`

It now includes a small synthetic public examples pack for the `typora-classic` and `markdown-basic` templates.

It is still not a complete public starter kit because it does not publish:

- private working materials or real resume content
- a public demo app built on top of the published runtime package
- PDF or HTML final resume outputs
