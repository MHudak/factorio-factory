# factorio-factory

Desired state for live Factorio factories, worked as a software project. Model and rules:
`README.md`, `docs/architecture.md`, `docs/workflow.md`, `docs/snapshots.md`.

## Rules for agents

1. Work starts from an issue with numbered acceptance criteria. Change only the story's write
   scope (normally `factories/<name>/**`). Need more: ask on the issue.
2. Never commit runtime state (saves, databases, logs, status files). `scripts/validate.py`
   fails if you do.
3. Do not edit another factory's directory, and do not read other factories' plans when a story
   says the comparison is blind.
4. `library/`, `schemas/`, `scripts/`, `templates/`, `.github/` and `docs/` are shared or
   governing (see `.github/CODEOWNERS`). Change them only under an infrastructure story.
5. Run `python scripts/validate.py` before every PR, and report its result faithfully.
6. Game actions go through the factorio-claude MCP tools. Planning roles use observation tools
   only.
