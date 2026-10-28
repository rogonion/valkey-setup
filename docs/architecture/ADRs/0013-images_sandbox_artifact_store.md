# ADR 0013: Container Images as the Sandbox and Artifact Store

Date - 2026-10-28

## Status

Accepted (establishes the `*-setup` project pattern shared with `postgres-setup` and `valkey-setup`; to be replicated into those repositories' docs)

## Context

We maintain a family of `*-setup` projects that compile external dependencies from source with our own customizations, so that every environment consumes the same pinned, feature-controlled build ([ADR 0011](0011-deterministic_sqlite_spatialite_builds.md)). Two dialects existed:

* `postgres-setup` / `valkey-setup` already used buildah: the container is the build sandbox and the **output is container images** — runtime images (postgres, valkey run as containers) and build/artifact images whose compiled binaries can be copied out for other uses.
* The icipe-portfolio's `tools/deps/spatialite` routine compiled on the host (devcontainer toolchain) into a sandboxed `dist/` prefix — deterministic, but it required every environment to install the geo devel packages and a C toolchain, and `dist/` was the only artifact.

A build artifact that exists only as a host folder is environment-bound: it cannot be cached between steps, composed from another image, shipped, or resumed. Container images solve all four: a buildah layer is a cache entry, `--from` copies compose images, registries ship them, and a daemon is never needed (rootless buildah with the podman store).

## Decision

Every `*-setup` project treats **container images as the unit of sandboxing and artifact storage**:

* Builds run inside a buildah working container created from a pinned base image; build dependencies are installed inside that container, never on the host.
* Each build step commits its result as a **cache layer** image under `sqlite-setup/cache/<profile>:<hash>`, where the hash covers the current image, command, environment, and explicit cache keys (pins, flags). Cache hits resume from the intermediate image instead of re-running the step.
* The final step commits the **artifact image**: `localhost/<project>/<app>:<version>-<profile>`, labelled with pins, profile, prefix, and features.
* Host requirements are minimal and constant: uv, buildah, and a container runtime store. No compilers, devel packages, or interpreter versions on the host.
* Whether a **runtime image** also exists is per-application: postgres and valkey are daemons (runtime images), SQLite is a library (artifact image only), and a future wasm target produces static artifacts rather than a runtime image.
* Consumers that need a host prefix get it by **materializing** it out of the artifact image ([ADR 0014](0014-dist_materialized_cache.md)) — the image remains the source of truth.

## Consequences

### Positive

* The build environment is identical everywhere — host, devcontainer, CI — because the toolchain lives in the image, not the host; this strengthens [ADR 0011](0011-deterministic_sqlite_spatialite_builds.md) by removing the devcontainer's role as dependency provider.
* Step-level layer caching makes rebuilds cheap and resumable; the host and devcontainer share one podman store.
* Artifact images compose: binaries can be copied out (psql, sqlite3, headers/libs) to build custom runtimes (e.g. an alpine postgres) without recompiling.
* Images are distributable: a registry (even a local one) turns a per-machine cache into a shared one without changing the build logic.

### Negative / Trade-offs

* The podman store grows: one image per cache layer plus artifact images (mitigated by `clean --cache` pruning under the cache prefix).
* Until a registry exists, the cache is local to one machine/store; CI and second machines rebuild from source.
* Rootless buildah has constraints that must be handled at the adapter boundary, never in the use cases: `buildah mount` requires an unshare session (the extractor streams tar over `buildah run` instead), and unknown tags/containers exit non-zero (absence, not error).

## References

* [ADR 0011](0011-deterministic_sqlite_spatialite_builds.md) — the determinism premise this realizes
* [ADR 0012](0012-scripting_python_uv.md) — the uv/Python tooling this is written in
* [ADR 0015](0015-pins_and_profiles.md) — where the pinned inputs to the sandbox come from
* `postgres-setup`, `valkey-setup` — the precedent projects
* `docs/architecture/description/0001-system_overview.md` — the runtime picture of this pattern
