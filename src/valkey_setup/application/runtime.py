"""Use case: assemble the runtime image for a profile.

Valkey is a daemon: the runtime image is the product (ADR 0013's
per-application choice). The assembly composes artifact images - core
binaries copied in, then each profile module's .so - installs only the
runtime packages, and shapes the image (user, dirs, config, entrypoint,
ports). Missing core/module images are built first.
"""

from pathlib import Path

import valkey_setup.domain.ports.infra as infra_ports
import valkey_setup.domain.ports.sandbox as sandbox_port
from valkey_setup.application.core import BuildValkey
from valkey_setup.application.modules import BuildModule
from valkey_setup.application.publish import PullImages
from valkey_setup.domain.error import ImageNotFoundError, VerificationError
from valkey_setup.domain.model.build import (
    Pins,
    Profile,
    RegistryConfig,
    cache_prefix,
    core_image_tag,
    module_image_tag,
    runtime_image_tag,
)

SOURCES = ("auto", "build", "pull")


class BuildRuntime:
    """Compose core + module artifact images into the runtime image."""

    def __init__(
        self,
        *,
        pins: Pins,
        core_builder: BuildValkey,
        module_builder: BuildModule,
        sandbox: sandbox_port.Sandbox,
        registry: infra_ports.ImageRegistry,
        reporter: infra_ports.Reporter,
        puller: PullImages | None = None,
        registry_config: RegistryConfig | None = None,
    ) -> None:
        self._pins = pins
        self._core = core_builder
        self._modules = module_builder
        self._sandbox = sandbox
        self._registry = registry
        self._reporter = reporter
        self._puller = puller
        self._registry_config = registry_config

    def run(self, profile: Profile, *, force: bool = False, jobs: int | None = None, source: str = "auto") -> str:
        if source not in SOURCES:
            raise ValueError(f"unknown source {source!r}; expected one of {', '.join(SOURCES)}")
        tag = runtime_image_tag(self._pins, profile)
        if not force and self._registry.image_exists(tag):
            self._reporter.info(f"image {tag} already exists (use --force to rebuild)")
            return tag

        pulled = self._resolve_runtime(profile, tag, source)
        if pulled:
            return tag

        core_tag = core_image_tag(self._pins, profile)
        if not self._registry.image_exists(core_tag):
            self._reporter.info(f"core image {core_tag} missing; building it")
            self._core.run(profile, jobs=jobs)
        module_tags: dict[str, str] = {}
        for module in profile.modules:
            module_tag = module_image_tag(self._pins, profile, module)
            if not self._registry.image_exists(module_tag):
                self._reporter.info(f"module image {module_tag} missing; building it")
                self._modules.run(profile, module, jobs=jobs)
            module_tags[module] = module_tag

        self._reporter.info(
            f"assembling runtime {self._pins.valkey.version} "
            f"({', '.join(profile.modules) or 'no modules'}) -> {tag}"
        )
        packages = sorted(
            set(profile.runtime_packages)
            | {p for m in profile.modules for p in self._pins.modules[m].runtime_packages}
        )

        self._sandbox.begin(profile.base_image, cache_prefix(profile, "runtime"))
        try:
            self._sandbox.copy_from_image(core_tag, profile.prefix, profile.prefix)
            self._sandbox.run_cached(
                ["sh", "-c",
                 "zypper --non-interactive refresh && "
                 f"zypper --non-interactive install --no-recommends -- {' '.join(packages)}"],
                cache_keys={
                    "step": "runtime-packages",
                    "packages": ",".join(packages),
                },
            )
            for module in profile.modules:
                artifact = self._pins.modules[module].artifact
                self._sandbox.copy_from_image(
                    module_tags[module],
                    f"{profile.prefix}/modules/{artifact}",
                    f"{profile.prefix}/modules/{artifact}",
                )

            self._setup_user(profile)
            self._setup_config(profile)
            self._verify(profile)

            self._sandbox.set_env(
                {
                    "PATH": f"{profile.prefix}/bin:/usr/bin:/bin",
                    "VALKEY_DATA": profile.data_dir,
                }
            )
            self._sandbox.set_volumes([profile.data_dir])
            self._sandbox.set_ports(profile.ports)
            self._sandbox.set_entrypoint(["/usr/local/bin/entrypoint.sh"])
            self._sandbox.set_cmd(["valkey-server", f"{profile.config_dir}/valkey.conf"])
            self._sandbox.set_user(str(profile.uid))
            self._sandbox.set_labels(
                {
                    **self._pins.labels(),
                    **profile.labels(),
                    **{
                        f"org.valkey-setup.module.{name}.version": version
                        for name, version in self._pins.module_versions(profile).items()
                    },
                }
            )
            self._sandbox.commit(tag)
        finally:
            self._sandbox.finish()

        self._reporter.info(f"runtime image ready: {tag}")
        return tag

    def _resolve_runtime(self, profile: Profile, tag: str, source: str) -> bool:
        """Resolve a missing runtime image: pull when possible, else build.

        Returns True when the image was pulled (assembly skipped - the
        pulled image is the assembled product). --from build keeps the
        from-source path explicit; --from pull refuses to build.
        """
        if self._registry.image_exists(tag) or source == "build":
            return False
        if self._puller is not None:
            self._puller.run(profile, self._registry_config)
            if self._registry.image_exists(tag):
                return True
        if source == "pull":
            raise ImageNotFoundError(
                f"--from pull but image {tag} could not be pulled; "
                "configure registry.toml or use --from build"
            )
        return False

    def _setup_user(self, profile: Profile) -> None:
        self._sandbox.run(
            ["groupadd", "-r", "-g", str(profile.gid), "valkey"]
        )
        self._sandbox.run(
            ["useradd", "-r", "-u", str(profile.uid), "-g", str(profile.gid),
             "-d", profile.data_dir, "-s", "/sbin/nologin", "-c", "Valkey Server", "valkey"]
        )
        self._sandbox.run(["mkdir", "-p", profile.data_dir])
        self._sandbox.run(["chown", "-R", f"{profile.uid}:{profile.gid}", profile.data_dir])

    def _setup_config(self, profile: Profile) -> None:
        self._sandbox.run(["mkdir", "-p", profile.config_dir])
        self._sandbox.copy_in(
            Path(profile.resources) / "valkey.conf",
            f"{profile.config_dir}/valkey.conf",
        )
        self._sandbox.copy_in(
            Path(profile.resources) / "entrypoint.sh",
            "/usr/local/bin/entrypoint.sh",
        )
        self._sandbox.run(["chmod", "+x", "/usr/local/bin/entrypoint.sh"])
        self._sandbox.run(
            ["chown", "-R", f"{profile.uid}:{profile.gid}",
             profile.config_dir, "/usr/local/bin/entrypoint.sh"]
        )

    def _verify(self, profile: Profile) -> None:
        self._reporter.info("verifying runtime inside the image")
        version = self._sandbox.capture(
            [f"{profile.prefix}/bin/valkey-server", "--version"]
        )
        if self._pins.valkey.version not in version:
            raise VerificationError(
                f"runtime valkey-server reports {version.strip()!r}, "
                f"expected {self._pins.valkey.version}"
            )
        for module in profile.modules:
            artifact = self._pins.modules[module].artifact
            listing = self._sandbox.capture(
                ["ls", f"{profile.prefix}/modules/{artifact}"]
            )
            if artifact not in listing:
                raise VerificationError(
                    f"runtime image lacks module artifact {artifact} ({module})"
                )
