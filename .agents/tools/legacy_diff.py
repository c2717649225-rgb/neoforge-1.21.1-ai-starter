"""Legacy Diff Helper (legacy_diff.py).

Simultaneously searches a query term in both the current project and a legacy/reference
repository directory, displaying formatted side-by-side search results.

Usage:
    python .agents/tools/legacy_diff.py --reference /path/to/legacy_mod --query "someMethod"
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


def search_in_tree(root: Path, query: str, is_regex: bool = False, max_results: int = 20) -> list[tuple[Path, int, str]]:
    results = []
    if not root.is_dir():
        return results

    if is_regex:
        pattern = re.compile(query, re.IGNORECASE)
    else:
        pattern = None

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip build and hidden dirs
        dirnames[:] = [d for d in dirnames if d not in ("build", ".git", ".gradle", "run", "bin")]
        for name in filenames:
            if not (name.endswith(".java") or name.endswith(".json") or name.endswith(".toml")):
                continue
            file_path = Path(dirpath) / name
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                    for line_idx, line in enumerate(fh, 1):
                        match = pattern.search(line) if pattern else (query.lower() in line.lower())
                        if match:
                            results.append((file_path, line_idx, line.strip()))
                            if len(results) >= max_results:
                                return results
            except OSError:
                pass
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", "-q", required=True, help="Search term or regex pattern")
    parser.add_argument("--reference", "-r", type=Path, required=True, help="Path to legacy/reference repository")
    parser.add_argument("--current", "-c", type=Path, default=Path.cwd(), help="Path to current project (default: CWD)")
    parser.add_argument("--regex", action="store_true", help="Treat query as regular expression")
    parser.add_argument("--max", type=int, default=20, help="Max results per repository")
    args = parser.parse_args(argv)

    current_dir = args.current.resolve()
    ref_dir = args.reference.resolve()

    print("==================================================")
    print(f"Legacy Diff Search: '{args.query}'")
    print("==================================================")
    print(f"Current:   {current_dir}")
    print(f"Reference: {ref_dir}")
    print("--------------------------------------------------")

    cur_results = search_in_tree(current_dir, args.query, is_regex=args.regex, max_results=args.max)
    ref_results = search_in_tree(ref_dir, args.query, is_regex=args.regex, max_results=args.max)

    print(f"\n[CURRENT REPO RESULTS] ({len(cur_results)} match(es))")
    if not cur_results:
        print("  (no matches found)")
    for path, line_num, line_str in cur_results:
        rel = path.relative_to(current_dir).as_posix()
        print(f"  {rel}:{line_num}: {line_str}")

    print(f"\n[REFERENCE REPO RESULTS] ({len(ref_results)} match(es))")
    if not ref_results:
        print("  (no matches found)")
    for path, line_num, line_str in ref_results:
        rel = path.relative_to(ref_dir).as_posix()
        print(f"  {rel}:{line_num}: {line_str}")

    print("==================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
