"""Use case: build the pinned valkey core artifact image for a profile.

Orchestrates ports only: the source fetcher, the container sandbox, the
image registry, and the reporter. Step order, cache keys, image naming,
and the verification contract live here.
"""

import valkey_setup.domain.ports.infra as infra_ports
import valkey_setup.domain.ports.sandbox as sandbox_port
from valkey_setup.domain.error import VerificationError
from valkey_setup.domain.model.build import (
    Pins,
    Profile,
    cache_prefix,
    core_image_tag,
    effective_jobs,
)


class BuildValkey:
    """Compile pinned valkey into the core artifact image."""

    def __init__(
        self,
        *,
        pins: Pins,
        fetcher: infra_ports.SourceFetcher,
        sandbox: sandbox_port.Sandbox,
        registry: infra_ports.ImageRegistry,
        reporter: infra_ports.Reporter,
    ) -> None:
        self._pins = pins
        self._fetcher = fetcher
        self._sandbox = sandbox
        self._registry = registry
        self._reporter = reporter

    def run(self, profile: Profile, *, force: bool = False, jobs: int | None = None) -> str:
        tag = core_image_tag(self._pins, profile)
        if not force and self._registry.image_exists(tag):
            self._reporter.info(f"image {tag} already exists (use --force to rebuild)")
            return tag

        pin = self._pins.valkey
        workers = effective_jobs(profile, jobs)
        self._reporter.info(
            f"building valkey {pin.version} ({profile.name} profile, -j{workers}) -> {tag}"
        )
        archive = self._fetcher.fetch(pin)
        flags = " ".join(profile.build_flags)

        self._sandbox.begin(profile.base_image, cache_prefix(profile, "core"))
        try:
            self._sandbox.run_cached(
                ["sh", "-c",
                 "zypper --non-interactive refresh && "
                 f"zypper --non-interactive install -- {' '.join(profile.build_packages)}"],
                cache_keys={
                    "step": "build-packages",
                    "packages": ",".join(sorted(profile.build_packages)),
                },
            )
            self._sandbox.copy_in(archive, f"/tmp/{pin.archive}")
            self._sandbox.run_cached(
                ["sh", "-c",
                 f"cd /tmp && tar -xf {pin.archive} && "
                 f"cd {pin.source_dir} && "
                 f"make -j{workers} {flags} && "
                 f"make install PREFIX={profile.prefix}"],
                cache_keys={
                    "step": "compile",
                    "version": pin.version,
                    "sha256": pin.sha256,
                    "flags": ",".join(sorted(profile.build_flags)),
                    "jobs": str(workers),
                },
            )

            self._reporter.info("verifying built valkey inside the image")
            version = self._sandbox.capture(
                [f"{profile.prefix}/bin/valkey-server", "--version"]
            )
            if pin.version not in version:
                raise VerificationError(
                    f"built valkey-server reports {version.strip()!r}, "
                    f"expected {pin.version}"
                )

            self._sandbox.set_labels({**self._pins.labels(), **profile.labels()})
            self._sandbox.set_env({"PATH": f"{profile.prefix}/bin:/usr/bin:/bin"})
            self._sandbox.commit(tag)
        finally:
            self._sandbox.finish()

        self._reporter.info(f"core artifact image ready: {tag}")
        return tag
