#!/usr/bin/env python3
"""Generate a markdown table mapping each Java project folder to its Maven
coordinates (groupId/artifactId) and Git remote URL.

Used by the `resolve-local-maven-dependency` skill to look up which Maven
dependencies are available as local checkouts under configured project roots.

Scans every immediate subdirectory of each root for a top-level pom.xml.
Folders without a pom.xml or with unresolvable coordinates are skipped.
Missing root paths are silently ignored. Overwrites the output file on each run.

Configure root paths in ~/.claude/local-dependency-resolver-config.json.
Falls back to paths.config.json next to this script for development use.
Defaults to ~/projects and ~/Documents/Projects if no config file is found.

Usage:
    python generate-local-dependency-resolver.py
    python generate-local-dependency-resolver.py --root ~/code
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional

POM_NS = "{http://maven.apache.org/POM/4.0.0}"

CONFIG_FILENAME = "paths.config.json"
USER_CONFIG_PATH = Path.home() / ".claude" / "local-dependency-resolver-config.json"
DEFAULT_ROOTS = [
    str(Path.home() / "projects"),
    str(Path.home() / "Documents" / "Projects"),
]


def load_roots(config_path: str) -> list[str]:
    """Load and expand root paths from the JSON config file.

    Falls back to DEFAULT_ROOTS if the file is missing or malformed.
    Expands both ~ (home dir) and environment variables in each path.
    """
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        roots = data.get("roots", [])
        if isinstance(roots, list) and roots:
            return [str(Path(os.path.expandvars(r)).expanduser()) for r in roots]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return [str(Path(os.path.expandvars(r)).expanduser()) for r in DEFAULT_ROOTS]


def find_child(element: ET.Element, tag: str) -> Optional[ET.Element]:
    """Find a direct child by tag, with or without the Maven POM namespace."""
    for qualified in (POM_NS + tag, tag):
        child = element.find(qualified)
        if child is not None:
            return child
    return None


def parse_pom(pom_path: str) -> Optional[dict[str, Optional[str]]]:
    """Return {groupId, artifactId, packaging} for the project at pom_path,
    inheriting groupId from <parent> when not declared on the project itself."""
    try:
        root = ET.parse(pom_path).getroot()
    except ET.ParseError:
        return None

    parent_group = None
    parent_el = find_child(root, "parent")
    if parent_el is not None:
        pg = find_child(parent_el, "groupId")
        if pg is not None and pg.text:
            parent_group = pg.text.strip()

    own_group_el = find_child(root, "groupId")
    own_group = own_group_el.text.strip() if own_group_el is not None and own_group_el.text else None

    artifact_el = find_child(root, "artifactId")
    artifact = artifact_el.text.strip() if artifact_el is not None and artifact_el.text else None

    packaging_el = find_child(root, "packaging")
    packaging = packaging_el.text.strip() if packaging_el is not None and packaging_el.text else "jar"

    return {
        "groupId": own_group or parent_group,
        "artifactId": artifact,
        "packaging": packaging,
    }


def get_git_remote(project_path: str) -> Optional[str]:
    """Return the git remote.origin.url for the repo at project_path, or None if unavailable."""
    try:
        return subprocess.check_output(
            ["git", "-C", project_path, "config", "--get", "remote.origin.url"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def collect_projects(roots: list[str]) -> list[dict[str, Optional[str]]]:
    """Scan each root for immediate subdirectories containing a top-level pom.xml.

    Missing roots are silently skipped. Duplicate project paths (same directory
    reached via multiple roots) are included only once. Returns a list of dicts
    with keys: path, groupId, artifactId, packaging, remote. Sorted by path.
    """
    projects = []
    seen_paths: set[str] = set()
    for root_dir in roots:
        if not os.path.isdir(root_dir):
            continue
        for entry in sorted(os.listdir(root_dir)):
            project_path = os.path.normpath(os.path.join(root_dir, entry))
            if project_path in seen_paths:
                continue
            seen_paths.add(project_path)
            pom_path = os.path.join(project_path, "pom.xml")
            if not os.path.isfile(pom_path):
                continue
            info = parse_pom(pom_path)
            if not info or not info["groupId"] or not info["artifactId"]:
                continue
            info["path"] = project_path
            info["remote"] = get_git_remote(project_path)
            projects.append(info)
    projects.sort(key=lambda p: p["path"])
    return projects


def render_markdown(projects: list[dict[str, Optional[str]]], active_roots: list[str], script_path: str) -> str:
    """Render the dependency lookup table as a Markdown string.

    Includes a timestamped header recording the scanned roots so the skill
    can check staleness and regenerate when needed.
    """
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    scanned = ", ".join(f"`{r}`" for r in active_roots) or "_(none found)_"
    lines = [
        "# Local Maven Dependencies",
        "",
        f"_Generated {timestamp}. Scanned roots: {scanned}._",
        "",
        "> This file is auto-generated by the `resolve-local-maven-dependency` skill.",
        "> To refresh it after adding or removing projects, run:",
        "> ```",
        f"> python {script_path}",
        "> ```",
        "> The script overwrites this file on each run.",
        "> To configure which roots are scanned, edit `~/.claude/local-dependency-resolver-config.json`.",
        "",
        f"Found **{len(projects)}** Java projects.",
        "",
        "| Path | `groupId` | `artifactId` | Packaging | Git remote |",
        "|---|---|---|---|---|",
    ]
    for p in projects:
        remote = f"`{p['remote']}`" if p["remote"] else "_(no remote)_"
        lines.append(
            f"| `{p['path']}` "
            f"| `{p['groupId']}` "
            f"| `{p['artifactId']}` "
            f"| {p['packaging']} "
            f"| {remote} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    """Parse CLI arguments, collect projects, render the table, and write the output file."""
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    default_output = os.path.join(script_dir, "local-dependencies.md")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--config",
        default=None,
        help="Path to the config file. Defaults to ~/.claude/local-dependency-resolver-config.json, then the file next to this script.",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Scan a single directory, overriding the configured roots for this run.",
    )
    parser.add_argument("--output", default=default_output, help="Output markdown file (overwritten each run)")
    args = parser.parse_args()

    if args.config is not None:
        config_path = str(Path(os.path.expandvars(args.config)).expanduser())
    elif USER_CONFIG_PATH.exists():
        config_path = str(USER_CONFIG_PATH)
    else:
        config_path = os.path.join(script_dir, CONFIG_FILENAME)

    roots = load_roots(config_path)

    if args.root is not None:
        roots = [str(Path(os.path.expandvars(args.root)).expanduser())]

    active_roots = [r for r in roots if os.path.isdir(r)]
    projects = collect_projects(roots)
    content = render_markdown(projects, active_roots, script_path)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Wrote {len(projects)} projects to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
