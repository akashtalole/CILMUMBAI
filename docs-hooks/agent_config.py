"""MkDocs hook: show each agent's configuration on its page.

Agent files keep their configuration (model, tools, roster) in YAML front
matter, which MkDocs would otherwise hide. This puts it back above the prompt.
"""

import yaml


def on_page_markdown(markdown, page, config, files, **kwargs):
    if "/managed-agents/agents/" not in "/" + page.file.src_uri or not page.meta:
        return markdown
    settings = yaml.safe_dump(page.meta, sort_keys=False, allow_unicode=True, width=100)
    return (
        "## Configuration\n\n"
        "Applied with `ant apply` from the agent's file in the repository.\n\n"
        f"```yaml\n{settings}```\n\n"
        "## System prompt\n\n" + markdown
    )
