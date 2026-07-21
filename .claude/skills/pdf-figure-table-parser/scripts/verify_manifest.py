#!/usr/bin/env python3
"""
Standalone quality check for an image-manifest.json, useful when the
manifest was hand-edited after generation (e.g. a downstream agent added
table_markdown, or you manually fixed a caption).

Usage:
    python verify_manifest.py <path/to/image-manifest.json> [repo_root]

repo_root defaults to the current working directory; manifest "file" paths
are resolved relative to it.
"""
import json
import os
import sys

import pdf_parser_lib as lib


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    manifest_path = sys.argv[1]
    repo_root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

    manifest = lib.load_json(manifest_path)
    errors = lib.verify_manifest(manifest, repo_root)

    print(f"{len(manifest.get('images', []))} entries checked against repo_root={repo_root}")
    if errors:
        print("FAILURES:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print("All quality checks passed.")


if __name__ == "__main__":
    main()
