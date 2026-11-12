# factorio-factory

Factorio factories run as software projects. Each factory's **desired state** (plans,
blueprints, regions, acceptance checks) lives here. AI agents work the issues, open PRs that are
validated before merge, and a deploy step builds the merged state into a **live** Factorio game.
The game keeps running while tickets wait, just as production does.

The game-side tooling (MCP server, verification, design sandbox, lineages) is
[factorio-claude](https://github.com/MHudak/factorio-claude). Orchestration is moving to
[Progeny](https://github.com/MHudak/Progeny), whose epics #146 (parallel workers) and #147 (target
profiles, including live targets) were written for this repo.

## The model

| | Where it lives | Churn |
|---|---|---|
| **Desired state:** plans, blueprints, regions, checks | This repo, `factories/<name>/` on `main` | Low; every change is a reviewed PR |
| **Observed state:** what the game currently is | The factory's own store (SQLite, single writer) | Constant; **never committed here** |
| **Snapshots:** periodic text summaries, milestone saves | One snapshot repo per factory ([docs/snapshots.md](docs/snapshots.md)) | Hourly and per milestone, single writer |
| **Telemetry:** agent action logs, traces | Object storage or run directories, one file per run | Constant, single writer per file |

Issues → PR → validation → merge → **deploy** → post-deploy checks → monitoring → issues.
Design: [docs/architecture.md](docs/architecture.md). Contributor workflow: [docs/workflow.md](docs/workflow.md).

## Layout

```
factories/<name>/        one live factory = one game world
  factory.yaml           goal, seed, map, mode, team and models, time model, library pin, snapshot repo
  plans/                 roadmap and design docs
  blueprints/            desired-state builds
  regions.yaml           who owns which part of the map
  checks/                acceptance checks (milestones, per-build throughput)
library/                 shared blueprints and checks, versioned; factories pin a version
schemas/                 JSON Schemas for every file above and for snapshots
templates/snapshot-repo/ template for a factory's snapshot repo (protection + signature audit)
scripts/                 validation and setup helpers
```

## Factories

| Factory | Goal | Team | Purpose |
|---|---|---|---|
| [`rocket-solo`](factories/rocket-solo/factory.yaml) | Launch a rocket | One agent | Baseline (the pilots' setup) |
| [`rocket-team`](factories/rocket-team/factory.yaml) | Launch a rocket | Lead, designer, builder | Does team structure beat a single agent? Same seed. |

## Rules

1. **No runtime state in this repo.** It holds no status files, logs or saves, only desired state.
2. **One factory, one writer.** Each factory has exactly one controller process, which is the
   only writer of its store and its snapshot repo.
3. **Shared things are rare and versioned.** `library/` changes are released as versions, and
   factories upgrade their pin through their own PR.
4. **Only epics and stories are issues.** Fine-grained tasks live in the orchestrator's store.

## Validate locally

```bash
pip install pyyaml jsonschema
python scripts/validate.py
```

## License

MIT
