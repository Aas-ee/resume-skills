<div class="resume-page">

<table class="resume-header">
  <tr>
    <td class="label name">{{basic.name}}</td>
    <td class="value name">{{basic.nameEn}}</td>
  </tr>{{#basic.phone}}
  <tr>
    <td class="label">电话</td>
    <td class="value">{{basic.phone}}</td>
  </tr>{{/basic.phone}}
  <tr>
    <td class="label">邮箱</td>
    <td class="value">{{basic.email}}</td>
  </tr>{{#links.github}}
  <tr>
    <td class="label">链接</td>
    <td class="value"><a href="{{links.github}}">{{links.github}}</a></td>
  </tr>{{/links.github}}
  <tr>
    <td class="label">求职方向</td>
    <td class="value emphasis">{{required.role}}</td>
  </tr>
</table>

## 个人总结

{{#summary.items}}
- {{.}}
{{/summary.items}}

## 专业技能

{{#skills.items}}
- {{.}}
{{/skills.items}}

{{#work}}
## 工作经历

<table class="entry-table work-table">
  <tr>
    <td class="date">{{date}}</td>
    <td class="main">{{company}}</td>
    <td class="side">{{role}}</td>
  </tr>
</table>

{{#bullets}}
- {{.}}
{{/bullets}}
{{/work}}

## 项目经历

{{#project}}
<table class="entry-table project-table">
  <tr>
    <td class="date">{{date}}</td>
    <td class="main">{{name}}</td>
    <td class="side">{{role}}</td>
  </tr>{{#techStack}}
  <tr class="meta-row">
    <td class="meta" colspan="3">技术栈：{{techStack}}</td>
  </tr>{{/techStack}}
</table>

{{#bullets}}
- {{.}}
{{/bullets}}
{{/project}}

## 教育经历

{{#education}}
<table class="entry-table edu-table">
  <tr>
    <td class="date">{{date}}</td>
    <td class="main">{{school}}</td>
    <td class="side">{{degree}}</td>
  </tr>
  <tr class="meta-row">
    <td class="date"></td>
    <td class="meta">{{major}}</td>
    <td class="side"></td>
  </tr>
</table>
{{/education}}

</div>
