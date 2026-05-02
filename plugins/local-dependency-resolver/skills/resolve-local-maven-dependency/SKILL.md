---
name: resolve-local-maven-dependency
description: "Maven projects only. Use when a task requires reading or modifying the source of a Maven dependency (groupId/artifactId). Resolves the dependency to a local checkout path under the user's configured projects root (~/projects by default) when one exists, so source files can be read or edited directly instead of inspecting JARs."
---

# Resolve Local Maven Dependency

The user keeps Java project checkouts under a configured **projects root** -
default `~/projects`, overridable via the `LOCAL_DEPENDENCY_RESOLVER_ROOT`
environment variable. When a task in one project references a Maven
dependency, that dependency's source code may be available locally as a
sibling folder under the same root. This skill maps `groupId:artifactId` to
a local path so files can be read and edited directly.

The lookup table itself records which root it was generated from - its header
contains a line:

```
_Generated YYYY-MM-DD HH:MM:SS <tz> from `pom.xml` files under `<projects-root>`._
```

Use that `<projects-root>` value when resolving paths; do not assume the
default.

## How to use

1. **Check freshness first.** Read the top ~10 lines of
   `local-dependencies.md` in this skill's directory and find the line:
   `_Generated YYYY-MM-DD HH:MM:SS <tz> from ..._`.
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
   The script rescans the configured projects root (default `~/projects`,
   overridable via the `LOCAL_DEPENDENCY_RESOLVER_ROOT` environment variable
   or `--root <path>` CLI flag), reparses every top-level `pom.xml`, reads
   each folder's `git remote.origin.url`, and overwrites
   `local-dependencies.md` in this skill's directory.

2. **Look up the dependency** in the table. It has one row per Java project
   folder under the projects root, with columns: Folder, groupId, artifactId,
   Packaging, Git remote.
   - Match `groupId` and `artifactId` directly when possible.
   - If the dependency artifact ends in something like `-core`, `-api`,
     `-client`, `-dto`, `-business`, `-app`, etc. and is not in the table,
     it's likely a submodule of a multi-module project. Look for a row whose
     `artifactId` ends in `-parent` (or whose `Packaging` is `pom`) and whose
     `groupId` matches or is the obvious parent group. The submodule lives in
     a subdirectory under that row's `Folder`.
   - When several rows share the same Git remote (e.g. `cherry/`, `cherry-2/`,
     `cherry-3/`), prefer the one without a numeric suffix unless the user is
     already working in one of the suffixed checkouts.

3. The resolved path is `<projects-root>/<Folder>/` (plus the submodule
   subdirectory if applicable), where `<projects-root>` is the value from
   the table's header line described above. Read or edit files there as
   needed for the task.

4. If no row matches, tell the user the dependency was not found locally and
   fall back to the JAR or ask for guidance.
