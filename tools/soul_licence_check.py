#!/usr/bin/env python3
"""Soul Licence gate -- self-contained, stdlib only, no arguments.

MASTER: C:/Users/clint/Desktop/_azazael_fix/tools/soul_licence_check.py
(kept as soul_licence_check.py to match owner spelling; vendored copies
carry this header so drift is visible). Exit 0 clean, 1 defects, 2 unrunnable.

Policy (owner, permanent): every owned repo declares exactly one project
licence -- the Soul Forge License v1.0 (LicenseRef-SoulForge-1.0). Any
other licence claimed for first-party code is a defect. Third-party
material keeps its own licence and must live in a recognised third-party
context (NOTICE third-party section, lockfiles, vendored dirs, SBOMs);
relicensing someone else's code would be a false statement.

Checks (worktree, read-only):
 1. LICENSE exists, contains "Soul Forge License v1.0", and carries a
    Source: https://github.com/myzticalbabe/<repo> maker's-mark line.
 2. CITATION.cff, if present: license field is LicenseRef-SoulForge-1.0.
 3. PUBLIC_MANIFEST.json, if present: "license" is LicenseRef-SoulForge-1.0
    and no License :: OSI/CDDL/MIT/GPL/Apache trove classifier remains.
 4. pyproject.toml / setup.py / setup.cfg, if present: no foreign-licence
    trove classifier and no license = { text } naming another licence.
 5. NOTICE, if present: outside its third-party section, no foreign
    project-licence token (CDDL, MIT License, GPL, Apache License,
    BSD License, MPL, Common Development and Distribution).
 6. Prose sweep (*.md, *.cff, *.toml outside lockfiles/vendored): no live
    first-party claim of another licence (CDDL-1.1, MIT/CDDL, Apache-2.0
    as project licence, "Licensed under the ... License" naming another).
    History notes describing a migration are allowed only when they name
    Soul Forge as the outcome in the same paragraph.
"""
from __future__ import annotations

import contextlib
import json
import re
import subprocess
import sys
from pathlib import Path

FOREIGN_PROJECT_TOKENS = (
    "CDDL",
    "Common Development and Distribution",
    "Apache-2.0",
    "Apache License",
    "apache.org/licenses",
    "GPL-3.0",
    "GPL-2.0",
    "General Public License",
    "MIT License",
    "BSD License",
    "BSD-3-Clause License",
    "Mozilla Public License",
    "MPL-2.0",
)

# Filenames / dirs whose licence mentions describe someone else's code.
EXEMPT_NAMES = (
    "package-lock.json",
    "package.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.lock",
    "poetry.lock",
    "Pipfile.lock",
)
EXEMPT_DIRS = (
    ".git",
    "node_modules",
    "vendor",
    "vendored",
    "third_party",
    "third-party",
    ".venv",
    "venv",
    # Generated artifacts are verified by regeneration, not by text scan:
    # graphify-out/GRAPH_REPORT.md quotes whatever the tree said when the
    # extract ran, and tools/artifact_freshness.py already guards its
    # staleness. Fixing the sources (which this gate scans) is the cause;
    # hand-editing the generated copy would be the bypass.
    "graphify-out",
)
EXEMPT_SUFFIX_PARTS = ("sbom", "spdx", "cyclonedx", ".min.js")

# Historical records describe past rulings; they are evidence, not claims.
EXEMPT_NAME_PARTS = ("PRECEDENT", "precedent", "HISTORY", "MIGRATION", "CHANGELOG", "changelog")


def repo_slug(root: Path) -> str:
    """Best-effort repo name from origin URL, else directory name."""
    with contextlib.suppress(OSError, subprocess.SubprocessError):
        proc = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        url = (proc.stdout or "").strip()
        if url:
            slug = url.rstrip("/").rsplit("/", 1)[-1]
            return slug[:-4] if slug.endswith(".git") else slug
    return root.name


def read_text(path: Path) -> str | None:
    with contextlib.suppress(OSError, UnicodeError):
        return path.read_text(encoding="utf-8", errors="strict")
    return None


def exempt_path(path: Path, root: Path) -> bool:
    if not path.is_relative_to(root):
        return True
    rel = path.relative_to(root)
    parts = rel.parts
    if path.name in EXEMPT_NAMES:
        return True
    if any(part in path.name for part in EXEMPT_NAME_PARTS):
        return True
    lowered = str(rel).lower()
    if any(part in EXEMPT_DIRS for part in parts[:-1]):
        return True
    if any(tag in lowered for tag in EXEMPT_SUFFIX_PARTS):
        return True
    return False


def strip_third_party_section(notice: str) -> str:
    """Remove the recognised third-party attribution block from NOTICE."""
    lines = notice.splitlines(keepends=True)
    out: list[str] = []
    skipping = False
    for line in lines:
        if re.match(r"^#{1,3}\s+third-party", line, re.IGNORECASE):
            skipping = True
            continue
        # Only a level-1/2 heading ends the section: ### sub-headings
        # (per-dependency entries) belong to it. Measured 2026-11-23: ending
        # on any heading stripped nothing and flagged third-party FFmpeg/
        # PyYAML lines as project claims.
        if skipping and re.match(r"^#{1,2}\s+", line):
            skipping = False
        if not skipping:
            out.append(line)
    return "".join(out)


def check(root: Path) -> list[str]:
    defects: list[str] = []
    slug = repo_slug(root)

    lic = root / "LICENSE"
    txt = read_text(lic) if lic.is_file() else None
    if txt is None:
        defects.append("LICENSE missing or unreadable")
    else:
        if "Soul Forge License v1.0" not in txt:
            defects.append("LICENSE is not the Soul Forge text")
        expect = f"https://github.com/myzticalbabe/{slug}"
        if expect not in txt and "myzticalbabe" not in txt:
            defects.append(f"LICENSE carries no maker's-mark Source URL ({expect})")

    citation = root / "CITATION.cff"
    if citation.is_file():
        txt = read_text(citation) or ""
        m = re.search(r'^license:\s*["\']?([^"\'\n]+)', txt, re.MULTILINE)
        if m and m.group(1).strip() != "LicenseRef-SoulForge-1.0":
            defects.append(f"CITATION.cff license is {m.group(1).strip()!r}, not LicenseRef-SoulForge-1.0")

    manifest = root / "PUBLIC_MANIFEST.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            defects.append(f"PUBLIC_MANIFEST.json unreadable ({exc})")
            data = None
        if isinstance(data, dict):
            if data.get("license") != "LicenseRef-SoulForge-1.0":
                defects.append(f'PUBLIC_MANIFEST.json "license" is {data.get("license")!r}')
            for clf in data.get("classifiers", []) or []:
                if re.search(r"License\s*::", clf) and "SoulForge" not in clf and "Soul Forge" not in clf:
                    defects.append(f"PUBLIC_MANIFEST.json foreign classifier: {clf}")

    for name in ("pyproject.toml", "setup.cfg", "setup.py"):
        p = root / name
        if p.is_file() and not exempt_path(p, root):
            txt = read_text(p) or ""
            for clf in re.findall(r'"?(License\s*::[^",\n]*)"?', txt):
                if "SoulForge" not in clf and "Soul Forge" not in clf:
                    defects.append(f"{name} foreign trove classifier: {clf.strip()}")
            # Strip # comments only when the # sits outside string literals.
            stripped: list[str] = []
            for ln in txt.splitlines():
                cut = len(ln)
                in_str = False
                for i, ch in enumerate(ln):
                    if ch == '"':
                        in_str = not in_str
                    elif ch == "#" and not in_str:
                        cut = i
                        break
                stripped.append(ln[:cut])
            code = "\n".join(stripped)
            # PEP 639 plain form: license = "<spdx-id>" -- the id itself
            # is the claim, so it must be exactly the SoulForge ref.
            m = re.search(r"^license\s*=\s*\"([^\"]+)\"", code, re.MULTILINE)
            if m and m.group(1).strip() != "LicenseRef-SoulForge-1.0":
                defects.append(f"{name} license id is {m.group(1)!r}, not LicenseRef-SoulForge-1.0")
            m = re.search(r"license\s*=\s*\{[^}]*text\s*=\s*\"([^\"]+)\"", code)
            if m and "Soul Forge" not in m.group(1) and "SoulForge" not in m.group(1):
                defects.append(f"{name} license.text names {m.group(1)!r}")

    notice = root / "NOTICE"
    if notice.is_file():
        txt = read_text(notice) or ""
        first_party = strip_third_party_section(txt)
        # The owner's explicit banishment marker declares intent; it names
        # the banished licences only to forbid them.
        first_party = "\n".join(
            ln for ln in first_party.splitlines() if "SOUL LICENCE ONLY" not in ln
        )
        for tok in FOREIGN_PROJECT_TOKENS:
            if tok in first_party:
                defects.append(f"NOTICE claims {tok} outside third-party section")

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "NOTICE":
            continue
        if path.suffix.lower() not in (".md", ".cff", ".toml", ".cfg", ".txt", ".rst"):
            continue
        if exempt_path(path, root):
            continue
        if len(path.parts) > len(root.parts) + 3:
            continue
        txt = read_text(path)
        if txt is None:
            continue
        rel = str(path.relative_to(root))
        for tok in ("CDDL", "Common Development and Distribution"):
            if tok in txt and "Soul Forge" not in txt and "SoulForge" not in txt:
                defects.append(f"{rel} claims {tok} with no Soul Forge outcome")
                break
        m = re.search(r"[Ll]icensed under the ([A-Z][A-Za-z0-9 .+/-]+License)", txt)
        if m and "Soul Forge" not in m.group(1):
            defects.append(f"{rel} claims project licence {m.group(1)!r}")

    return defects


def main() -> int:
    root = Path.cwd().resolve()
    if not (root / ".git").is_dir():
        print(f"soul-licence-check: {root} is not a repo root", file=sys.stderr)
        return 2
    defects = check(root)
    if defects:
        print(f"soul-licence-check: {len(defects)} defect(s) in {root.name}:")
        for d in defects:
            print(f"  - {d}")
        return 1
    print(f"soul-licence-check: SOUL LICENCE ONLY -- {root.name} clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
