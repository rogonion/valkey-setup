# 0001 — System Overview

This document describes valkey-setup as it runs: what executes where,
what the images are, and where each piece's decision record lives. It is
the entry point into the description docs.

## Shape in one paragraph

A Python (uv) CLI compiles a pinned Valkey source tarball inside a buildah
working container and commits the core **artifact image**
`localhost/valkey-setup/valkey:9.0.1-<profile>`. Each pinned module
(valkey-json, valkey-search, valkey-bloom) compiles in its own sandbox
into its own artifact image holding the module `.so`. The `runtime`
command assembles the **runtime image** — the product — from those
artifacts: core prefix copied in, module artifacts copied in, only
runtime packages installed, a valkey user (999:999), config, entrypoint,
and port 6379 shaped per the profile
([ADR 0017](../ADRs/0017-runtime_images_daemons.md)). The host needs only
uv and buildah.

## Layers

### Inputs & CLI (primary adapter)

- `pins.toml` — the single versions file: core + module sources, each
  with version, URL, and sha256 ([ADR 0015](../ADRs/0015-pins_and_profiles.md)).
- `profiles.toml` — named build profiles: base image, build packages,
  make flags (TLS, systemd, jemalloc), runtime packages, the runtime
  shape (uid/gid, data dir, ports), and the module list the runtime
  includes.
- The typer CLI (`build`, `module`, `runtime`, `clean`, `profiles`)
  stays thin: parse flags, delegate to framework-free callables,
  translate domain errors into exit code 1.

### Application (use cases)

- **BuildValkey** — core artifact: fetch + verify tarball, install build
  packages, `make -j$(nproc) BUILD_TLS=yes USE_SYSTEMD=yes MALLOC=jemalloc`,
  `make install PREFIX=...`, verify `valkey-server --version` against the
  pin, label and commit.
- **BuildModule** — per-module artifact: fetch + verify, run the module's
  recipe (code, not configuration — `build.sh --release` for json with
  `SERVER_VERSION` from the core pin; cmake release for search; cargo
  release for bloom), locate the built `.so` via a scoped find, place it
  under `<prefix>/modules/`, verify present, label and commit.
- **BuildRuntime** — the product: auto-build missing core/module images,
  assemble (copy-from-image, runtime packages, user, dirs, config,
  entrypoint), verify daemon version + every module artifact, configure
  image (env, volume, ports, entrypoint, cmd, user), label with full
  provenance, commit.

### Domain

- Pydantic models: SourcePin, ModulePin (adds artifact name + build/runtime
  packages), Pins (core + modules), Profile (build/runtime shape), image
  tag helpers (`core/module/runtime` tags, per-scope cache prefixes).
- Ports: `SourceFetcher`, `Sandbox` (with `copy_from_image` and image
  config methods — the runtime-assembly surface), `ImageRegistry`,
  `Reporter`.
- Error taxonomy: the only exceptions raised anywhere.

### Adapters (infra)

- **BuildahSandbox** — `buildah from/run/copy/config/commit` with
  hash-keyed layer caching; `copy --from` composes artifact images.
- **BuildahRegistry**, **HttpxSourceFetcher** (sha256 verified, cached),
  **RichReporter**.

## Image topology

| Image | Built by | Role |
| --- | --- | --- |
| `valkey-setup/valkey:9.0.1-default` | BuildValkey | core artifact (compiled daemon + CLI) |
| `valkey-setup/module/<name>:<ver>-default` | BuildModule | module artifact (`.so` under `<prefix>/modules`) |
| `valkey-setup/runtime:9.0.1-default` | BuildRuntime | the product (assembled, verified, shaped) |
| `valkey-setup/cache/<profile>/<scope>:<hash>` | all | replayable build layers (prunable) |

## Pinning gaps (known, documented)

The module tarballs are sha256-pinned; three transitive fetches happen at
build time inside the sandbox and are **not** content-pinned yet:

- valkey-json's CMake ExternalProject clones the valkey server source at
  `GIT_TAG ${SERVER_VERSION}` — the same 9.0.1 tag as the core pin, but
  from git, not from our tarball.
- valkey-search's CMake FetchContent-pulls submodules (gRPC v1.70.1,
  Protobuf, Abseil, GTest).
- valkey-bloom's cargo build resolves crates from crates.io.

Closing these (vendoring submodules, patching ExternalProject to the
pinned tarball, a cargo offline lockfile) is future hardening per
[ADR 0015](../ADRs/0015-pins_and_profiles.md)'s spirit.

## How the pieces map to decisions

| Piece | ADR |
| --- | --- |
| ADR process (shared series) | [0001](../ADRs/0001-architectural_decision_records.md) |
| Python/uv tooling + poe tasks | [0012](../ADRs/0012-scripting_python_uv.md) |
| Images as sandbox and artifact store | [0013](../ADRs/0013-images_sandbox_artifact_store.md) |
| Pinned sources and build profiles | [0015](../ADRs/0015-pins_and_profiles.md) |
| Hexagonal setup tooling shape | [0016](../ADRs/0016-hexagonal_setup_tooling.md) |
| Runtime images for daemon dependencies | [0017](../ADRs/0017-runtime_images_daemons.md) |

## Diagrams

The image topology view is drawn in [docs/shared/design.drawio](../../shared/design.drawio)
(**Image Topology** page): base image → core artifact → module artifacts →
runtime image → podman deploy, with the hash-keyed layer cache alongside.
PNG exports follow the `<file>-<Page>.drawio.png` convention.
