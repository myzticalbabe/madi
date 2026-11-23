#!/usr/bin/env python3
"""
requiem.py — Final words for a failed component.

This module captures the last state of a component that has been
deprecated, removed, or failed in production. It serves as a
forensic record for post-mortem analysis.

Usage:
    python requiem.py --component <name> --reason <reason> [--output <file>]
"""

import argparse
import json
import sys
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List


@dataclass
class RequiemRecord:
    component: str
    reason: str
    timestamp: str
    version: str
    git_commit: Optional[str]
    last_known_state: str
    error_trace: Optional[str]
    dependencies: List[str]
    dependents: List[str]
    migration_path: Optional[str]
    lessons_learned: List[str]
    tags: List[str]


def get_git_commit() -> Optional[str]:
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def capture_exception() -> Optional[str]:
    exc_type, exc_value, exc_tb = sys.exc_info()
    if exc_type is not None:
        return ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Record the final state of a failed/deprecated component"
    )
    parser.add_argument('--component', required=True, help='Component name')
    parser.add_argument('--reason', required=True, help='Reason for demise')
    parser.add_argument('--version', default='unknown', help='Component version')
    parser.add_argument('--state', default='unknown', help='Last known operational state')
    parser.add_argument('--error', help='Error message or traceback')
    parser.add_argument('--deps', nargs='*', default=[], help='Dependencies')
    parser.add_argument('--dependents', nargs='*', default=[], help='Components that depend on this')
    parser.add_argument('--migration', help='Migration path for users')
    parser.add_argument('--lessons', nargs='*', default=[], help='Lessons learned')
    parser.add_argument('--tags', nargs='*', default=[], help='Tags for categorization')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    record = RequiemRecord(
        component=args.component,
        reason=args.reason,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=args.version,
        git_commit=get_git_commit(),
        last_known_state=args.state,
        error_trace=args.error or capture_exception(),
        dependencies=args.deps,
        dependents=args.dependents,
        migration_path=args.migration,
        lessons_learned=args.lessons,
        tags=args.tags
    )
    
    output = json.dumps(asdict(record), indent=2)
    
    if args.output:
        Path(args.output).write_text(output)
        print(f"Requiem written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
