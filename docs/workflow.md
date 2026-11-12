# Workflow

## Issues

- **Epics** are factory goals ("rocket-team: launch a rocket") or infrastructure outcomes.
  **Stories** are deliverable slices with numbered, checkable acceptance criteria. Both use the
  forms in `.github/ISSUE_TEMPLATE/`, which match Progeny's.
- Every factory issue carries the label `factory:<name>`. Repo-wide work carries
  `infrastructure`. Monitoring opens `incident` issues.
- Only epics, stories and incidents are issues. Fine-grained tasks (one build step, one
  refuel) stay in the orchestrator's store.

## Changes

- One story per PR. The PR changes only the story's write scope, normally
  `factories/<name>/**`.
- Factory PRs change desired state: plans, blueprints, regions, checks. They never change live
  state directly; the deploy step does that after merge.
- A blueprint PR includes its creative-sandbox validation results (throughput, footprint,
  inputs per output, tileability).
- `library/` changes are released as a new version (`library/VERSION`, `library/CHANGELOG.md`,
  tag `library-vX.Y.Z`). Factories adopt a release in a separate PR that changes only their pin.

## After merge

Merge → deploy (the builder reconciles the live world to the merged state, inside the story's
regions) → post-deploy checks → snapshot. A check that later fails opens an `incident`.
