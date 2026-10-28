"""CLI wiring: pins -> adapters -> use cases."""

from valkey_setup.adapters.cli.config import find_project_root, resolve_profile
from valkey_setup.adapters.infra.buildah import BuildahRegistry, BuildahSandbox
from valkey_setup.adapters.infra.fetcher import HttpxSourceFetcher
from valkey_setup.adapters.infra.reporting import RichReporter
from valkey_setup.application.core import BuildValkey
from valkey_setup.application.modules import BuildModule
from valkey_setup.application.runtime import BuildRuntime


def _core():
    root = find_project_root()
    reporter = RichReporter()
    return (
        root,
        reporter,
        HttpxSourceFetcher(cache_dir=root / ".cache"),
        BuildahSandbox(),
        BuildahRegistry(),
    )


def run_build(profile_name: str | None, *, force: bool, jobs: int | None) -> None:
    root, reporter, fetcher, sandbox, registry = _core()
    pins, profile = resolve_profile(root, profile_name)
    BuildValkey(
        pins=pins, fetcher=fetcher, sandbox=sandbox, registry=registry, reporter=reporter
    ).run(profile, force=force, jobs=jobs)


def run_module(profile_name: str | None, modules: list[str] | None, *, force: bool, jobs: int | None) -> None:
    root, reporter, fetcher, sandbox, registry = _core()
    pins, profile = resolve_profile(root, profile_name)
    builder = BuildModule(
        pins=pins, fetcher=fetcher, sandbox=sandbox, registry=registry, reporter=reporter
    )
    for module in modules or profile.modules:
        builder.run(profile, module, force=force, jobs=jobs)


def run_runtime(profile_name: str | None, *, force: bool, jobs: int | None) -> None:
    root, reporter, fetcher, sandbox, registry = _core()
    pins, profile = resolve_profile(root, profile_name)
    core_builder = BuildValkey(
        pins=pins, fetcher=fetcher, sandbox=sandbox, registry=registry, reporter=reporter
    )
    module_builder = BuildModule(
        pins=pins, fetcher=fetcher, sandbox=sandbox, registry=registry, reporter=reporter
    )
    BuildRuntime(
        pins=pins,
        core_builder=core_builder,
        module_builder=module_builder,
        sandbox=sandbox,
        registry=registry,
        reporter=reporter,
    ).run(profile, force=force, jobs=jobs)


def run_clean(profile_name: str | None, *, cache: bool) -> None:
    root, reporter, fetcher, sandbox, registry = _core()
    pins, profile = resolve_profile(root, profile_name)
    if cache:
        removed = registry.prune_cache(f"valkey-setup/cache/{profile.name}")
        if removed:
            reporter.info(f"pruned {len(removed)} cache image(s)")
        else:
            reporter.info("no cache images to prune")
