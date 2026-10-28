# ADR 0015: Pinned Sources and Build Profiles

Date - 2026-10-28

## Status

Accepted (generalizes the single-versions-file rule of [ADR 0011](0011-deterministic_sqlite_spatialite_builds.md) with a configuration axis; replicable to the other `*-setup` projects)

## Context

[ADR 0011](0011-deterministic_sqlite_spatialite_builds.md) pinned *what* source is built (one versions file, sha256 checksums, no floating versions) but hardcoded *how* it is built: one fixed compile configuration per project. The `*-setup` pattern needs a second axis: the same pinned source, built with different feature sets, base images, or install prefixes — e.g. SQLite with FTS5 for the portfolio, or a spatialite-ready variant; postgres with ICU/LZ4/Zstd versus a minimal build. postgres-setup proved the need (its `build.yaml` carried versions, dependencies, and flags) but as one unversioned ad-hoc schema.

These two axes answer different questions and must not be conflated: "which source" changes rarely and must be verified by checksum; "how it is configured" changes per use case and must be verifiable by the built artifact itself.

## Decision

Two TOML files at the project root, validated into pydantic models at the CLI boundary:

* **`pins.toml` — the single versions file** (ADR 0011 unchanged): per component, the version, archive name, download URL, and sha256. Upgrades are edits to this file, and nothing else invalidates a build's provenance.
* **`profiles.toml` — named build profiles**: each profile selects the base image (the build sandbox), the build packages installed into it, the compile-time **feature defines** (e.g. `FTS5` becomes `-DSQLITE_ENABLE_FTS5=1`), extra flags, and the install prefix. The default profile is named; unknown names are errors.
* **Image identity is `version + profile`**: the artifact tag `localhost/<project>/<app>:<version>-<profile>` encodes both axes, so caches and consumers never confuse configurations.
* **The build verifies itself against the profile**: after `make install`, the built binary must report the pinned version (`--version`) and every requested feature (`PRAGMA compile_options` for SQLite). A profile that silently builds the wrong thing is a build failure, not a documentation problem.
* Planned extensions join the same schema: a spatialite profile adds a pinned component to `pins.toml` and a profile that builds it against the core prefix; a wasm profile adds a target axis rather than new files.

## Consequences

### Positive

* Feature requests become declarative and reviewable: "add GEOPOLY" is a one-line profile edit whose result is verified by the build itself.
* One project serves many use cases without forks — the same sha256-verified SQLite source underlies every profile.
* The schema is portable: postgres-setup's `build.yaml` (versions + deps + flags in one file) maps onto pins + profiles with the axes properly separated.

### Negative / Trade-offs

* Two files to keep consistent where the old tools had one; mitigated because only `pins.toml` carries checksums and only `profiles.toml` carries configuration.
* Verification support is per-application: each `*-setup` project must know how to ask its artifact what it is (compile options, `--version`, extension load). Generic verification is not possible by design — asking the artifact is the point.
* Profile sprawl is possible; every profile costs a build matrix cell and cache storage.

## References

* [ADR 0011](0011-deterministic_sqlite_spatialite_builds.md) — the pinning discipline this extends
* [ADR 0013](0013-images_sandbox_artifact_store.md) — where the version-profile tag is consumed
* `pins.toml`, `profiles.toml`, `src/sqlite_setup/domain/model/build.py`
