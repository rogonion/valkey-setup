# valkey-setup

A utility for creating customized, pinned-from-source [Valkey](https://valkey.io/)
container images, following the house `*-setup` pattern: **uv + Python
(hexagonal), buildah sandboxes, container images as the artifact store**
([ADR 0013](docs/architecture/ADRs/0013-images_sandbox_artifact_store.md)).
The host needs only uv and buildah — compilers and devel packages live in
the sandbox images, never on the host.

```
├── pins.toml        the single versions file: pinned version + url + sha256
├── profiles.toml    build profiles: base image, packages, flags, runtime shape
├── src/valkey_setup (uv project, hexagonal)
│   ├── domain/      models (pins, profiles, image tags), ports, error taxonomy
│   ├── application/ BuildValkey, BuildModule, BuildRuntime use cases
│   └── adapters/    typer CLI; buildah/httpx/rich infra adapters
└── resources/       runtime image entrypoint.sh + valkey.conf
```

## Image topology

| Image | Content |
|---|---|
| `localhost/valkey-setup/valkey:9.0.1-default` | core artifact: compiled valkey server + CLI under `/usr/local/valkey` |
| `localhost/valkey-setup/module/<name>:<version>-default` | module artifact: the module's `.so` under `/usr/local/valkey/modules` |
| `localhost/valkey-setup/runtime:9.0.1-default` | the product: core + selected modules, runtime packages, valkey user (999:999), config, entrypoint, port 6379 |

The runtime image assembles the artifact images (core binaries copied in,
each profile module's `.so` copied in), installs only runtime packages,
and is shaped per the profile (user, data dir, config dir, ports). Valkey
is a daemon, so the runtime image is the product — there is no `dist/`
materialization step (that exists where consumers need host prefixes,
e.g. sqlite-setup).

## Modules

Modules are the valkey analogue of postgres extensions: pinned sources
in `pins.toml`, per-module build recipes in the application layer, one
artifact image each, merged into the runtime image per profile.

- **valkey-json** 1.0.2 — JSON data type and JSONPath queries
- **valkey-search** 1.1.0 — vector and full-text search (OpenMP at runtime)
- **valkey-bloom** 1.0.0 — bloom filter and cuckoo filter data types

Known pinning gaps (see
[system overview](docs/architecture/description/0001-system_overview.md)):
valkey-json's CMake clones the valkey server source at the pinned tag,
valkey-search's CMake FetchContent-pulls its submodules (gRPC, Protobuf,
Abseil, GTest), and valkey-bloom's cargo build resolves crates from
crates.io. The module tarballs themselves are sha256-pinned; the
transitive sources are not (yet).

## Requirements

- [uv](https://docs.astral.sh/uv/) (auto-installs managed Python)
- [buildah](https://buildah.io/) 1.41+ (or a podman that ships it)

## Usage

```shell
uv sync                                   # once
uv run poe build                          # core artifact image
uv run poe module                         # all profile module images
uv run poe runtime                        # runtime image (builds missing artifacts)
uv run poe test                           # pytest suite
uv run poe clean                          # prune the profile's cache images
```

Per-module or per-profile: `uv run valkey-setup module --name valkey-json`,
`... --profile <name>`. `valkey-setup --help` lists all commands.

### Running the runtime image

```shell
podman volume exists valkey-data || podman volume create valkey-data
podman run -d --name valkey --network host \
  -v valkey-data:/var/lib/valkey/data:Z \
  localhost/valkey-setup/runtime:9.0.1-default
podman exec valkey valkey-cli ping
podman exec valkey valkey-cli MODULE LIST
```

`deploy/` holds podman quadlet units (`valkey.container`, `valkey-data.volume`)
as an alternative to raw commands.

## Upgrading versions

Edit `pins.toml` (version, URL, archive name, sha256 — compute with
`sha256sum` after downloading) and re-run; stale images rebuild
automatically. Never leave a floating version in the file.

## Documentation

- `docs/architecture/description/0001-system_overview.md` — the entry point
- `docs/architecture/ADRs/` — the shared ADR series subset this repo
  grounds on (0012, 0013, 0015, 0016) plus ADR 0017 (runtime images for
  daemon dependencies), drafted here for replication into postgres-setup
