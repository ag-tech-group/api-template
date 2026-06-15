#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 AG Technology Group LLC
# SPDX-License-Identifier: Apache-2.0

"""Stamp or verify SPDX license headers on Python sources.

Usage:
    python scripts/license_header.py --check    verify every tracked .py file (CI)
    python scripts/license_header.py --fix      add the header where missing

Default mode is --check. Re-running is safe: a file that already carries an
SPDX identifier in its first lines is left untouched (idempotent), so the CI
check and a manual --fix can never disagree.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HEADER = (
    "# SPDX-FileCopyrightText: 2026 AG Technology Group LLC\n"
    "# SPDX-License-Identifier: Apache-2.0\n"
)

GENERATED_BANNER = re.compile(r"@generated|do not edit|automatically generated", re.IGNORECASE)
ENCODING = re.compile(r"coding[:=]\s*[-\w.]+")


def tracked_py_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def classify(text: str) -> str:
    """Return "stamped", "skip", or "needs"."""
    lines = text.splitlines()
    if GENERATED_BANNER.search("\n".join(lines[:15])):
        return "skip"
    if "SPDX-License-Identifier" in "\n".join(lines[:10]):
        return "stamped"
    return "needs"


def apply_header(text: str) -> str:
    """Insert the header below a shebang/encoding line, above everything else."""
    lines = text.splitlines(keepends=True)
    prefix: list[str] = []
    if lines and lines[0].startswith("#!"):
        prefix.append(lines.pop(0))
    if lines and lines[0].lstrip().startswith("#") and ENCODING.search(lines[0]):
        prefix.append(lines.pop(0))
    while lines and lines[0].strip() == "":
        lines.pop(0)
    body = "".join(lines)
    separator = "\n" if body else ""
    return "".join(prefix) + HEADER + separator + body


def main() -> int:
    args = sys.argv[1:]
    fix = "--fix" in args
    explicit = [a for a in args if not a.startswith("--")]
    files = explicit or tracked_py_files()

    stamped: list[str] = []
    already: list[str] = []
    skipped: list[str] = []
    missing: list[str] = []

    for name in files:
        path = Path(name)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        status = classify(text)
        if status == "skip":
            skipped.append(name)
        elif status == "stamped":
            already.append(name)
        elif fix:
            path.write_text(apply_header(text), encoding="utf-8")
            stamped.append(name)
        else:
            missing.append(name)

    if fix:
        print(
            f"license-header: stamped {len(stamped)}, already {len(already)}, skipped {len(skipped)}"
        )
        for name in stamped:
            print(f"  + {name}")
    elif missing:
        print(f"license-header: {len(missing)} file(s) missing an SPDX header:", file=sys.stderr)
        for name in missing:
            print(f"  - {name}", file=sys.stderr)
        print('Run "uv run python scripts/license_header.py --fix" to add them.', file=sys.stderr)
        return 1
    else:
        print(f"license-header: OK — {len(already)} stamped, {len(skipped)} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
