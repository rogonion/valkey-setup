# ADR 0019: Registry Distribution of Setup Images

Date - 2026-10-28

## Status

Accepted (drafted in sqlite-setup; replicated into valkey-setup, postgres-setup, and map-stack-prep; amends [ADR 0013](0013-images_sandbox_artifact_store.md)'s "local-only cache" negative)

## Context

ADR 0013 made container images the unit of sandboxing and artifact storage,
with a stated negative: until a registry exists, the image store is local
to one machine, and CI or second machines rebuild from source. The build
time is the whole cost — a fresh machine compiles SQLite/Valkey/PostgreSQL
and their extensions before any work starts.

Since the images are already the distribution unit (version+profile tags,
provenance labels, in-image verification), sharing them needs no change to
the build logic — only a transport and a resolution policy. The open
question was what to share: final images, the hash-keyed cache layers, or
both.

## Decision

1. **Final images only.** Each project publishes its product image:
   the artifact image (sqlite-setup), the runtime image (valkey-setup,
   postgres-setup), the toolchain image (map-stack-prep). Cache layers
   (`*/cache/*:<hash>`) are never published: they are internal build
   accelerators with no consumer-facing identity, a pulled cache set
   costs the same bytes as the final image, and final images already
   serve as the resume point for anyone building on top (postgres
   extensions build FROM the core artifact image).

2. **User-local registry configuration.** `registry.toml` (git-ignored;
   `registry.toml.example` committed) declares a namespace that replaces
   the `localhost/` prefix —
   `localhost/<project>/<image>:<tag>` → `<namespace>/<project>/<image>:<tag>`
   — plus `tls_verify = false` for plain-HTTP LAN registries. One file per
   repository (map-stack-prep: one at the workspace root). Authentication
   stays out of the file: `buildah login` once.

3. **Explicit publish, resolved consume.** `push` is a deliberate act
   (never auto-run from build steps). Final-output steps resolve a missing
   image with `--from auto | build | pull` (default auto):
   existing local image wins; else pull if a registry is configured;
   else build from source. `--from build` keeps the from-source path
   explicit; `--from pull` refuses to compile.

4. **From-source builds remain the audit path.** The registry is an
   accelerator, not the source of truth: pins.toml is the replayable
   recipe, images carry the pins in their labels, and consumers should
   treat tags as convenient but digests as the real reference. The
   `--from` modes never bypass the verification contracts.

## Consequences

### Positive

* New machines and CI go from minutes of compilation to a pull; `dist`
  and `runtime` become network-resolvable steps.
* No new trust boundary for a solo namespace: images are built
  deterministically from public pins, and labels make any image's claimed
  provenance inspectable.
* The resolve policy is uniform across the family: same flag, same
  semantics, regardless of project.

### Negative / Trade-offs

* Tags are mutable in registries; a moved tag silently changes what
  `--from pull` fetches — digest-pinning in consumer references is the
  mitigation and is left to consumption records (dist manifests can grow
  a digest field).
* `tls_verify = false` is a footgun for anything beyond a LAN registry;
  the example documents it as LAN-only.
* Multi-arch is out of scope: artifacts are x86-64; arm consumption means
  from-source builds on that architecture.

## References

* [ADR 0013](0013-images_sandbox_artifact_store.md) — the image store being distributed
* [ADR 0014](0014-dist_materialized_cache.md), [ADR 0017](0017-runtime_images_daemons.md) — the steps that gained `--from`
* `registry.toml.example` in each repository; `push`/`pull` commands and poe tasks
