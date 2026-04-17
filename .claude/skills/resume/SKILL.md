---
name: resume
description: This skill should be used when the user asks to improve a resume, rewrite resume material, choose a resume template, or run the resume workflow inside Claude.
argument-hint: [目标岗位或要求]
---

# Claude Resume Adapter Skill

This Claude skill is an adapter layer over the shared resume workflow.

**Primary shared workflow definition:** `skills/resume/SKILL.md`

Use that shared skill as the source of truth for:
- when to use the resume workflow;
- template-first flow;
- public runtime and CLI entrypoints;
- structured intake vs direct rewrite behavior;
- cross-agent usage.

## What is Claude-specific here

Keep Claude-specific behavior in this layer only:

- prompt rendering in `.claude/skills/resume/runtime/prompt_renderer.py`
- Claude prompt adaptation in `.claude/skills/resume/runtime/agent_prompt_adapter.py`
- compatibility wrappers:
  - `.claude/skills/resume/agent_intake_cli.py`
  - `.claude/skills/resume/host_cli.py`
  - `.claude/skills/resume/template_catalog_cli.py`
  - `.claude/skills/resume/template_store_cli.py`

When possible, prefer the public entrypoints in `resume_runtime/` as the real shared interface. The Claude wrappers exist so Claude-side integrations keep working without redefining the runtime contract.

For template discovery, `.claude/skills/resume/template_catalog_cli.py` delegates to the public catalog CLI.
Inside this repository it can be run without extra arguments:

```bash
python3 .claude/skills/resume/template_catalog_cli.py
```

Do not assume the current working directory is this repository root.
If Claude is operating from another workspace, invoke the wrapper by absolute path instead of using a cwd-relative repo path.

Example:

```bash
python3 /abs/path/to/resume-skills/.claude/skills/resume/template_catalog_cli.py
```

The response shape matches the public runtime contract, including:
- `card`
- `template_context`
- `asset_paths` for resolved markdown/html/css file locations

Recommended template discovery sequence inside Claude:
1. Run `python3 .claude/skills/resume/template_catalog_cli.py`
2. Read `entries[].card` to present built-in template choices
3. Read `entries[].asset_paths` when you need the concrete CSS, HTML, or Markdown asset files
4. After the user chooses a template, pass `entries[].template_context` into `.claude/skills/resume/agent_intake_cli.py` or the public `resume_runtime/agent_intake_cli.py`
5. Only fall back to direct rewrite without template selection when the task is explicitly a pure rewrite request
6. Match fixed section headings and field labels to the user's language; Chinese requests should not keep English template headings in the final resume

## Claude-specific operating rules

1. Follow `skills/resume/SKILL.md` for the shared workflow.
2. Use Claude prompt rendering only after the shared runtime has determined the workflow state.
3. Do not move shared runtime logic back into `.claude`.
4. Treat `.claude/skills/resume/` as adapter code, not as the canonical cross-agent implementation.

## Additional Claude resources

- `references/rewrite-rules.md` — concrete rewrite heuristics and anti-patterns
- `references/intake-checklist.md` — information to collect before finalizing a resume
