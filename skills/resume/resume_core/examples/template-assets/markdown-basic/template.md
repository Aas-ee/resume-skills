# {{basic.name}}

{{basic.email}}
{{#links.github}}{{links.github}}{{/links.github}}

## 个人总结
{{#summary.items}}
- {{.}}
{{/summary.items}}

## 教育经历
{{#education}}
- {{school}} · {{degree}} · {{major}}
{{/education}}

## 项目经历
{{#project}}
### {{name}}
角色：{{role}}
{{#bullets}}
- {{.}}
{{/bullets}}
{{/project}}
