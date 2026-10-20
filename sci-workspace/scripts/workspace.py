#!/usr/bin/env python3
"""Initialize an SCI project scaffold or inspect its structure (stdlib only)."""

import argparse
import json
from pathlib import Path
import re
import sys


TOP_LEVEL = ("01_reference", "02_manuscript", "03_chapter", "04_data", "05_results")
DOCUMENTS = ("AGENTS.md", "WORKSPACE_GUIDE.md")
OPTIONAL_SUBDIRS = (
    "04_data/raw", "04_data/processed", "04_data/metadata",
    "05_results/statistics", "05_results/tables", "05_results/figures",
)
RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])", re.I)


class WorkspaceError(Exception):
    pass


def section_name(value):
    if (not re.fullmatch(r"[^\W_][\w -]*", value)
            or value != value.strip()
            or len(value.encode("utf-8")) > 160
            or RESERVED.fullmatch(value)):
        raise WorkspaceError(
            "Invalid section name {!r}: use a single name containing letters, "
            "numbers, spaces, underscores or hyphens; no reserved device names.".format(value)
        )
    return value


def root_path(value, must_exist=True):
    root = Path(value).expanduser().resolve()
    if root.exists() and not root.is_dir():
        raise WorkspaceError("Workspace root is not a directory: {}".format(root))
    if must_exist and not root.is_dir():
        raise WorkspaceError("Workspace root does not exist: {}".format(root))
    return root


def checked_path(root, path, kind, required=False):
    """Reject escaping symlinks and unexpected file types before any write."""
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise WorkspaceError("Workspace path escapes the project through a symlink: {}".format(path))
    if path.is_symlink() and not path.exists():
        raise WorkspaceError("Dangling workspace symlink: {}".format(path))
    if path.exists():
        matches = path.is_dir() if kind == "directory" else path.is_file()
        if not matches:
            raise WorkspaceError("Expected a {}, found another file type: {}".format(kind, path))
    elif required:
        raise WorkspaceError("Required {} does not exist: {}".format(kind, path))
    return resolved


def initialize(args):
    root = root_path(args.root, must_exist=False)
    sections = [section_name(name) for name in args.sections]
    if len({name.casefold() for name in sections}) != len(sections):
        raise WorkspaceError("Section names must be unique, including when case is ignored.")
    directories = [root] + [root / name for name in TOP_LEVEL]
    directories += [root / "03_chapter" / name for name in sections]
    if args.with_subdirs:
        directories += [root / name for name in OPTIONAL_SUBDIRS]
    files = [root / name for name in DOCUMENTS]
    # Complete the path and template preflight before creating even the root.
    for directory in directories:
        checked_path(root, directory, "directory")
    for file in files:
        checked_path(root, file, "file")
    assets = Path(__file__).resolve().parent.parent / "assets"
    contents = {
        file: (assets / (file.stem + ".template.md")).read_text(encoding="utf-8").replace(
            "{{PROJECT_NAME}}", args.project_name or root.name
        )
        for file in files
    }
    result = {"root": str(root), "dry_run": args.dry_run,
              "created": [], "preserved": [], "warnings": []}
    if (root / "WORKSPACE_GUIDE.md").exists():
        result["warnings"].append(
            "Existing WORKSPACE_GUIDE.md is preserved; review it separately if additions need documenting."
        )
    if args.dry_run:
        result["would_create"] = []
        for path in directories + files:
            result["preserved" if path.exists() else "would_create"].append(str(path))
        return result
    for directory in directories:
        checked_path(root, directory, "directory")
        try:
            directory.mkdir(parents=True)
            result["created"].append(str(directory))
        except FileExistsError:
            checked_path(root, directory, "directory", required=True)
            result["preserved"].append(str(directory))
    for file in files:
        checked_path(root, file, "file")
        try:
            with file.open("x", encoding="utf-8", newline="\n") as output:
                output.write(contents[file])
            result["created"].append(str(file))
        except FileExistsError:
            checked_path(root, file, "file", required=True)
            result["preserved"].append(str(file))
    return result


def inspect_path(root, path, kind, optional=False):
    report = {"path": str(path), "expected_type": kind, "optional": optional}
    try:
        checked_path(root, path, kind)
        report["state"] = "present" if path.exists() else ("not_created" if optional else "missing")
    except (WorkspaceError, OSError, RuntimeError) as error:
        report.update(state="conflict", detail=str(error))
    return report


def status(args):
    root = root_path(args.root)
    result = {
        "root": str(root),
        "directories": [inspect_path(root, root / name, "directory") for name in TOP_LEVEL],
        "documents": [inspect_path(root, root / name, "file") for name in DOCUMENTS],
        "chapters": [],
        "optional_subdirectories": [
            inspect_path(root, root / name, "directory", optional=True) for name in OPTIONAL_SUBDIRS
        ],
        "warnings": [],
    }
    chapters = root / "03_chapter"
    if result["directories"][2]["state"] == "present":
        try:
            checked_path(root, chapters, "directory", required=True)
            for child in sorted(chapters.iterdir(), key=lambda path: path.name):
                if child.is_dir() or child.is_symlink():
                    result["chapters"].append(inspect_path(root, child, "directory"))
        except (WorkspaceError, OSError, RuntimeError) as error:
            result["warnings"].append(str(error))
    reports = (result["directories"] + result["documents"]
               + result["chapters"] + result["optional_subdirectories"])
    for report in reports:
        if report["state"] == "missing":
            result["warnings"].append("Required workspace item is missing: " + report["path"])
        elif report["state"] == "conflict":
            result["warnings"].append(report["detail"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create missing scaffold items; preserve existing files.")
    init.add_argument("--root", required=True)
    init.add_argument("--project-name")
    init.add_argument("--sections", nargs="+", default=[], help="Chapter directories to add; none by default.")
    init.add_argument("--with-subdirs", action="store_true", help="Add the six optional data/results subdirectories.")
    init.add_argument("--dry-run", action="store_true", help="Preview changes without creating files or directories.")
    init.set_defaults(action=initialize)
    inspect = commands.add_parser("status", help="Inspect directory and guide-file presence without reading contents.")
    inspect.add_argument("--root", required=True)
    inspect.set_defaults(action=status)
    args = parser.parse_args()
    try:
        result = args.action(args)
    except (WorkspaceError, OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(json.dumps({"error": "Interrupted."}), file=sys.stderr)
        return 130
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
