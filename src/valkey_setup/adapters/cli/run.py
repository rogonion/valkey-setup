"""CLI wiring: pins -> adapters -> use cases."""

from valkey_setup.adapters.cli.config import (
    find_project_root,
    load_registry_config,
    resolve_profile,
)
from valkey_setup.adapters.infra.buildah import BuildahRegistry, BuildahSandbox, BuildahTransport
from valkey_setup.adapters.infra.fetcher import HttpxSourceFetcher
from valkey_setup.adapters.infra.reporting import RichReporter
from valkey_setup.application.core import BuildValkey
from valkey_setup.application.modules import BuildModule
from valkey_setup.application.publish import PullImages, PushImages
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


def run_runtime(profile_name: str | None, *, force: bool, jobs: int | None, source: str) -> None:
    root, reporter, fetcher, sandbox, registry = _core()
    pins, profile = resolve_profile(root, profile_name)
    registry_config = load_registry_config(root)
    core_builder = BuildValkey(
        pins=pins, fetcher=fetcher, sandbox=sandbox, registry=registry, reporter=reporter
    )
    module_builder = BuildModule(
        pins=pins, fetcher=fetcher, sandbox=sandbox, registry=registry, reporter=reporter
    )
    puller = PullImages(
        pins=pins,
        transport=BuildahTransport(),
        reporter=reporter,
    )
    BuildRuntime(
        pins=pins,
        core_builder=core_builder,
        module_builder=module_builder,
        sandbox=sandbox,
        registry=registry,
        reporter=reporter,
        puller=puller,
        registry_config=registry_config,
    ).run(profile, force=force, jobs=jobs, source=source)


def run_clean(profile_name: str | None, *, cache: bool) -> None:
    root, reporter, fetcher, sandbox, registry = _core()
    pins, profile = resolve_profile(root, profile_name)
    if cache:
        removed = registry.prune_cache(f"valkey-setup/cache/{profile.name}")
        if removed:
            reporter.info(f"pruned {len(removed)} cache image(s)")
        else:
            reporter.info("no cache images to prune")


def run_push(profile_name: str | None) -> None:
    root, reporter, fetcher, sandbox, registry = _core()
    pins, profile = resolve_profile(root, profile_name)
    PushImages(
        pins=pins,
        transport=BuildahTransport(),
        reporter=reporter,
    ).run(profile, load_registry_config(root))


def run_pull(profile_name: str | None) -> None:
    root, reporter, fetcher, sandbox, registry = _core()
    pins, profile = resolve_profile(root, profile_name)
    PullImages(
        pins=pins,
        transport=BuildahTransport(),
        reporter=reporter,
    ).run(profile, load_registry_config(root))
