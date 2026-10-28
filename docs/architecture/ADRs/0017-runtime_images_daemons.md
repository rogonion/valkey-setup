# ADR 0017: Runtime Images for Daemon Dependencies

Date - 2026-10-28

## Status

Accepted (drafted in valkey-setup; to be replicated into postgres-setup and future daemon `*-setup` projects such as zenoh-setup)

## Context

[ADR 0013](0013-images_sandbox_artifact_store.md) established container
images as the unit of sandboxing and artifact storage for the `*-setup`
family, and left one choice per application: whether a runtime image
exists. SQLite is a library consumed as a host prefix, so sqlite-setup
produces artifact images plus a materialized `dist/`
([ADR 0014](0014-dist_materialized_cache.md)). Valkey (and postgres,
valkey's sibling precedent) are daemons: consumers do not link against
them or copy prefixes — they **run** them, as containers, attached to
volumes and networks.

The old valkey-setup/postgres-setup already had this shape implicitly:
build images holding compiled binaries, and a runtime image assembled
from them with a user, entrypoint, config, and ports. The distinction was
not stated as a decision, so assembly details lived in ad-hoc builder
code.

## Decision

For daemon dependencies, the `*-setup` project produces three image kinds,
all tagged `localhost/<project>/<app>:<version>-<profile>`:

1. **Core artifact image** — compiled daemon under its prefix. Rebuilt
   from pins; never run directly.
2. **Extension/module artifact images** — one per pinned extension
   (valkey modules, postgres extensions), built against the core,
   holding just the extension's artifact under the prefix.
3. **Runtime image** — the product: base image + core prefix copied in
   via `buildah copy --from` + each profile extension's artifact + only
   the *runtime* packages + a dedicated uid/gid, data dir, config files,
   entrypoint, ports, volumes, and user.

Assembly is a use case like any other (`BuildRuntime`), not builder
plumbing: it auto-builds missing core/module images, verifies the daemon
version and every expected extension artifact inside the image, and
labels the image with the full provenance (pins, profile, module
versions). There is no `dist/` materialization for daemons — the runtime
image is the only consumption form.

## Consequences

### Positive

* One command (`runtime`) produces the deployable image from pins;
  the acceptance (daemon version + artifacts present) runs inside it.
* Extension selection is declarative: the profile's module list decides
  what the runtime contains; adding an extension = pin + recipe + list.
* The deploy story stays podman-native: quadlet/container units
  reference the image tag; no host daemon process to manage.

### Negative / Trade-offs

* Extension upgrades rebuild the runtime image (cheap: assembly
  replays from artifact-image cache layers).
* A daemon that needs host binaries (rare) has no supported path — by
  design; that is the library case (ADR 0014).
* Runtime verification is build-time only; a running-daemon smoke test
  (ping, MODULE LIST / extension \df) is left to deployment acceptance.

## References

* [ADR 0013](0013-images_sandbox_artifact_store.md) — images as artifact store
* [ADR 0015](0015-pins_and_profiles.md) — pins vs profiles (extension axis)
* [ADR 0016](0016-hexagonal_setup_tooling.md) — the shape BuildRuntime lives in
* `postgres-setup` — the sibling implementation (extensions instead of modules)
