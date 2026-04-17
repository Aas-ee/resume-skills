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

## Claude-specific operating rules

1. Follow `skills/resume/SKILL.md` for the shared workflow.
2. Use Claude prompt rendering only after the shared runtime has determined the workflow state.
3. Do not move shared runtime logic back into `.claude`.
4. Treat `.claude/skills/resume/` as adapter code, not as the canonical cross-agent implementation.

## Additional Claude resources

- `references/rewrite-rules.md` — concrete rewrite heuristics and anti-patterns
- `references/intake-checklist.md` — information to collect before finalizing a resume
