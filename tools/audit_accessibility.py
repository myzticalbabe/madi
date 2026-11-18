#!/usr/bin/env python
# coding: utf-8
"""audit_accessibility -- the second script soul-forge-gate.yml called but that never existed.

WHY
`soul-forge-gate.yml` runs `python tools/audit_accessibility.py --path .
--fail-on high` in 18 repositories. The file was absent everywhere, so the gate
was red on every pull request by construction. Its sibling
`audit_inclusion.py` covers language; this one covers the document.

WHAT IT CHECKS
Static, deterministic HTML rules that a screen reader or keyboard user trips
over, parsed with `html.parser` (no browser, no network, no dependencies):

  high    an image with no `alt` attribute at all (`alt=""` is valid -- it
          declares the image decorative, and the difference between absent and
          empty is the whole point), and a form control with no accessible name
          from label[for], aria-label, aria-labelledby or title.
  medium  a document with no `lang`, no `<title>`, a link or button with no
          text and no aria-label, or a positive `tabindex`.
  low     a heading level that skips (h1 -> h3), a second `<h1>`.

WHAT IT DELIBERATELY DOES NOT CLAIM
This is not a WCAG conformance verdict. It cannot see rendered contrast,
focus order, motion, or anything behind script. `--axe` exists for that: when
`playwright` is importable it runs axe against each page and merges the results.
When it is not, the report says `axe: skipped (playwright not installed)` and
still exits on the static findings -- an unavailable reading is recorded, never
rounded into a pass (HED-6).

Every run prints how many files it read and how many it skipped as
non-HTML, so a green line carries its denominator.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from html.parser import HTMLParser
from pathlib import Path

VERSION = "1.1.0"

EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".tox", "venv", ".venv", "env", ".venv-314t",
    "build", "dist", "site-packages", ".egg-info", "skills.pkg-archive",
    "archived", "_archive",
}

MAX_FILE_BYTES = 3_000_000
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}
CONTROLS = {"input", "select", "textarea"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}
FAIL_ON_RANK = {"never": 99, "high": 3, "medium": 2, "low": 1}


class PageScan(HTMLParser):
    """One pass: collect tags, label targets and inline text of links/buttons."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []            # (tag, attrs_dict, line)
        self.label_for = set()
        self._capture = None      # [tag, attrs_dict, pile of text]
        self._depth = 0
        self.pending = []         # (tag, attrs_dict, joined text, line)

    def handle_starttag(self, tag, attrs):
        attr = {k.lower(): (v if v is not None else "") for k, v in attrs}
        self.tags.append((tag, attr, self.getpos()[0]))
        if tag == "label" and attr.get("for"):
            self.label_for.add(attr["for"].strip())
        if tag in ("a", "button") and self._capture is None:
            self._capture = [tag, attr, [], self.getpos()[0]]
            self._depth = 1
        elif self._capture is not None and tag not in VOID:
            self._depth += 1

    def handle_data(self, data):
        if self._capture is not None:
            self._capture[2].append(data)

    def handle_endtag(self, tag):
        if self._capture is None:
            return
        if tag == self._capture[0]:
            self._depth -= 1
            if self._depth <= 0:
                joined = " ".join("".join(self._capture[2]).split())
                self.pending.append(
                    (self._capture[0], self._capture[1], joined, self._capture[3]))
                self._capture = None
        elif tag not in VOID:
            self._depth -= 1


def has_name(attr, label_targets):
    if attr.get("aria-label", "").strip() or attr.get("aria-labelledby", "").strip():
        return True
    if attr.get("title", "").strip():
        return True
    element_id = attr.get("id", "").strip()
    return bool(element_id and element_id in label_targets)


def scan_file(path: Path, root: Path, use_axe: bool):
    rel = path.relative_to(root).as_posix()
    findings = []

    def add(severity, rule, line, match, why):
        findings.append({"file": rel, "line": line, "severity": severity,
                         "rule": rule, "match": match, "why": why})

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings

    scanner = PageScan()
    try:
        scanner.feed(text)
        scanner.close()
    except Exception as exc:  # a parser that dies must not read as clean
        add("high", "unparseable", 1, "<html>",
            f"html.parser raised {type(exc).__name__}: {exc}")
        return findings

    label_targets = scanner.label_for | {
        attr.get("id", "").strip()
        for tag, attr, _ in scanner.tags
        if tag == "label" and attr.get("id")
    }

    heading_levels = []
    for tag, attr, line in scanner.tags:
        if tag == "img" and "alt" not in attr:
            add("high", "img-alt", line, "<img>",
                "no alt attribute; use alt=\"\" if the image is decorative")
        if tag in CONTROLS:
            kind = attr.get("type", "text").lower()
            if kind in ("hidden", "submit", "reset", "button", "image"):
                continue
            if not has_name(attr, label_targets):
                add("high", "control-name", line, f"<{tag}>",
                    "no accessible name from label[for], aria-label, "
                    "aria-labelledby or title")
        if tag == "html" and not attr.get("lang", "").strip():
            add("medium", "html-lang", line, "<html>",
                "a screen reader picks its pronunciation from lang=")
        if tag in HEADINGS:
            heading_levels.append((int(tag[1]), line))
        if tag in ("a", "button"):
            tabindex = attr.get("tabindex", "").strip()
            if tabindex.lstrip("+").isdigit() and int(tabindex) > 0:
                add("medium", "tabindex-positive", line, f"<{tag}>",
                    "a positive tabindex reorders keyboard focus for everyone")

    if not any(tag == "title" for tag, _, _ in scanner.tags):
        add("medium", "missing-title", 1, "<title>",
            "a document with no title is announced as its URL")

    for tag, attr, content, line in scanner.pending:
        if content.strip():
            continue
        if has_name(attr, label_targets):
            continue
        add("medium", "empty-control", line, f"<{tag}>",
            "link or button with no text and no aria-label")

    previous = None
    for level, line in heading_levels:
        if previous is not None and level > previous + 1:
            add("low", "heading-skip", line, f"<h{level}>",
                f"heading level jumps from h{previous} to h{level}")
        previous = level
    if sum(1 for level, _ in heading_levels if level == 1) > 1:
        add("low", "multiple-h1", 1, "<h1>", "more than one h1 on the page")

    if use_axe:
        findings.extend(run_axe(path, rel))
    return findings


def run_axe(path: Path, rel: str):
    """axe-core through playwright, only when the browser stack is importable."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception:
        return [{"file": rel, "line": 1, "severity": "low", "rule": "axe-skipped",
                 "match": "axe",
                 "why": "playwright not installed; axe not run (recorded, not passed)"}]
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as play:
            browser = play.chromium.launch()
            page = browser.new_page()
            page.goto(path.resolve().as_uri())
            page.add_script_tag(
                url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js")
            violations = page.evaluate(
                "() => axe.run().then(r => r.violations.map(v => "
                "({id: v.id, impact: v.impact, help: v.help})))")
            browser.close()
    except Exception as exc:
        return [{"file": rel, "line": 1, "severity": "low", "rule": "axe-skipped",
                 "match": "axe",
                 "why": f"axe could not run: {type(exc).__name__} (recorded, not passed)"}]

    out = []
    for violation in violations or []:
        impact = (violation.get("impact") or "minor").lower()
        severity = {"critical": "high", "serious": "high",
                    "moderate": "medium", "minor": "low"}.get(impact, "low")
        out.append({"file": rel, "line": 1, "severity": severity,
                    "rule": f"axe:{violation.get('id')}",
                    "match": violation.get("id", ""),
                    "why": violation.get("help", "")})
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Accessibility audit: static HTML rules, optional axe.")
    parser.add_argument("--path", default=".", help="tree to audit")
    parser.add_argument("--fail-on", default="high",
                        choices=["high", "medium", "low", "never"],
                        help="lowest severity that fails the run (default: high)")
    parser.add_argument("--axe", action="store_true",
                        help="also run axe-core via playwright when available")
    parser.add_argument("--json", dest="json_path", default=None,
                        help="write the full report here")
    parser.add_argument("--quiet", action="store_true", help="counts only")
    args = parser.parse_args(argv)

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"audit_accessibility: not a directory: {root}", file=sys.stderr)
        return 2

    pages, skipped = [], 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d.lower() not in EXCLUDED_DIRS and not d.startswith(".")]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix.lower() not in {".html", ".htm"}:
                skipped += 1
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    skipped += 1
                    continue
            except OSError:
                continue
            pages.append(path)

    findings = []
    for path in pages:
        findings.extend(scan_file(path, root, args.axe))

    counts = {s: 0 for s in SEVERITY_RANK}
    for f in findings:
        counts[f["severity"]] += 1

    axe_state = "requested" if args.axe else "not requested"
    if args.axe and any(f["rule"] == "axe-skipped" for f in findings):
        axe_state = next(f["why"] for f in findings if f["rule"] == "axe-skipped")

    if not args.quiet:
        for f in sorted(findings, key=lambda x: (-SEVERITY_RANK[x["severity"]],
                                                 x["file"], x["line"])):
            print(f"{f['severity']:6s} {f['file']}:{f['line']}  "
                  f"[{f['rule']}] {f['why']}")

    print(f"audit_accessibility {VERSION}: scanned {len(pages)} HTML file(s) "
          f"under {root} ({skipped} non-HTML file(s) skipped)")
    print(f"  axe: {axe_state}")
    print(f"  findings: high={counts['high']} medium={counts['medium']} "
          f"low={counts['low']}  (total {len(findings)})")
    print(f"  fail-on={args.fail_on}")

    if args.json_path:
        Path(args.json_path).write_text(json.dumps({
            "tool": "audit_accessibility",
            "version": VERSION,
            "root": str(root),
            "html_files_scanned": len(pages),
            "non_html_skipped": skipped,
            "axe": axe_state,
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
