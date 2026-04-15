---
name: resume
description: This skill should be used when the user asks to "优化简历", "完善简历", "修改简历", "润色简历", "制作简历", "写简历", "改简历", "整理项目经历", "把项目写进简历", "生成一版社招后端简历", or when the user provides resume files, project notes, handoff docs, PDFs, Markdown drafts, or asks for a job-targeted resume rewrite. Use it whenever the task is to extract resume material, rewrite experience bullets, tailor a resume to a target role, or turn repeated resume-editing practice into reusable guidance.
argument-hint: [目标岗位或要求]
---

# Resume Improvement Skill

Use this skill to turn rough resume material into a stronger, role-targeted resume draft while also preserving reusable editing knowledge.

## Goals

Accomplish two things in parallel:

1. Improve the user's actual resume deliverable.
2. Extract stable rules that can be reused in future resume work.

Do not treat resume editing as one-off polishing. Capture durable patterns such as evaluation criteria, rewrite heuristics, missing-information checklists, and output structure.

## When to use this skill

Apply this skill when the task involves any of the following:

- Improving an existing resume draft.
- Rewriting project or work experience into resume bullets.
- Extracting resume material from PDFs, Markdown files, handoff notes, project docs, or interview notes.
- Tailoring a resume to a target role such as Java backend, full-stack, or campus recruiting.
- Converting messy material into a structured resume draft.
- Identifying what information is still missing before a resume can become a final delivery.
- Building a reusable resume-editing workflow from the current collaboration.

## Operating principles

- Prefer role-targeted rewriting over generic polishing.
- Prefer evidence over self-evaluation.
- Prefer enterprise project experience over weakly related filler for social-hire backend resumes.
- Prefer truthful wording over inflated ownership claims.
- Prefer concise, interview-friendly bullets over dense keyword stacking.
- Prefer collecting missing facts explicitly instead of guessing dates, impact, scale, or ownership.

## Recommended workflow

### 1. Identify the current source material

Start by locating the best available source:

- editable source files first: Markdown, JSON, DOCX source, notes
- then PDFs if no editable source exists
- then supporting docs such as handoff notes, project summaries, or architecture docs

Read the current resume before changing it. If the resume exists only as a PDF, search for adjacent editable source files or exported JSON.

### 2. Choose the working path

Keep two paths available and choose the one that matches the task:

- non-structured rewrite or polish: direct resume editing, tailoring, and cleanup
- structured guided-intake or follow-up: question-driven collection when facts are missing or the session is already in intake mode

Use the structured path when the work depends on intake batches, projected answers, or runtime-managed continuation. Otherwise keep the faster direct-editing path.

### 3. Non-structured rewrite or polish path

For normal polishing, rewriting, or role-targeted drafting, work directly from the source material:

- determine the target version such as social-hire backend, campus / junior, full-stack, or general fallback
- build a working inventory for each project: project name, team, time range, role, business scenario, responsibilities, tech stack, contributions, difficulty, optimizations, results
- condense long source material into project fact sheets when needed
- rewrite projects into resume-ready summaries, tech stacks, and bullets
- improve the skills section, replace empty self-evaluation with evidence, check quantification opportunities, and verify truthful wording
- produce an updated draft plus a missing-information list when facts are still needed

If the target is social-hire backend:

- move enterprise projects to the front
- reduce generic self-evaluation
- reduce weakly related frontend emphasis unless it supports the backend story
- rewrite titles and summary language to sound more professional and less student-oriented

Prefer bullets that can be expanded naturally in an interview.

Use patterns like:

- 负责 / 参与 **业务场景**，基于 **技术方案** 完成 **核心能力**，从而 **带来结果**
- 针对 **问题/瓶颈**，设计并落地 **方案**，使 **指标/体验/稳定性** 得到提升
- 通过 **架构/中间件/流程改造**，提升 **扩展性/复用度/吞吐/可观测性**

Avoid bullets that are only technology lists with no action or result.

### 4. Structured guided-intake or follow-up path

For structured intake or follow-up work, route through the host conversation adapter, which in turn reuses the structured runtime session runner. Do not improvise the control flow in the prompt.

Follow these rules:

- the host conversation adapter decides whether this turn should resume an active structured session, continue it with the current user reply, start a new structured session from explicit guided-intake artifacts, or stay in the normal freeform rewrite path
- guided-intake first-round answers are projected before follow-up begins
- the system/runtime decides whether the session should stop or continue
- the agent asks and normalizes only the current batch
- at the recommended-only boundary, the agent collects a yes/no decision and does not expand the scope on its own
- if an active structured session already exists, resume or continue it before starting a new freeform rewrite flow
- when the runtime is in `ask_batch`, only normalize the currently materialized batch
- when the runtime is in `await_recommended_decision`, only collect a yes/no continuation decision
- persist stable structured-session state after each transition so the next host turn can resume deterministically
- once the structured session is `completed`, hand the resulting projection back to the normal resume drafting path instead of continuing intake questions
- if no active structured session exists and no explicit structured-start inputs are available, stay in the normal freeform rewrite path instead of guessing that structured flow should start
- external hosts can drive the outer entrypoint through `.claude/skills/resume/agent_intake_cli.py`, which accepts a JSON request on stdin or via `--input-file` and returns a JSON envelope for host-side routing
- use `.claude/skills/resume/host_cli.py` only when a host needs direct structured-session control instead of the higher-level intake entrypoint

Host usage example:

```bash
python3 .claude/skills/resume/agent_intake_cli.py \
  --session-store .claude/skills/resume/.runtime/host_sessions \
  --input-file request.json
```

Minimal request shape:

```json
{
  "version": "resume-agent-intake-cli/v1",
  "turn": {
    "kind": "reply",
    "timestamp": "2026-04-14T10:00:00Z",
    "user_message": "这是我现在的简历"
  },
  "template_context": {
    "manifest": {"templateId": "...", "version": "..."},
    "checklist": {"checklistId": "..."}
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

Resume an active intake session with:

```json
{
  "version": "resume-agent-intake-cli/v1",
  "turn": {
    "kind": "resume",
    "timestamp": "2026-04-14T10:03:00Z"
  }
}
```

Success response shape:

```json
{
  "ok": true,
  "version": "resume-agent-intake-cli/v1",
  "outcome": {
    "mode": "structured_intake",
    "prompt_directive": "ask_current_batch",
    "prompt": "...",
    "structured_outcome": {
      "prompt_directive": "ask_current_batch",
      "session_id": "host-session-...",
      "next_action_kind": "ask_batch",
      "current_batch": [{"field_id": "required.role", "question": "..."}]
    },
    "material_result": {
      "parse_status": "parsed",
      "document_ids": ["source-existing-resume-md"]
    }
  }
}
```

Request rules:

- `version` must be `resume-agent-intake-cli/v1`
- `turn.kind` must be `reply` or `resume`
- `turn.timestamp` is required
- `turn.user_message` is optional
- `template_context` is optional, but if present it must include both `manifest` and `checklist`; omit it entirely when no template context is available
- `materials` is optional and must use snake_case keys: `document_id`, `source_label`, `media_type`, `text`
- `drafting_started` is optional and must be a boolean when provided

Error responses keep the same top-level `version` and use machine-readable codes: `invalid_request_json`, `invalid_request_shape`, and `invalid_request_io`.

Keep this path focused on collecting or normalizing the current batch cleanly. Do not turn it back into an open-ended rewrite workflow mid-session.

## Output expectations

When performing a substantial rewrite, prefer this output structure:

### A. Draft file

Create or update a role-specific resume draft in the project.

Suggested naming:

- `简历-社招后端.md`
- `简历-校招版.md`
- `简历-全栈版.md`

### B. Reusable process notes

Update reusable guidance when a stable lesson emerges. Store detailed heuristics in `references/` or another project note file rather than bloating this SKILL.md.

### C. Missing information list

Always list the facts still needed to reach a final delivery, especially:

- dates
- company and role names
- ownership boundaries
- metrics
- whether external links should be kept

## Quality bar

A strong resume bullet should let an interviewer naturally ask:

- What was the business background?
- Why was this solution chosen?
- What was difficult?
- How was it implemented?
- How was the result verified?

If a bullet cannot support a 1–3 minute explanation, rewrite it.

## Additional resources

Read these files when needed:

- `references/rewrite-rules.md` — concrete rewrite heuristics and anti-patterns
- `references/intake-checklist.md` — the information to collect before finalizing a resume

If the project already contains role-specific drafts or resume notes, treat them as higher-priority local context than generic advice.
