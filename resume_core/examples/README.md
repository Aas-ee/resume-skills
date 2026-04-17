# Public Resume Examples

All files in this directory are **synthetic fixtures** for schema, validator, and runtime demonstrations. They are not redacted copies of a real candidate resume.

## Baseline templates

The public baseline templates are:

- `typora-classic`
- `markdown-basic`

## Start with the shared template artifacts

Read these first:

- `shared-field-catalog.v1.json`
- `template-registry.v1.json`
- `templates/typora-classic.v1.json`
- `templates/markdown-basic.v1.json`

## Template asset directories

Each built-in template now points to concrete assets in `template-assets/`:

- `template.md` — markdown-first editable template
- `template.html` — HTML rendering template
- `style.css` — reusable style asset for the Typora-first template package and later host reuse

For `typora-classic`, the markdown asset is the primary authoring surface and closely follows a Typora-style table-based printable resume layout.

## Built-in template gallery

Each built-in template manifest includes a `previewCard` block that hosts can surface as a template-selection card before intake starts.

Hosts can list those cards through the public catalog CLI:

```bash
python3 resume_runtime/template_catalog_cli.py \
  --examples-root resume_core/examples \
  --generated-at 2026-04-16T12:00:00Z
```

The CLI response includes one `card` per template, derived directly from each manifest's `previewCard`, alongside the matching `template_context` payload for downstream intake.

## Raw material to extracted facts

This chain shows how one synthetic source document becomes extracted facts and then a reusable profile:

1. `source-documents/existing-resume-markdown.v1.json`
2. `source-extractions/extract-basic-name.v1.json`
3. `source-extractions/extract-github-link.v1.json`
4. `source-extractions/extract-project-name.v1.json`
5. `source-extractions/extract-project-role.v1.json`
6. `source-extractions/extract-project-tech-stack.v1.json`
7. `resume-profiles/sample-ai-agent-profile.v1.json`

## Typora Classic reading path

The Typora-first package is the primary end-to-end example. It shows both import-existing and guided-intake entry points, then one guided round and one follow-up round:

- `intake-sessions/typora-import-existing.v1.json`
- `intake-sessions/typora-guided-empty.v1.json`
- `guided-intake-checklists/typora-classic.v1.json`
- `guided-intake-question-sets/typora-classic.v1.json`
- `guided-intake-response-sets/typora-classic.partial.v1.json`
- `guided-intake-profile-projections/typora-classic.partial.v1.json`
- `gap-reports/typora-classic-gap.v1.json`
- `follow-up-question-sets/typora-classic.v1.json`
- `follow-up-response-sets/typora-classic.partial.v1.json`
- `follow-up-profile-projections/typora-classic.partial.v1.json`
- `gap-reports/typora-classic-follow-up-gap.v1.json`

## Markdown Basic reading path

The Markdown path shows the same contract flow with a different template manifest and field requirements:

- `intake-sessions/markdown-manual-override.v1.json`
- `guided-intake-checklists/markdown-basic.v1.json`
- `guided-intake-question-sets/markdown-basic.v1.json`
- `guided-intake-response-sets/markdown-basic.partial.v1.json`
- `guided-intake-profile-projections/markdown-basic.partial.v1.json`
- `gap-reports/markdown-basic-gap.v1.json`
- `follow-up-question-sets/markdown-basic.v1.json`
- `follow-up-response-sets/markdown-basic.partial.v1.json`
- `follow-up-profile-projections/markdown-basic.partial.v1.json`
- `gap-reports/markdown-basic-follow-up-gap.v1.json`

## Ids to follow while reading

- `templateId` and `templateVersion` connect template-scoped artifacts.
- `documentId` and `extractionId` connect the raw-material example to extracted facts.
- `questionSetId`, `responseSetId`, `followUpQuestionSetId`, and `followUpResponseSetId` connect each intake round.
- `profileId` and `reportId` connect projections and gap reports across the flow.
