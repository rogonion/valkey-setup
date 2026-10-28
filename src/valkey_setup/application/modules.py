"""Use case: build a pinned module artifact image for a profile.

Modules are the valkey analogue of postgres extensions (ADR 0015's
extension axis): each is compiled in its own sandbox from a pinned
tarball, and its .so lands under <prefix>/modules/ in a dedicated
artifact image the runtime assembly copies from.

The per-module build recipe is code in this module (not configuration):
what a recipe contributes is the build command, its env, and the find
pattern that locates the built .so. Transitive fetches the recipes
trigger are documented as pinning gaps in the system overview.
"""

import valkey_setup.domain.ports.infra as infra_ports
import valkey_setup.domain.ports.sandbox as sandbox_port
from valkey_setup.domain.error import VerificationError
from valkey_setup.domain.model.build import (
    ModulePin,
    Pins,
    Profile,
    cache_prefix,
    effective_jobs,
    module_image_tag,
)

SUPPORTED_MODULES = ("valkey-json", "valkey-search", "valkey-bloom")


class ModuleRecipe:
    """Build recipe for one module: build command, env, artifact find spec.

    The .so location is expressed as (find_dir, find_glob) rather than a
    fixed path: upstream build systems place module libraries at target-
    specific paths (build/src/libjson.so, build/src/libsearch.so,
    target/release/libvalkey_bloom.so) and the find keeps the recipe
    honest across them.
    """

    def __init__(self, build_command: str, env: dict[str, str], find_dir: str, find_glob: str) -> None:
        self.build_command = build_command
        self.env = env
        self.find_dir = find_dir
        self.find_glob = find_glob


def module_recipe(name: str, pin: ModulePin, valkey_version: str, cflags: str, workers: int) -> ModuleRecipe:
    """The pinned build recipe for a module, mirroring its upstream build."""
    src = f"/tmp/{pin.source_dir}"
    if name == "valkey-json":
        return ModuleRecipe(
            build_command=f"cd {src} && ./build.sh --release",
            # build.sh's nested makes honor MAKEFLAGS; the explicit -j in
            # cmake's own make is bounded via the jobserver.
            env={"SERVER_VERSION": valkey_version, "CFLAGS": cflags, "MAKEFLAGS": f"-j{workers}"},
            find_dir=f"{src}/build",
            find_glob="libjson.so",
        )
    if name == "valkey-search":
        return ModuleRecipe(
            build_command=(
                f"cd {src} && mkdir -p build && cd build && "
                # BUILD_TESTS=OFF: the gtest targets OOM-kill low-memory
                # hosts under -flto and are not part of the artifact.
                f"cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF && "
                f"make -j{workers} libsearch"
            ),
            env={"CFLAGS": cflags},
            find_dir=f"{src}/build",
            find_glob="libsearch.so",
        )
    if name == "valkey-bloom":
        return ModuleRecipe(
            build_command=f"cd {src} && cargo build --release -j {workers}",
            env={},
            find_dir=f"{src}/target",
            find_glob="libvalkey_bloom.so",
        )
    raise VerificationError(f"no recipe for module {name!r}")


class BuildModule:
    """Compile one pinned module into its own artifact image."""

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

    def run(self, profile: Profile, module: str, *, force: bool = False, jobs: int | None = None) -> str:
        if module not in self._pins.modules:
            raise VerificationError(
                f"module {module!r} is not pinned in pins.toml"
            )
        tag = module_image_tag(self._pins, profile, module)
        if not force and self._registry.image_exists(tag):
            self._reporter.info(f"image {tag} already exists (use --force to rebuild)")
            return tag

        pin = self._pins.modules[module]
        workers = effective_jobs(profile, jobs)
        recipe = module_recipe(
            module, pin, self._pins.valkey.version,
            cflags="-O2 -march=x86-64-v3 -flto", workers=workers,
        )
        self._reporter.info(
            f"building module {module} {pin.version} (-j{workers}) -> {tag}"
        )
        archive = self._fetcher.fetch(pin)
        module_dir = f"{profile.prefix}/modules"

        self._sandbox.begin(profile.base_image, cache_prefix(profile, module))
        try:
            self._sandbox.run_cached(
                ["sh", "-c",
                 "zypper --non-interactive refresh && "
                 f"zypper --non-interactive install -- {' '.join(pin.build_packages)}"],
                cache_keys={
                    "step": "build-packages",
                    "module": module,
                    "packages": ",".join(sorted(pin.build_packages)),
                },
            )
            self._sandbox.copy_in(archive, f"/tmp/{pin.archive}")
            self._sandbox.run_cached(
                ["sh", "-c", f"cd /tmp && tar -xf {pin.archive} && {recipe.build_command}"],
                env=recipe.env,
                cache_keys={
                    "step": "compile",
                    "module": module,
                    "version": pin.version,
                    "sha256": pin.sha256,
                    "env": ",".join(f"{k}={v}" for k, v in sorted(recipe.env.items())),
                },
            )
            self._sandbox.run(
                ["sh", "-c",
                 f"mkdir -p {module_dir} && "
                 f"find {recipe.find_dir} -name '{recipe.find_glob}' "
                 f"-exec cp {{}} {module_dir}/{pin.artifact} \\; && "
                 f"test -s {module_dir}/{pin.artifact}"]
            )

            self._reporter.info(f"verifying {pin.artifact} present in the image")
            listing = self._sandbox.capture(["ls", "-la", f"{module_dir}/{pin.artifact}"])
            if pin.artifact not in listing:
                raise VerificationError(
                    f"module {module} did not produce {pin.artifact}"
                )

            self._sandbox.set_labels(
                {
                    "org.valkey-setup.module": module,
                    "org.valkey-setup.module.version": pin.version,
                    "org.valkey-setup.module.sha256": pin.sha256,
                    "org.valkey-setup.valkey.version": self._pins.valkey.version,
                }
            )
            self._sandbox.commit(tag)
        finally:
            self._sandbox.finish()

        self._reporter.info(f"module artifact image ready: {tag}")
        return tag
