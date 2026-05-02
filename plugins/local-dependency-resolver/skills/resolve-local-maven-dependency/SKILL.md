---
name: resolve-local-maven-dependency
description: "Maven projects only. Use when a task requires reading or modifying the source of a Maven dependency (groupId/artifactId). Resolves the dependency to a local checkout path when one exists under any of the user's configured project roots, so source files can be read or edited directly instead of inspecting JARs."
---

# Resolve Local Maven Dependency

The user keeps Java project checkouts under one or more **project roots**.
Roots are configured in `paths.config.json` in the marketplace plugin directory.
To add or remove paths, edit:

```
~/.claude/plugins/marketplaces/local-dependency-resolver/plugins/local-dependency-resolver/skills/resolve-local-maven-dependency/paths.config.json
```

The defaults cover both Windows and Unix/Mac:

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

> **Why the marketplace path?** When Claude Code installs a plugin from the
> marketplace it keeps two copies: a user-editable source under
> `~/.claude/plugins/marketplaces/` and a processed cache under
> `~/.claude/plugins/cache/`. The generator script runs from the cache, so
> without an explicit `--config` the script would silently read the cached copy
> of `paths.config.json` rather than the one the user edits. Passing the
> marketplace path via `--config` fixes this.

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
   skill's installation directory and invoke it with `python`, passing the
   marketplace config path explicitly so the script reads the user-editable
   copy rather than the cached one:
   ```
   python "<this-skill-dir>/generate-local-dependency-resolver.py" --config "~/.claude/plugins/marketplaces/local-dependency-resolver/plugins/local-dependency-resolver/skills/resolve-local-maven-dependency/paths.config.json"
   ```
   The script reads `paths.config.json` for roots, reparses every top-level
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
