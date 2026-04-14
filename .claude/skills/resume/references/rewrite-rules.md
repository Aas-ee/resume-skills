# Resume Rewrite Rules

## Role targeting

### Social-hire backend

Prioritize:
- enterprise project experience
- backend ownership
- architecture, middleware, asynchronous processing, observability, storage, and performance topics
- measurable improvements

De-emphasize:
- generic self-evaluation
- weakly related frontend details
- student-style titles such as “初级” unless strategically necessary
- long ungrouped skill lists

## Project ordering

Default order for a social-hire backend resume:
1. most relevant enterprise projects
2. strongest role-aligned personal project
3. older or weaker supporting experience

## Bullet rewrite pattern

Prefer this logic:

- scenario
- action
- method
- result

Examples:

- Participated in the core message flow of a messaging platform, using RabbitMQ consumers and strategy factories to support send, reissue, and callback scenarios, improving channel extensibility and routing clarity.
- Built a dynamic AI quality-check workflow with parallel simple nodes and serial aggregator nodes, improving throughput while preserving downstream aggregation logic.
- Unified gateway-side AK/SK signature validation and call statistics with Spring Cloud Gateway + Dubbo, improving API governance consistency.

## What to avoid

Avoid bullets that are only:
- technology stacks with no action
- broad claims with no evidence
- task lists with no value statement
- copied architecture prose that does not show personal contribution

## Skill section heuristics

Group skills into 4–6 recruiter-readable categories. Do not present a single oversized paragraph.

A good skills section helps a reviewer answer:
- Is this candidate relevant?
- Can this person be interviewed for this role?
- What areas are worth drilling into?

## Quantification prompts

For each project, try to ask:
- Did it make anything faster?
- Did it reduce failures or manual work?
- What scale did it serve?
- How many systems, channels, nodes, tasks, or files were involved?
- Was any internal reuse or onboarding improved?

If a number cannot be confirmed, ask for it instead of manufacturing it.

If a true number feels "not huge," still use it when it is meaningful. Prefer honest scale wording such as:
- 10万级
- 百级节点
- 毫秒级响应

Pair moderate scale numbers with stability, efficiency, reuse, or troubleshooting improvements so the bullet still carries business value.

When throughput is not the strongest signal, quantify structural complexity or operational value instead, for example:
- number of workflow nodes
- number of channels or integrations
- text length / document size / file volume handled
- configurability that reduces manual maintenance cost
- alerting or observability improvements that reduce diagnosis effort

For file and object-storage projects, strong quantification often comes from:
- supported file size (for example, 10GB-class uploads)
- number of archived records or files
- whether traffic is offloaded to MinIO / OSS / COS through pre-signed URLs
- async export / download behavior and troubleshooting visibility

For workflow, strategy, scheduling, or batch-processing projects, strong quantification often comes from:
- single-batch processing scale
- target capacity design level (for example, 100万级)
- stateless horizontal scaling design
- fixed-frequency writeback to reduce database pressure
- improvements to allocation efficiency, scheduling automation, or stats latency

## Truthfulness ladder

Use wording based on evidence strength:

- strong evidence: 主导 / 设计并落地 / 独立负责
- medium evidence: 深度参与 / 负责核心模块
- weak evidence: 参与 / 协助

Upgrade wording only after user confirmation.

## Deliverable hygiene

Keep collaboration scaffolding out of the final resume body.

Do not leave items like:
- 时间待补
- 待确认信息
- later / TODO-style placeholders
- internal reminders to the candidate

Keep unresolved facts in a separate checklist or project note, not in the outward-facing resume.

## Final-pass checks

Before considering a draft strong enough to deliver, verify:
- target role is explicit
- project order matches the role
- the top 2–4 projects are the strongest ones
- each major project has at least 2–4 useful bullets
- at least some bullets contain outcome or impact
- weak self-evaluation has been removed or minimized
- unresolved missing facts are listed separately from the resume body
