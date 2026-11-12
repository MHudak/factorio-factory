#!/usr/bin/env python3
"""Validate the factory repo: schemas, consistency, library pins, regions, blueprints, rules.

Usage: python scripts/validate.py [--snapshot FILE ...]
Exit code 0 when everything is valid; problems are printed one per line.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import zlib
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"

# Rule 1: no runtime state in this repo (saves, databases, logs, status dumps).
FORBIDDEN_SUFFIXES = {".zip", ".db", ".sqlite", ".sqlite3", ".jsonl", ".log"}
FORBIDDEN_DIRS = {"state", "runs", "saves", ".factorio-data"}


def load_schema(name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((SCHEMAS / name).read_text()))


def check_schema(validator: Draft202012Validator, data: object, where: str, problems: list[str]) -> None:
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = "/".join(str(p) for p in err.path) or "(root)"
        problems.append(f"{where}: {path}: {err.message}")


def library_versions() -> set[str]:
    versions = {(ROOT / "library" / "VERSION").read_text().strip()}
    try:
        tags = subprocess.run(["git", "tag", "-l", "library-v*"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        versions |= {t.removeprefix("library-v") for t in tags.split()}
    except (OSError, subprocess.CalledProcessError):
        pass
    return versions


def decode_blueprint(text: str) -> dict:
    """A blueprint string: version byte '0' + base64(zlib(json))."""
    text = text.strip()
    if not text or text[0] != "0":
        raise ValueError("blueprint strings start with version byte '0'")
    return json.loads(zlib.decompress(base64.b64decode(text[1:])))


def overlaps(a: dict, b: dict) -> bool:
    return a["x1"] < b["x2"] and b["x1"] < a["x2"] and a["y1"] < b["y2"] and b["y1"] < a["y2"]


def validate_repo() -> list[str]:
    problems: list[str] = []
    factory_v, regions_v, checks_v = load_schema("factory.schema.json"), load_schema("regions.schema.json"), load_schema("checks.schema.json")
    versions = library_versions()
    library_checks = {p.stem for p in (ROOT / "library" / "checks").glob("*.yaml")}

    for p in sorted((ROOT / "library" / "checks").glob("*.yaml")):
        check_schema(checks_v, yaml.safe_load(p.read_text()), str(p.relative_to(ROOT)), problems)

    factories = sorted(d for d in (ROOT / "factories").iterdir() if d.is_dir())
    instances: dict[int, str] = {}
    for d in factories:
        rel = d.relative_to(ROOT)
        fy = d / "factory.yaml"
        if not fy.exists():
            problems.append(f"{rel}: missing factory.yaml")
            continue
        f = yaml.safe_load(fy.read_text())
        check_schema(factory_v, f, f"{rel}/factory.yaml", problems)
        if not isinstance(f, dict):
            continue
        if f.get("name") != d.name:
            problems.append(f"{rel}/factory.yaml: name '{f.get('name')}' must equal the directory name '{d.name}'")
        if f.get("library") and f["library"] not in versions:
            problems.append(f"{rel}/factory.yaml: library {f['library']} is not a release (tags library-v*, or library/VERSION)")
        for c in f.get("library_checks", []):
            if c not in library_checks:
                problems.append(f"{rel}/factory.yaml: library check '{c}' not found in library/checks/")
        inst = (f.get("world") or {}).get("server_instance")
        if inst is not None:
            if inst in instances:
                problems.append(f"{rel}/factory.yaml: server_instance {inst} is also used by {instances[inst]}")
            instances[inst] = d.name
        backend = (f.get("snapshots") or {}).get("backend")
        if backend in ("gateway", "rulesets-apps"):
            problems.append(f"{rel}/factory.yaml: snapshot backend '{backend}' is planned but not implemented yet; use repo-per-factory")

        ry = d / "regions.yaml"
        if ry.exists():
            r = yaml.safe_load(ry.read_text())
            check_schema(regions_v, r, f"{rel}/regions.yaml", problems)
            regs = (r or {}).get("regions") or []
            ids = [x.get("id") for x in regs]
            for dup in {i for i in ids if ids.count(i) > 1}:
                problems.append(f"{rel}/regions.yaml: duplicate region id '{dup}'")
            for i, a in enumerate(regs):
                ar = a.get("area") or {}
                if ar and (ar.get("x1", 0) >= ar.get("x2", 0) or ar.get("y1", 0) >= ar.get("y2", 0)):
                    problems.append(f"{rel}/regions.yaml: region '{a.get('id')}' needs x1 < x2 and y1 < y2")
                for b in regs[i + 1:]:
                    if a.get("area") and b.get("area") and overlaps(a["area"], b["area"]):
                        problems.append(f"{rel}/regions.yaml: regions '{a.get('id')}' and '{b.get('id')}' overlap")
            region_ids = set(ids)
        else:
            region_ids = set()

        for cp in sorted((d / "checks").glob("*.yaml")):
            c = yaml.safe_load(cp.read_text())
            check_schema(checks_v, c, str(cp.relative_to(ROOT)), problems)
            for chk in (c or {}).get("checks") or []:
                if chk.get("region") and chk["region"] not in region_ids:
                    problems.append(f"{cp.relative_to(ROOT)}: check '{chk.get('id')}' names unknown region '{chk['region']}'")

        for bp in sorted((d / "blueprints").glob("*")):
            if bp.name.startswith(".") or bp.suffix not in (".txt", ".blueprint"):
                continue
            try:
                data = decode_blueprint(bp.read_text())
                if not any(k in data for k in ("blueprint", "blueprint_book")):
                    problems.append(f"{bp.relative_to(ROOT)}: decodes, but is not a blueprint or blueprint book")
            except Exception as exc:  # noqa: BLE001 - report any decode failure
                problems.append(f"{bp.relative_to(ROOT)}: not a valid blueprint string ({exc})")

    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    for t in tracked:
        p = Path(t)
        if p.suffix in FORBIDDEN_SUFFIXES or FORBIDDEN_DIRS & set(p.parts):
            if not t.startswith("templates/"):
                problems.append(f"{t}: runtime state (saves, databases, logs, status) must not be committed here; see docs/architecture.md")
    return problems


def validate_snapshots(paths: list[str]) -> list[str]:
    problems: list[str] = []
    v = load_schema("snapshot.schema.json")
    for p in paths:
        check_schema(v, json.loads(Path(p).read_text()), p, problems)
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", nargs="*", default=[], help="also validate snapshot JSON files")
    args = ap.parse_args()
    problems = validate_repo() + validate_snapshots(args.snapshot)
    for p in problems:
        print(p)
    if not problems:
        print(f"ok: {len(list((ROOT / 'factories').iterdir()))} factories valid")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
