# agent rules

- Architecture decisions and their context live in
  `docs/architecture/ADRs/` (the shared icipe-portfolio ADR series subset
  this repo grounds on). The runtime picture is
  `docs/architecture/description/0001-system_overview.md`. A change that
  alters the build contract = ADR first, then implementation.
- Hexagonal architecture: `domain/` defines ports and models and imports
  nothing from `adapters/` or `application/`; `application/` orchestrates
  ports only. All buildah/httpx subprocess work lives in `adapters/infra/`
  ([ADR 0016](docs/architecture/ADRs/0016-hexagonal_setup_tooling.md)).
- Container images are the artifact store; the runtime image is the
  product ([ADR 0013](docs/architecture/ADRs/0013-images_sandbox_artifact_store.md),
  [ADR 0017](docs/architecture/ADRs/0017-runtime_images_daemons.md)).
- Pinned builds only: versions live in `pins.toml` (with sha256), build
  and runtime configuration in `profiles.toml`
  ([ADR 0015](docs/architecture/ADRs/0015-pins_and_profiles.md)).
  Module build recipes are code in `application/modules.py`, not
  configuration. Known transitive pinning gaps are documented in the
  system overview — do not add new ones silently.
- Scratch and temporary files go under `.tmp/` (git-ignored); never
  commit build logs or other scratch output.
- Subprocess adapters use argument lists; no `shell=True` on the host
  (`sh -c` inside the container is fine).
- Tests use fakes over ports, never the network, buildah, or the
  filesystem. `uv run poe test` must stay green.
- Task surface is `uv run poe <task>` (ADR 0012); keep `[tool.poe.tasks]`
  and this file's documented commands in sync.
