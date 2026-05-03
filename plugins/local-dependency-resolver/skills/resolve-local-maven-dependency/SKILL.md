---
name: resolve-local-maven-dependency
description: "Maven projects only. Use when a task requires reading or modifying the source of a Maven dependency (groupId/artifactId). Resolves the dependency to a local checkout path when one exists under any of the user's configured project roots, so source files can be read or edited directly instead of inspecting JARs."
---

# Resolve Local Maven Dependency

The user keeps Java project checkouts under one or more **project roots**.
Roots are configured in a stable user-level config file.
To add or remove paths, create or edit:

```
~/.claude/local-dependency-resolver-config.json
```

If the file does not exist, the script falls back to these built-in defaults:
`~/projects` and `~/Documents/Projects`.

A minimal config looks like:

```json
{
  "roots": [
    "~/projects",
    "~/Documents/Projects"
  ]
}
```

Paths support `~` (home directory) and environment variables (e.g.
`%USERPROFILE%` on Windows, `$HOME` on Unix). Missing paths are silently
skipped at generation time.

When a task in one project references a Maven dependency, that dependency's
source code may be available locally as a folder under one of the configured
roots. This skill maps `groupId:artifactId` to an absolute local path so files
can be read and edited directly.

## How to use

1. **Check freshness first.** Read the top ~10 lines of
   `local-dependencies.md` in this skill's directory and find the line:
   `_Generated YYYY-MM-DD HH:MM:SS <tz>. Scanned roots: ..._`.
   Compare that date to today. Regenerate the table before continuing if any
   of these are true:
   - the timestamp is more than **14 days** old,
   - the file is missing or the timestamp line cannot be found,
   - the user mentions a project that has been added or removed since the
     table was generated.

   To regenerate, run the `generate-local-dependency-resolver.py` script
   that lives next to this `SKILL.md`. Resolve its absolute path from the
   skill's installation directory and invoke it with `python`:
   ```
   python "<this-skill-dir>/generate-local-dependency-resolver.py"
   ```
   The script reads `~/.claude/local-dependency-resolver-config.json` for roots, reparses every top-level
   `pom.xml` in each root's immediate subdirectories, reads each folder's
   `git remote.origin.url`, and overwrites `local-dependencies.md`.

2. **Look up the dependency** in the table. It has one row per Java project
   found across all configured roots, with columns: Path, groupId, artifactId,
   Packaging, Git remote.
   - Match `groupId` and `artifactId` directly when possible.
   - If the dependency artifact ends in something like `-core`, `-api`,
     `-client`, `-dto`, `-business`, `-app`, etc. and is not in the table,
     it's likely a submodule of a multi-module project. Look for a row whose
     `artifactId` ends in `-parent` (or whose `Packaging` is `pom`) and whose
     `groupId` matches or is the obvious parent group. The submodule lives in
     a subdirectory under that row's `Path`.
   - When several rows share the same Git remote (e.g. `cherry/`, `cherry-2/`,
     `cherry-3/`), prefer the one without a numeric suffix unless the user is
     already working in one of the suffixed checkouts.

3. The **Path** column contains the absolute path to the project directory
   (plus the submodule subdirectory if applicable). Read or edit files there
   directly as needed for the task.

4. If no row matches, tell the user the dependency was not found locally and
   fall back to the JAR or ask for guidance.
