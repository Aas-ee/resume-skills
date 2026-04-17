---
name: resume
description: Use when improving a resume, extracting resume material, choosing a resume template, or running a template-first intake workflow in any agent environment.
---

# Shared Resume Workflow

This is the shared, agent-neutral definition of the resume workflow.

Use it when you need to:
- improve an existing resume draft;
- turn project notes or raw material into resume content;
- select a template before intake;
- run structured guided intake for missing fields;
- keep the workflow reusable across Claude and non-Claude agents.

## Core rule

Treat `resume_runtime/` as the primary shared interface.

Use these public entrypoints:
- `resume_runtime/template_catalog_cli.py` — list built-in and stored templates and derive `template_context`
- `resume_runtime/template_store_cli.py` — save personal templates and promote candidate templates
- `resume_runtime/agent_intake_cli.py` — host-facing outer intake entrypoint
- `resume_runtime/host_cli.py` — lower-level structured session control
- `resume_runtime/render_cli.py` — render markdown/html/css output bundles from a manifest and profile

Claude-specific wrappers under `.claude/skills/resume/` are compatibility adapters, not the primary shared contract.

## Recommended workflow

### 1. Choose the template first

Before parsing materials or asking for missing information, choose a template.

- In this repository, built-in template manifests live under `resume_core/examples/templates/`
- Built-in template assets, including CSS, live under `resume_core/examples/template-assets/`
- The current built-in templates are `typora-classic` and `markdown-basic`
- load built-in and stored templates through `resume_runtime/template_catalog_cli.py`
- read `asset_paths` from the catalog CLI response when you need the concrete markdown/html/css file locations for a template
- show template cards with template id, style, use cases, and required-content summary
- let the user choose a built-in template, a stored template, upload a new template, or ask for a derivative template
- once a template is chosen, use the returned `manifest` + derived `checklist` as the `template_context` for `resume_runtime/agent_intake_cli.py`

If you are running inside this repository, enumerate built-in templates with:

```bash
python3 resume_runtime/template_catalog_cli.py
```

You can still override the defaults when needed:

```bash
python3 resume_runtime/template_catalog_cli.py \
  --examples-root resume_core/examples \
  --generated-at 2026-04-16T12:00:00Z
```

If you need to inspect a built-in template directly, start from:
- `resume_core/examples/templates/typora-classic.v1.json`
- `resume_core/examples/templates/markdown-basic.v1.json`
- `resume_core/examples/template-assets/typora-classic/style.css`
- `resume_core/examples/template-assets/markdown-basic/style.css`

Do not assume the template files live beside `skills/resume/SKILL.md`. The skill file defines the workflow; the built-in template manifests and assets live in the repository paths above.

### 2. Choose the content path after template selection

Use one of these paths:
- direct content entry
- parsing existing materials
- follow-up questioning only for missing template-required fields

If the work is straightforward rewrite/polish, stay in direct editing.
If the work depends on structured intake state, missing-field projection, or follow-up rounds, route through the public intake/session CLIs.

### 3. Use the public intake flow for structured collection

For structured intake and follow-up:
- call `resume_runtime/agent_intake_cli.py` as the public outer entrypoint
- provide `template_context` when a template has already been chosen
- let the runtime decide whether the turn should stay freeform, ask for material, parse material, continue a structured session, or hand off to drafting
- only ask the current batch of questions materialized by the runtime
- at the recommended-only boundary, collect only a yes/no continuation decision

### 4. Draft against the selected template

When enough information is available:
- produce the resume draft that matches the selected template’s required structure
- preserve evidence-based wording and truthful ownership
- list any remaining missing facts explicitly instead of guessing

### 5. Render final template artifacts through the public renderer

When a profile is ready:
- use `resume_runtime/render_cli.py` or the shared rendering helpers
- generate markdown/html/css outputs from the selected manifest and profile
- treat these rendered assets as the portable output bundle for host integrations and Typora-first preview flows

## Host-neutral request shape

When calling `resume_runtime/agent_intake_cli.py`, use the public request envelope documented in `README.md` and this shared skill.

At minimum, expect these concepts:
- `version`
- `turn`
- optional `template_context`
- optional `materials`
- optional `drafting_started`

## Output expectations

A good run should usually produce:
- a selected template or template decision
- a filled or partially filled profile
- a clear missing-information list when facts are still absent
- a resume draft or rendered output bundle when enough information is present

## Boundary rule

Shared workflow logic belongs in `resume_runtime/` and shared docs like this file.
Agent-specific prompt shaping belongs in that agent’s adapter layer.
