# Library changelog

Factories pin a release in `factory.yaml` (`library: X.Y.Z`). A release is the git tag
`library-vX.Y.Z`. `library/` on `main` is the next release. To upgrade a factory, open a PR
that changes only its pin, so each factory adopts library changes deliberately.

## 0.1.0

- `checks/rocket-milestones.yaml`: the 9 rocket milestones used by the factorio-claude pilots.
