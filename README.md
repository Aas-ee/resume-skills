# resume-skills

[中文说明 / Chinese README](README.zh-CN.md)

A privacy-safe public snapshot of a resume skill runtime, JSON CLIs, schemas, and template artifacts.

## What is in this repo

This repository currently publishes the reusable, non-personal parts of the project:

- `.claude/skills/resume/` — the resume skill prompt, runtime, and JSON CLIs
- `resume_core/schema/` — JSON schema contracts for the template, intake, checklist, question, response, and projection layers
- `resume_core/examples/README.md` — guide to the synthetic public examples and recommended reading order
- `resume_core/examples/shared-field-catalog.v1.json` — shared field catalog example
- `resume_core/examples/template-registry.v1.json` — template registry example
- `resume_core/examples/templates/` — public template manifest examples
- `resume_core/scripts/validate_resume_core.py` — schema and artifact validator

## What is intentionally not published

Some local files are intentionally excluded from the public repository because they may contain personal resume content, private examples, or internal working notes.

Examples of excluded material:

- personal resume drafts and exports
- private source documents and extracted artifacts
- internal design docs and implementation plans
- local-only test fixtures derived from private resume content

This means the public repository is a safe runtime-and-contract snapshot, not yet a fully reproducible end-to-end example pack.

## Main entrypoints

### Higher-level agent intake CLI

Use this when a host wants one outer entrypoint that can:

- detect resume intent
- ask for existing material when needed
- parse provided material
- route into structured intake when facts are missing
- hand off to drafting when enough information is available

```bash
python3 .claude/skills/resume/agent_intake_cli.py \
  --session-store .claude/skills/resume/.runtime/host_sessions \
  --input-file request.json
```

Request version:

- `resume-agent-intake-cli/v1`

### Lower-level host CLI

Use this when a host wants direct control over structured session turns.

```bash
python3 .claude/skills/resume/host_cli.py \
  --session-store .claude/skills/resume/.runtime/host_sessions \
  --input-file request.json
```

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

- reading the runtime and CLI design
- reusing the JSON contracts
- understanding the host-facing request and response envelopes
- studying the synthetic public examples in `resume_core/examples/README.md`
- building a host adapter around the published skill runtime

It now includes a small synthetic public examples pack for the `typora-classic` and `markdown-basic` templates.

It is still not a complete public starter kit because it does not publish:

- private working materials or real resume content
- a public demo app or packaged SDK outside `.claude/`
- PDF or HTML final resume outputs
