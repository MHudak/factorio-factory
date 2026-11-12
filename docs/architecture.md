# Architecture

## Desired state vs. observed state

This repo is GitOps for a game. `main` holds what each factory *should* be. The running game is
what it *is*. A deploy step reconciles the two, and monitoring reports drift. That mirrors the
split Kubernetes makes between spec (in git) and status (in the cluster), with metrics and logs
kept elsewhere entirely.

| Data | Store | Writer | Why |
|---|---|---|---|
| Plans, blueprints, regions, checks | git (`factories/<name>/`) | PRs, reviewed and validated | Low churn, needs review and history |
| Live observed state | Per-factory SQLite on the factory's host | The factory controller only | Changes constantly; committing it would rebase every open PR |
| Text snapshots, milestone saves | Per-factory snapshot repo, saves as release assets | The factory controller only | Durable, tamper-evident history at low frequency |
| Agent telemetry | One file per run (run directories, later object storage) | The run itself | Append-only with a single writer: no contention |

**Durability.** A factory's SQLite store is replicated continuously to object storage, or at
minimum snapshotted. Snapshots in git give a second, coarser recovery point: each milestone
save can be restored on a new host. When several hosts or operators need one live view, the
store moves to managed Postgres with one schema per factory. Progeny's store port was designed
for that swap.

**Hosting.** Long-running factories need a persistent host (a workstation, an always-on VM or
a managed container), not an ephemeral agent session.

## One factory

A factory is one game world: one headless Factorio server instance, one chain of saves, one
goal, one directory here, one snapshot repo. Issues carry a `factory:<name>` label.
Orchestrator config maps each factory to its server instance and its write scope
(`factories/<name>/**`). Inside a world, **regions** (`regions.yaml`) subdivide the map, so
parallel workers do not build over each other. Regions are the spatial counterpart of file
scopes in code.

## Many factories

Shard everything per factory, and keep shared things rare and versioned.

| Cost | Growth | Mitigation |
|---|---|---|
| Servers, storage | Linear, cheap | About 3 servers per machine early in the game; then more hosts |
| Agent spend | Linear | A budget per factory; queue factories instead of running all at once |
| Human review | Linear demand, fixed capacity | Autonomy earned per gate; review by exception; a daily digest per factory |
| GitHub API quota | Shared per token | Only epics and stories are issues; incidents are de-duplicated and rate-limited; webhooks later |
| Shared `main` | Contention grows with n | Directory scopes now; one repo per factory from a template once n is large or comparisons must be blind |
| Shared `library/` | One change reaches every factory | Versioned releases; each factory pins a version and upgrades through its own PR |

**Fair comparisons.** Agents in a monorepo can read other factories' plans. For blind model or
team comparisons, run each factory in its own repo, or give the workspace a sparse checkout of
`factories/<own>/` and `library/` only.

## Pipeline (Progeny phases)

| Phase | Factorio meaning | Who |
|---|---|---|
| Requirements | Goal epic → milestone stories | Staff lead (agent), approved by a human |
| Triage | Story → tasks with regions and checks | Lead |
| Design | Site selection and a blueprint, validated in the creative sandbox (throughput, footprint, tileability) | Designer |
| Implementation | The blueprint and plan changes in this repo | Designer or builder |
| Verification | Schema validation, sandbox checks, scope and region containment | Deterministic, plus a reviewer |
| Integration | PR merged | Maintainer (autonomy later) |
| Deploy | Builder reconciles the live world; post-deploy checks run | Builder |
| Monitoring | Re-checks and diagnoses; drift opens an `incident` issue | Operator |
| Retro | Lessons per role | All |

Time model: gates run with the game **paused** first, which makes runs easier to correct, and
**live** as the goal.
