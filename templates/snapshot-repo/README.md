# Factory snapshots

Append-only observed-state snapshots of one factorio-factory factory. Written only by that
factory's controller. Format and rules: `docs/snapshots.md` in
[factorio-factory](https://github.com/MHudak/factorio-factory).

- `latest.json`: the most recent snapshot
- `snapshots/YYYY/MM/DD/<HHMMSS>Z.json`: every snapshot
- Releases tagged `milestone/<id>`: the game save taken when that milestone was first reached

Do not commit here by hand. `main` is protected: no force pushes, no deletion, linear history,
and signed commits only. Every commit must be signed by a key listed in `allowed_signers`, and
`audit-signatures.yml` checks this on every push and daily.
