# {{basic.name}}

Email: {{basic.email}}
{{#links.github}}GitHub: {{links.github}}{{/links.github}}

{{#summary.items}}
- {{.}}
{{/summary.items}}

## Education
{{#education}}
### {{school}}
{{degree}} · {{major}}
{{/education}}

## Projects
{{#project}}
### {{name}} | {{role}}
Tech Stack: {{techStack}}
{{#bullets}}
- {{.}}
{{/bullets}}
{{/project}}
