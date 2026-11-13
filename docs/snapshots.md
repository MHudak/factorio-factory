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

A maintainer does this once per factory (agents cannot create repos). The example is for
`rocket-team`; the controller's key pair is `~/.ssh/rocket-team-snapshots`.

```bash
# 1. Create an empty repo and fill it from the template in this repo
gh repo create MHudak/factorio-snapshots-rocket-team --public
git clone git@github.com:MHudak/factorio-snapshots-rocket-team.git
cp -r templates/snapshot-repo/. factorio-snapshots-rocket-team/
```

Make the first commit with your GitHub noreply address (`<id>+<user>@users.noreply.github.com`),
not a personal one: the repo is public and its history cannot be rewritten once the ruleset is
on. The audit exempts this first commit, so it does not need to be signed.

```bash
# 2. Apply protection, register the deploy key, print the allowed_signers line
scripts/setup-snapshot-repo.sh MHudak/factorio-snapshots-rocket-team ~/.ssh/rocket-team-snapshots.pub
```

The principal defaults to `<factory>@factorio-factory` (here `rocket-team@factorio-factory`),
the email the writer commits as. For a repo not named `factorio-snapshots-<factory>`, pass it
as a third argument.

The setup script creates the ruleset (no force pushes, no deletion, linear history) and adds
the deploy key with write access. Commit the `allowed_signers` line it prints together with the
template in step 1, then push.

## Running the writer

The writer is `fclaude snapshot` in
[factorio-claude](https://github.com/MHudak/factorio-claude#snapshots-for-factorio-factory). It
runs on the factory's host, next to its Factorio server (`FCLAUDE_INSTANCE` set to the
factory's `world.server_instance`), and is the snapshot repo's only writer.

```bash
# Check what would be written; writes nothing
fclaude snapshot factories/rocket-team --dry-run

# One snapshot now (trigger manual, or --trigger incident)
fclaude snapshot factories/rocket-team --repo-dir ~/snapshots/rocket-team \
  --signing-key ~/.ssh/rocket-team-snapshots --deploy-key ~/.ssh/rocket-team-snapshots

# The factory controller: runs until stopped
fclaude snapshot factories/rocket-team --repo-dir ~/snapshots/rocket-team \
  --signing-key ~/.ssh/rocket-team-snapshots --deploy-key ~/.ssh/rocket-team-snapshots --watch
```

| Credential | Used for | Needed by |
|---|---|---|
| Signing key (SSH) | Signing each commit; its public half is in `allowed_signers` | Every write |
| Deploy key (SSH, write) | Pushing to the snapshot repo; may be the same key pair | Every push, unless the clone has other credentials |
| Token that may write releases (`gh`) | Attaching milestone saves (`--upload-saves`) | Only with `--upload-saves`; a deploy key cannot create releases |

**When snapshots are taken (`--watch`).**

- **Milestone:** when one of the factory goal's stages (factorio-claude
  `goals/<goal>.toml`) is first met. The tick it was first met is kept in the game save, so
  milestones travel with saves and the writer keeps no state of its own. Milestones already met
  when the writer first runs are recorded at that tick. With `snapshots.milestone_saves`, the
  game is saved and the snapshot records the save's SHA-256 and size (and URL, with
  `--upload-saves`).
- **Interval:** every `snapshots.interval_minutes` of **game** time since the last snapshot,
  read back from `latest.json`. A paused game takes no interval snapshots.

**Safety checks.** The writer refuses to write if:

- the running game's seed differs from `factory.yaml` (wrong server instance);
- the clone has uncommitted changes;
- the committer email is not in `allowed_signers`.

It also verifies each new commit against `allowed_signers` before pushing. If the commit does
not verify, it is undone and nothing is pushed.
