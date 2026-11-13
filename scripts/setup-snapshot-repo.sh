#!/usr/bin/env bash
# Protect a factory's snapshot repo and register the factory controller's deploy key.
# Usage: scripts/setup-snapshot-repo.sh OWNER/REPO path/to/controller_key.pub [principal-email]
# The principal defaults to <factory>@factorio-factory for a repo named factorio-snapshots-<factory>.
# Run by a maintainer (needs admin on the repo). Idempotent apart from re-adding the same key.
set -euo pipefail
repo="${1:?OWNER/REPO}"; pub="${2:?path to the controller public key}"
name="${repo##*/}"
if [ -n "${3:-}" ]; then
  principal="$3"; factory="${principal%@*}"
elif [[ "$name" == factorio-snapshots-?* ]]; then
  factory="${name#factorio-snapshots-}"; principal="${factory}@factorio-factory"
else
  echo "error: ${name} is not named factorio-snapshots-<factory>; pass the principal (<factory>@factorio-factory) as the third argument" >&2
  exit 2
fi

echo "Creating ruleset on ${repo} (no force pushes, no deletion, linear history) ..."
gh api "repos/${repo}/rulesets" --method POST --input - <<JSON >/dev/null
{
  "name": "snapshots-append-only",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}, {"type": "required_linear_history"}]
}
JSON

echo "Adding deploy key with write access ..."
gh api "repos/${repo}/keys" --method POST -f title="factory controller (${factory})" -f key="$(cat "$pub")" -F read_only=false >/dev/null

echo
echo "Add this line to allowed_signers in ${repo} (first signed commit by the controller):"
echo "${principal} namespaces=\"git\" $(cut -d' ' -f1,2 "$pub")"
echo
echo "The controller commits as ${principal} and signs with: git -c gpg.format=ssh -c user.signingkey=${pub} commit -S"
