# Snapshots

A snapshot is a periodic, append-only record of a factory's **observed** state. Snapshots are
not live status (that lives in the factory's store), and they never touch this repo.

## Where they live: one snapshot repo per factory (option A)

Each factory has its own snapshot repo, e.g. `MHudak/factorio-snapshots-rocket-team`, created
from [`templates/snapshot-repo/`](../templates/snapshot-repo/). This is the current backend
because a GitHub repository is the native permission boundary. A deploy key or fine-grained
token scoped to one repo can write only that repo. So each factory can push only its own
snapshots, enforced by GitHub, not by our code.

| | Snapshot repo per factory |
|---|---|
| Writer | That factory's controller only, with a deploy key scoped to the repo |
| Branch | `main`, append-only |
| Protection (ruleset) | No force pushes, no deletion, linear history |
| Signatures | The controller signs every commit with its own SSH key. The audit workflow verifies each commit against `allowed_signers` (on every push and daily) and opens an incident if any commit is unsigned or signed by another key |

**Why GitHub's "require signed commits" rule is not used here.** GitHub verifies signatures
only against signing keys registered to a GitHub *user account*. A deploy key cannot be one, so
with that rule enabled GitHub would reject every controller push. The repo's own
`allowed_signers` is the trust root instead; the audit was tested with good-key, foreign-key
and unsigned commits. Backend C avoids this, because commits a GitHub App makes through the API
are verified by GitHub.

Planned alternative backends (configurable per factory):

- **B. One snapshot repo plus a snapshot gateway.** A small service holds the only write
  credential, authenticates factory controllers and maps each factory to `snapshots/<factory>`.
  Enforcement lives in our code. Best for a fleet-wide view or more than about 10 factories.
- **C. One snapshot repo plus rulesets plus one GitHub App per factory.** Each
  `snapshots/<factory>` branch has a ruleset that only that factory's App may bypass.
  Enforcement lives in GitHub, at the cost of n Apps, and App commits are signature-verified by
  GitHub.

## What goes in git, and what doesn't

| Content | Where | Frequency |
|---|---|---|
| Text snapshot (`snapshot.schema.json`) | Committed: `snapshots/YYYY/MM/DD/<HHMMSS>Z.json`, plus `latest.json` | Hourly, at every milestone, and on demand |
| Milestone save (binary zip, MBs to 100+ MB) | **Release asset** tagged `milestone/<id>`, referenced by URL and SHA-256 from the snapshot | Only when a milestone is first reached |
| Live status, logs | Not in git | — |

Saves are zips, which git cannot delta-compress. Committing them hourly would grow each repo
by the full save size every hour. Release assets (or object storage) keep the repo small, and
the SHA-256 in the snapshot keeps the reference tamper-evident.

## Snapshot format

[`schemas/snapshot.schema.json`](../schemas/snapshot.schema.json) defines it. Summary:

```json
{
  "schema_version": "1.0.0",
  "factory": "rocket-team",
  "taken_at": "2026-11-12T18:00:00Z",
  "trigger": "interval | milestone | manual | incident",
  "game": {"tick": 864000, "minutes": 240.0, "version": "2.1.24", "seed": 2024},
  "desired_state_commit": "<factorio-factory sha last deployed>",
  "milestones": {"burner-mining": 28800, "steam-power": 51000},
  "research": {"researched": 27, "current": "advanced-circuit", "progress": 0.4},
  "production_per_minute": {"iron-plate": 182.5, "automation-science-pack": 10.0},
  "entity_counts": {"stone-furnace": 24, "assembling-machine-2": 12},
  "power": {"production_kw": 3600, "consumption_kw": 2900},
  "open_incidents": [12, 15],
  "save": {"kind": "milestone", "url": "https://github.com/.../releases/download/milestone%2Foil/save.zip", "sha256": "…", "bytes": 18234567}
}
```

## Setting up a factory's snapshot repo

```bash
# 1. Create the repo from the template; a maintainer creates repos (agents cannot)
gh repo create MHudak/factorio-snapshots-rocket-team --public --template MHudak/factorio-factory-snapshot-template
# or copy templates/snapshot-repo/ into an empty repo

# 2. Apply protection and register the factory's deploy key and signing key
scripts/setup-snapshot-repo.sh MHudak/factorio-snapshots-rocket-team ~/.ssh/rocket-team-snapshots.pub
```

The setup script creates the ruleset (no force pushes, no deletion, linear history) and adds
the deploy key with write access. It also prints the `allowed_signers` line to commit. The
controller must commit with the email that line names, and sign with
`git -c gpg.format=ssh -c user.signingkey=<key>.pub commit -S`.
