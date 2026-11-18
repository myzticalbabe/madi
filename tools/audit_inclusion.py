#!/usr/bin/env python
# coding: utf-8
"""audit_inclusion -- the script soul-forge-gate.yml called but that never existed.

WHY
`soul-forge-gate.yml` has shipped into 18 repositories running
`python tools/audit_inclusion.py --path . --fail-on high`. That file did not
exist in any repository or in this monorepo, so every pull request in every one
of those repos was red on a step that could never have passed. This is the
missing half of the gate; `audit_accessibility.py` is the other.

WHAT IT CHECKS
Text-language inclusion only -- terminology that carries a documented bias in
technical prose, and `lang` on HTML documents (a screen reader picks its
pronunciation from it). Things that are unambiguously wrong are `high`; things
a house style guide may legitimately keep are `medium`; style preferences are
`low`. `--fail-on` decides where the exit code falls.

WHAT IT DELIBERATELY DOES NOT CLAIM
A word match is not a verdict. "master" is exempt on purpose: it is a real
branch name here (`EveUnleashed` defaults to `master`), and a gate that reddens
a repository for the name of its own default branch gets switched off within a
day. Every finding carries file, line and the matched text so a human can
adjudicate instead of trusting a count.

A scan that finds nothing prints the population it read, never just "clean":
a reading without a denominator is the defect this tree keeps re-learning
(HED-9).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

VERSION = "1.0.0"

TEXT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".rst",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs",
    ".html", ".htm", ".css", ".scss",
    ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg",
    ".sh", ".bash", ".ps1", ".bat", ".cmd",
}

EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", ".tox", "venv", ".venv", "env",
    ".venv-314t", "build", "dist", "site-packages", ".egg-info",
    "skills.pkg-archive", "archived", "_archive",
}

MAX_FILE_BYTES = 2_000_000

# (pattern, severity, why)
TERMS = [
    (re.compile(r"\bwhitelist(s|ed|ing)?\b", re.I), "medium",
     "allowlist/denylist is the neutral pair"),
    (re.compile(r"\bblacklist(s|ed|ing)?\b", re.I), "medium",
     "allowlist/denylist is the neutral pair"),
    (re.compile(r"\bgrandfather(ed|ing)?\b", re.I), "medium",
     "'legacy exemption' says the same thing without the historical referent"),
    (re.compile(r"\bman[-\s]?hours\b", re.I), "medium",
     "'person-hours' or 'engineer-hours'"),
    (re.compile(r"\bman[-\s]?months\b", re.I), "low",
     "'person-months'"),
    (re.compile(r"\bhe/she\b|\bs/he\b", re.I), "low",
     "'they' reads better and covers everyone"),
    (re.compile(r"\bsanity[-\s]?check(s|ed|ing)?\b", re.I), "low",
     "'smoke check' or 'quick check'"),
    (re.compile(r"\bdummy\s+(value|variable|data)\b", re.I), "low",
     "'placeholder' or 'sample'"),
]

SUPPRESS = re.compile(r"audit:\s*ignore", re.I)
HTML_HINT = re.compile(r"<html\b", re.I)
LANG_ATTR = re.compile(r"<html\b[^>]*\blang\s*=", re.I)

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}
FAIL_ON_RANK = {"never": 99, "high": 3, "medium": 2, "low": 1}


def iter_files(root: Path):
    """Yield candidate files, skipping vendored and generated trees."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in EXCLUDED_DIRS and not d.startswith(".")
        ]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield path


def scan_file(path: Path, root: Path):
    findings = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings

    rel = path.relative_to(root).as_posix()
    for lineno, line in enumerate(text.splitlines(), 1):
        if SUPPRESS.search(line):
            continue
        for pattern, severity, why in TERMS:
            match = pattern.search(line)
            if match:
                findings.append({
                    "file": rel,
                    "line": lineno,
                    "severity": severity,
                    "rule": "terminology",
                    "match": match.group(0),
                    "why": why,
                })

    if path.suffix.lower() in {".html", ".htm"} and HTML_HINT.search(text):
        first = text[:4000]
        if not LANG_ATTR.search(first):
            findings.append({
                "file": rel,
                "line": 1,
                "severity": "high",
                "rule": "html-lang",
                "match": "<html>",
                "why": "a screen reader picks its pronunciation from lang=",
            })
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Inclusion audit: terminology and document language.")
    parser.add_argument("--path", default=".", help="tree to audit")
    parser.add_argument("--fail-on", default="high",
                        choices=["high", "medium", "low", "never"],
                        help="lowest severity that fails the run (default: high)")
    parser.add_argument("--json", dest="json_path", default=None,
                        help="write the full report here")
    parser.add_argument("--quiet", action="store_true", help="counts only")
    args = parser.parse_args(argv)

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"audit_inclusion: not a directory: {root}", file=sys.stderr)
        return 2

    scanned = 0
    findings = []
    for path in iter_files(root):
        scanned += 1
        findings.extend(scan_file(path, root))

    counts = {s: 0 for s in SEVERITY_RANK}
    for f in findings:
        counts[f["severity"]] += 1

    if not args.quiet:
        for f in sorted(findings, key=lambda x: (-SEVERITY_RANK[x["severity"]],
                                                 x["file"], x["line"])):
            print(f"{f['severity']:6s} {f['file']}:{f['line']}  "
                  f"[{f['rule']}] {f['match']!r} -> {f['why']}")

    print(f"audit_inclusion {VERSION}: scanned {scanned} files under {root}")
    print(f"  findings: high={counts['high']} medium={counts['medium']} "
          f"low={counts['low']}  (total {len(findings)})")
    print(f"  fail-on={args.fail_on}")

    if args.json_path:
        Path(args.json_path).write_text(json.dumps({
            "tool": "audit_inclusion",
            "version": VERSION,
            "root": str(root),
            "files_scanned": scanned,
            "counts": counts,
            "fail_on": args.fail_on,
            "findings": findings,
        }, indent=2), encoding="utf-8")

    threshold = FAIL_ON_RANK[args.fail_on]
    failing = [f for f in findings if SEVERITY_RANK[f["severity"]] >= threshold]
    if failing:
        print(f"  FAIL: {len(failing)} finding(s) at or above {args.fail_on}")
        return 1
    print(f"  PASS: no finding at or above {args.fail_on}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
