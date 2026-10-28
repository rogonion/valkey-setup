# ADR 0016: Hexagonal Python (uv) Shape for Setup Tooling

Date - 2026-10-28

## Status

Accepted (specializes [ADR 0012](0012-scripting_python_uv.md) for the `*-setup` project family; defines the target shape of the postgres-setup / valkey-setup refactors)

## Context

[ADR 0012](0012-scripting_python_uv.md) settled the toolchain — Python managed by uv, typer CLIs, poethepoet tasks, subprocess adapters without `shell=True` — but the icipe portfolio's first routine (`spatialite-deps`) and the older `postgres-setup`/`valkey-setup` embody it differently:

* `postgres-setup`/`valkey-setup` are Poetry projects with a layered `core/containers` design, `sh` for shell plumbing, and no test suite; configuration is an ad-hoc YAML schema.
* `spatialite-deps` is a uv project with a strict hexagonal layout — pydantic models and Protocol ports in `domain/`, use cases in `application/`, adapters in `adapters/` — and pytest suites whose ports are tested with fakes.

The `*-setup` family needs one canonical shape: the same decisions should not be re-litigated per project, and the postgres/valkey refactors need a concrete target architecture rather than a vibe.

## Decision

Every `*-setup` project is a **uv project in the spatialite-deps hexagonal shape**:

```
src/<project>/
  domain/          pydantic models, Protocol ports, error taxonomy
    model/         pins, profiles, artifacts (validated TOML schemas)
    ports/         fetcher, sandbox, image registry, artifact extractor,
                   dist store, reporter — the interfaces use cases depend on
    error.py       the only exceptions raised anywhere in the package
  application/     use cases orchestrating ports only: BuildImage,
                   MaterializeDist (fetch → verify → build → capture)
  adapters/
    cli/           typer app (thin), TOML config loading, port wiring
    infra/         buildah sandbox/registry/extractor, httpx fetcher,
                   local dist store, rich reporter
```

Rules, enforced by review and tests:

* **Dependency direction** `adapters → application → domain`; the domain imports nothing outward.
* **Errors cross the boundary once**: infra adapters translate subprocess exit codes, buildah quirks (e.g. non-zero exits for unknown tags/containers), and HTTP failures into the domain taxonomy; raw exceptions never travel past the adapter that produced them.
* **Ports are the test seam**: use cases are tested with fakes over the ports; no test touches buildah, the network, or the filesystem. The container-facing port (Sandbox: begin / run / run_cached / copy_in / set_labels / set_env / commit / finish) is deliberately narrow so a fake can record everything a build does.
* **Task surface is `uv run poe <task>`** with tasks declared in `[tool.poe.tasks]`; when uv grows a native task runner the table migrates one-for-one.
* **Host subprocess calls use argument lists**; `sh -c` strings appear only as the command executed *inside* the container, where the shell is the point.

## Consequences

### Positive

* The postgres/valkey refactors have a concrete, already-proven target: port their builders onto the Sandbox/Registry/Extractor ports, keep their runtime-image logic as additional use cases, delete Poetry and `sh`.
* Use cases stay honest: step order, cache keys, and the verification contract live in one reviewable place per project, testable without buildah.
* The CLI is swappable (typer today) because commands are thin wrappers over framework-free callables.

### Negative / Trade-offs

* More files and indirection than the layered design; the cost is accepted because the family repeats this shape and the seams are where the tests live.
* Discipline required: the error taxonomy and port set grow with each new project (wasm will add a target axis); schema changes are ADR-worthy.

## References

* [ADR 0012](0012-scripting_python_uv.md) — the toolchain decision this specializes
* `spatialite-deps` (`tools/deps/spatialite/` in the icipe-portfolio) — the first implementation of this shape
* [ADR 0013](0013-images_sandbox_artifact_store.md), [ADR 0014](0014-dist_materialized_cache.md), [ADR 0015](0015-pins_and_profiles.md) — the decisions the ports carry
