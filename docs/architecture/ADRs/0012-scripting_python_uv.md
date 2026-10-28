# ADR 0012: Python (uv) for Build Tooling, Data Routines, and Task Running

Date - 2026-10-27

## Status

Accepted (supersedes [ADR 0009](0009-scripting_nushell.md); amends the implementation language of [ADR 0011](0011-deterministic_sqlite_spatialite_builds.md))

## Context

ADR 0009 chose Nushell for `tools/` workflows and data routines. Since then:

* The heaviest routine (map-stack-prep, [ADR 0007](0007-basemap_geoboundaries_pmtiles.md)) outgrew shell orchestration: it needs real application logic (validation models, HTTP fetching, reporting, test suites) and was ported to a Python/uv project under `tools/pipelines/`. Keeping its CLI in Python while orchestrating around it in Nushell splits the toolchain.
* [uv](https://docs.astral.sh/uv/) gives Python the same ergonomics pnpm gives Node: per-project environments, a lockfile, managed CPython interpreters, and a one-line install in containers. ADR 0009's core objection — "a second heavyweight interpreter/dependency layer fragmenting the toolchain" — no longer holds, because every environment now ships uv regardless.
* We still need a single task-runner entry point for humans and coding agents (the AGENTS.md command table). `tasks.nu` was pencilled in but never built; poethepoet offers declarative tasks inside `pyproject.toml` with zero runner code and composes naturally with uv.

## Decision

1. `tools/` workflows and data routines are written in **Python, managed by uv**. No new Nushell scripts are created; remaining ones are ported and deleted once their Python replacement is verified.
2. The **repository root is a uv project** (`pyproject.toml` with `[tool.uv] package = false`) that exists to own the task runner: tasks are declared in its `[tool.poe.tasks]` table, and the universal entry point is `uv run poe <task>`. Workflow names live there and in the AGENTS.md command table — kept in sync.
3. Pinned from-source dependency builds ([ADR 0011](0011-deterministic_sqlite_spatialite_builds.md)) are **uv projects in the same shape as pipeline routines**: pins and checksums in a single versions file (`pins.toml`), pydantic models at the boundary, a typer CLI as the primary adapter, subprocess adapters with no `shell=True`, and pytest suites whose ports are tested with fakes.
4. Nushell is dropped from DevContainer/CI images once no `.nu` scripts remain.

## Consequences

### Positive

* One language across tooling: routine logic, tests, glue scripts, and the task runner share a single toolchain, dependency manager, and lockfile. `uv run poe --help` documents every workflow.
* uv-managed interpreters remove distro-Python drift in containers; the uv project root gives `tools/` the same reproducibility guarantees pnpm gives `apps/`.
* poe tasks are declarative (no runner code to maintain) yet can wrap anything — a stdlib build script, a `uv run --directory` invocation into a pipeline project, or later `pnpm`/`vitest` commands once the SvelteKit apps land.

### Negative / Trade-offs

* Python glue is more verbose than Nushell's structured pipelines for quick data shuffling; acceptable because anything non-trivial was always destined for a proper CLI in `tools/pipelines/` or `apps/`.
* Environments must install uv (curl installer, one line) — the same cost class as installing Nushell, which it replaces.
* A build routine that needs third-party packages now depends on `uv sync` resolving `uv.lock` — mitigated by committing the lockfile (ADR 0011 environments are fully specified by it).
* Historical documents referencing the Nushell era (ADR 0007/0011 wording, the read-only `map-stack-old` port notes) stay as-is; new work cites this ADR instead.

## References

* [ADR 0009](0009-scripting_nushell.md) — superseded predecessor
* [ADR 0002](0002-monorepo_architecture.md) — the `tools/` layout this runs in
* [ADR 0011](0011-deterministic_sqlite_spatialite_builds.md) — the pinned build routine this ports to `build.py`
* uv — https://docs.astral.sh/uv/
* poethepoet — https://github.com/nat-n/poethepoet
