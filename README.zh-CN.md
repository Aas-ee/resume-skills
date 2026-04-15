# resume-skills

[English README](README.md)

这是一个经过隐私筛选后公开的简历 skill 仓库快照，当前主要包含 runtime、JSON CLI、schema，以及模板相关的公共产物。

## 这个仓库当前包含什么

当前公开的是可复用、非个人化的部分：

- `.claude/skills/resume/` —— resume skill 的提示词、runtime 和 JSON CLI
- `resume_core/schema/` —— 模板层、intake 层、checklist 层、question 层、response 层、projection 层的 JSON Schema 合约
- `resume_core/examples/README.md` —— 纯虚构 public examples 的导读和推荐阅读顺序
- `resume_core/examples/shared-field-catalog.v1.json` —— 公共字段目录示例
- `resume_core/examples/template-registry.v1.json` —— 模板注册表示例
- `resume_core/examples/templates/` —— 可公开的模板清单示例
- `resume_core/scripts/validate_resume_core.py` —— schema 和工件校验脚本

## 哪些内容被刻意不公开

为了避免泄露个人简历内容、私有样例或内部工作过程，一部分本地文件没有放进公开仓库。

典型的未公开内容包括：

- 个人简历草稿和导出文件
- 私有 source documents 与 extraction 产物
- 内部设计文档和实现计划
- 基于个人简历数据生成的本地测试夹具

所以当前公开仓库更像是一个**安全可公开的 runtime + contract 快照**，而不是一个已经完整脱敏、可直接端到端复现的示例仓库。

## 主要入口

### 更高层的 agent intake CLI

适用于宿主只想接一个外层入口，由它完成：

- 识别是否是简历意图
- 在缺少材料时向用户索要现有简历
- 解析用户提供的简历材料
- 在信息缺失时切入 structured intake
- 在信息足够时把流程交回 drafting

```bash
python3 .claude/skills/resume/agent_intake_cli.py \
  --session-store .claude/skills/resume/.runtime/host_sessions \
  --input-file request.json
```

请求版本：

- `resume-agent-intake-cli/v1`

### 更底层的 host CLI

适用于宿主想直接控制 structured session turn 的场景。

```bash
python3 .claude/skills/resume/host_cli.py \
  --session-store .claude/skills/resume/.runtime/host_sessions \
  --input-file request.json
```

请求版本：

- `resume-host-cli/v1`

## 一个最小的 agent intake 请求示例

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

## 校验

可以用下面的脚本检查当前公开的 schema 和 artifact 集合：

```bash
python3 resume_core/scripts/validate_resume_core.py
```

注意：私有仓库中还有额外的 examples 和 tests，这些目前没有放进这个公开快照。

## 当前状态

这个仓库目前适合用来：

- 阅读 runtime 和 CLI 的设计
- 复用 JSON contract
- 理解宿主侧请求 / 响应 envelope
- 结合 `resume_core/examples/README.md` 阅读纯虚构的公开 examples 链路
- 基于已公开的 skill runtime 做自己的 host adapter

它现在已经包含一套面向 `typora-classic` 和 `markdown-basic` 的小型 synthetic public examples。

它仍然不是一个完整的公开 starter kit，因为还没有公开：

- 私有工作材料或真实简历内容
- `.claude/` 之外的 demo app / 独立 SDK 打包
- PDF / HTML 形式的最终简历产物
