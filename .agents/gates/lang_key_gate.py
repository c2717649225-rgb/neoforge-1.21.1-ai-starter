"""Language Key Gate (lang_key_gate.py).

Scans Java source files under ``src/main/java`` for ``Component.translatable("...")``
literal keys and dynamic key expressions. Compares literal keys against all language
JSON files under ``src/main/resources/assets/*/lang/`` and ``src/generated/resources/assets/*/lang/``.

Dual-track reporting policy:
  - Missing literal keys (e.g. Component.translatable("modid.foo")) -> FAIL (Exit code 1, Hard Error)
  - Unresolvable dynamic keys (e.g. Component.translatable(varName)) -> WARNING (Exit code 0, Info only)

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

LITERAL_KEY_REGEX = re.compile(
    r'Component\s*\.\s*translatable(?:WithFallback)?\s*\(\s*"([^"]+)"\s*(?=[,\)])',
    re.MULTILINE,
)
CONCAT_PREFIX_REGEX = re.compile(
    r'Component\s*\.\s*translatable(?:WithFallback)?\s*\(\s*"([^"]+)"\s*\+',
    re.MULTILINE,
)
DYNAMIC_KEY_REGEX = re.compile(
    r'Component\s*\.\s*translatable(?:WithFallback)?\s*\(\s*([^"\s][^,\)]*)',
    re.MULTILINE,
)


def load_lang_keys(project_dir: Path) -> Set[str]:
    """Collect all defined keys across all language JSON files."""
    keys: Set[str] = set()
    lang_dirs = [
        project_dir / "src" / "main" / "resources" / "assets",
        project_dir / "src" / "generated" / "resources" / "assets",
    ]
    for assets_dir in lang_dirs:
        if not assets_dir.is_dir():
            continue
        for lang_file in assets_dir.rglob("lang/*.json"):
            if not lang_file.is_file():
                continue
            try:
                with open(lang_file, "r", encoding="utf-8", errors="replace") as fh:
                    data = json.load(fh)
                    if isinstance(data, dict):
                        keys.update(data.keys())
            except (OSError, json.JSONDecodeError):
                pass
    return keys


def scan_java_sources(src_dir: Path) -> Tuple[List[Tuple[Path, int, str]], List[Tuple[Path, int, str]]]:
    """Scan Java files for literal and dynamic translatable keys.
    
    Returns:
        (literals, dynamics): lists of (file_path, line_number, key_or_expression)
    """
    literals: List[Tuple[Path, int, str]] = []
    dynamics: List[Tuple[Path, int, str]] = []

    if not src_dir.is_dir():
        return literals, dynamics

    for java_file in sorted(src_dir.rglob("*.java")):
        if not java_file.is_file():
            continue
        try:
            with open(java_file, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            continue

        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            for match in LITERAL_KEY_REGEX.finditer(line):
                literals.append((java_file, idx, match.group(1)))

            # Check for concatenated prefix expressions like "prefix." + var
            for match in CONCAT_PREFIX_REGEX.finditer(line):
                prefix_str = match.group(1)
                dynamics.append((java_file, idx, f'"{prefix_str}" + ...'))

            # Check for non-literal (dynamic) invocations if no literal matched
            if "Component.translatable" in line and not LITERAL_KEY_REGEX.search(line) and not CONCAT_PREFIX_REGEX.search(line):
                for match in DYNAMIC_KEY_REGEX.finditer(line):
                    expr = match.group(1).strip()
                    if expr and not expr.startswith('"'):
                        dynamics.append((java_file, idx, expr))

    return literals, dynamics


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="project root directory (default: current working directory)",
    )
    parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="treat dynamic key warnings as failures",
    )
    args = parser.parse_args(argv)

    project_dir = (args.project_dir or Path.cwd()).resolve()
    src_dir = project_dir / "src" / "main" / "java"

    lang_keys = load_lang_keys(project_dir)
    literals, dynamics = scan_java_sources(src_dir)

    missing_literals: List[Tuple[Path, int, str]] = []
    for file_path, line_num, key in literals:
        if key not in lang_keys:
            missing_literals.append((file_path, line_num, key))

    errors: List[str] = []
    warnings: List[str] = []

    for file_path, line_num, key in missing_literals:
        rel_path = file_path.relative_to(project_dir).as_posix()
        errors.append(f"  [MISSING KEY] {rel_path}:{line_num} -> \"{key}\" not found in any lang/*.json")

    for file_path, line_num, expr in dynamics:
        rel_path = file_path.relative_to(project_dir).as_posix()
        warnings.append(f"  [DYNAMIC KEY] {rel_path}:{line_num} -> expression `{expr}` cannot be statically verified")

    print("==================================================")
    print("Language Key Gate Check (lang_key_gate.py)")
    print("==================================================")
    print(f"Scanned {len(literals)} literal Component.translatable(...) usage(s).")
    print(f"Found {len(lang_keys)} defined key(s) across lang/*.json files.")

    if warnings:
        print(f"\nWarnings ({len(warnings)} dynamic/unresolvable key usages):")
        for w in warnings:
            print(w)

    if errors:
        print(f"\nERRORS ({len(errors)} missing literal language keys):")
        for e in errors:
            print(e)
        print("==================================================")
        print("RESULT: FAIL (lang_key_gate) — missing literal language keys must be added to lang JSON.")
        print("==================================================")
        return 1

    if args.warnings_as_errors and warnings:
        print("==================================================")
        print("RESULT: FAIL (lang_key_gate) — warnings escalated by --warnings-as-errors.")
        print("==================================================")
        return 1

    print("==================================================")
    print(f"RESULT: PASS (lang_key_gate) — 0 missing literal keys, {len(warnings)} dynamic warning(s).")
    print("==================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
