"""Core, module, and runtime use case tests over fakes."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from fakes import FakeFetcher, FakeRegistry, FakeReporter, FakeSandbox  # noqa: E402
from valkey_setup.application.core import BuildValkey  # noqa: E402
from valkey_setup.application.modules import BuildModule  # noqa: E402
from valkey_setup.application.runtime import BuildRuntime  # noqa: E402
from valkey_setup.domain.error import VerificationError  # noqa: E402
from valkey_setup.domain.model.build import (  # noqa: E402
    core_image_tag,
    module_image_tag,
    runtime_image_tag,
)

CORE_TAG = "localhost/valkey-setup/valkey:9.0.1-default"
MODULE_TAG = "localhost/valkey-setup/module/valkey-json:1.0.2-default"
RUNTIME_TAG = "localhost/valkey-setup/runtime:9.0.1-default"


def _builders(pins, sandbox, registry, reporter):
    fetcher = FakeFetcher(Path("/cache/x.tar.gz"))
    return (
        BuildValkey(pins=pins, fetcher=fetcher, sandbox=sandbox, registry=registry, reporter=reporter),
        BuildModule(pins=pins, fetcher=fetcher, sandbox=sandbox, registry=registry, reporter=reporter),
    )


def test_core_build_commits_expected_tag(pins, profile):
    sandbox = FakeSandbox(version_output="Valkey server v=9.0.1 ...")
    core, _ = _builders(pins, sandbox, FakeRegistry(), FakeReporter())
    assert core.run(profile) == CORE_TAG

    kinds = [c[0] for c in sandbox.calls]
    assert kinds == ["begin", "run_cached", "copy_in", "run_cached", "capture", "set_labels", "set_env", "commit", "finish"]
    assert sandbox.calls[-2][1] == CORE_TAG
    compile_call = sandbox.calls[3]
    assert "BUILD_TLS=yes" in " ".join(compile_call[1])
    assert "PREFIX=/usr/local/valkey" in " ".join(compile_call[1])


def test_core_skips_when_image_exists(pins, profile):
    sandbox = FakeSandbox()
    core, _ = _builders(pins, sandbox, FakeRegistry({CORE_TAG}), FakeReporter())
    core.run(profile)
    assert sandbox.calls == []


def test_core_version_mismatch_fails(pins, profile):
    sandbox = FakeSandbox(version_output="v=8.0.0")
    core, _ = _builders(pins, sandbox, FakeRegistry(), FakeReporter())
    with pytest.raises(VerificationError, match="8.0.0"):
        core.run(profile)


def test_module_build_steps_and_recipe(pins, profile):
    sandbox = FakeSandbox(version_output="v=9.0.1")
    _, modules = _builders(pins, sandbox, FakeRegistry(), FakeReporter())
    assert modules.run(profile, "valkey-json") == MODULE_TAG

    kinds = [c[0] for c in sandbox.calls]
    assert kinds == ["begin", "run_cached", "copy_in", "run_cached", "run", "capture", "set_labels", "commit", "finish"]
    compile_call = sandbox.calls[3]
    assert "./build.sh --release" in " ".join(compile_call[1])
    assert compile_call[2]["SERVER_VERSION"] == "9.0.1"
    assert sandbox.calls[-2][1] == MODULE_TAG


def test_module_unpinned_fails(pins, profile):
    _, modules = _builders(pins, FakeSandbox(), FakeRegistry(), FakeReporter())
    with pytest.raises(VerificationError, match="not pinned"):
        modules.run(profile, "valkey-search")


def test_runtime_assembles_core_and_modules(pins, profile, tmp_path):
    sandbox = FakeSandbox(version_output="Valkey server v=9.0.1")
    registry = FakeRegistry({CORE_TAG, MODULE_TAG})
    core, modules = _builders(pins, sandbox, registry, FakeReporter())

    (tmp_path / "resources").mkdir()
    (tmp_path / "resources" / "valkey.conf").write_text("# conf\n")
    (tmp_path / "resources" / "entrypoint.sh").write_text("#!/bin/sh\n")
    profile = profile.model_copy(update={"resources": str(tmp_path / "resources")})

    runtime = BuildRuntime(
        pins=pins,
        core_builder=core,
        module_builder=modules,
        sandbox=sandbox,
        registry=registry,
        reporter=FakeReporter(),
    )
    assert runtime.run(profile) == RUNTIME_TAG

    copies = [c for c in sandbox.calls if c[0] == "copy_from_image"]
    assert copies[0] == ("copy_from_image", CORE_TAG, "/usr/local/valkey", "/usr/local/valkey")
    assert copies[1] == (
        "copy_from_image", MODULE_TAG,
        "/usr/local/valkey/modules/valkeyjson.so", "/usr/local/valkey/modules/valkeyjson.so",
    )
    assert sandbox.calls[-2][1] == RUNTIME_TAG


def test_runtime_builds_missing_dependency_images(pins, profile, tmp_path):
    sandbox = FakeSandbox(version_output="v=9.0.1")
    registry = FakeRegistry()
    core, modules = _builders(pins, sandbox, registry, FakeReporter())

    (tmp_path / "resources").mkdir()
    (tmp_path / "resources" / "valkey.conf").write_text("# conf\n")
    (tmp_path / "resources" / "entrypoint.sh").write_text("#!/bin/sh\n")
    profile = profile.model_copy(update={"resources": str(tmp_path / "resources")})

    runtime = BuildRuntime(
        pins=pins,
        core_builder=core,
        module_builder=modules,
        sandbox=sandbox,
        registry=registry,
        reporter=FakeReporter(),
    )
    tag = runtime.run(profile)
    assert tag == RUNTIME_TAG
    # core and module image builds happened in the same recorded sandbox
    commits = [c[1] for c in sandbox.calls if c[0] == "commit"]
    assert CORE_TAG in commits and MODULE_TAG in commits and RUNTIME_TAG in commits


def test_runtime_skips_when_image_exists(pins, profile):
    sandbox = FakeSandbox()
    core, modules = _builders(pins, sandbox, FakeRegistry({RUNTIME_TAG}), FakeReporter())
    runtime = BuildRuntime(
        pins=pins, core_builder=core, module_builder=modules,
        sandbox=sandbox, registry=FakeRegistry({RUNTIME_TAG}), reporter=FakeReporter(),
    )
    runtime.run(profile)
    assert sandbox.calls == []


def test_image_tag_format(pins, profile):
    assert core_image_tag(pins, profile) == CORE_TAG
    assert module_image_tag(pins, profile, "valkey-json") == MODULE_TAG
    assert runtime_image_tag(pins, profile) == RUNTIME_TAG


def test_jobs_resolution_and_make_flag(pins, profile):
    from valkey_setup.domain.model.build import effective_jobs

    bounded = profile.model_copy(update={"jobs": 6})
    assert effective_jobs(bounded) == 6
    assert effective_jobs(bounded, override=3) == 3
    assert effective_jobs(profile) == max(1, (__import__("os").cpu_count() or 1) // 2)

    sandbox = FakeSandbox(version_output="v=9.0.1")
    core, _ = _builders(pins, sandbox, FakeRegistry(), FakeReporter())
    core.run(bounded)
    compile_call = sandbox.calls[3]
    assert f"make -j6" in " ".join(compile_call[1])


def test_module_recipe_carries_job_limits(pins):
    from valkey_setup.application.modules import module_recipe

    json_recipe = module_recipe(
        "valkey-json", pins.modules["valkey-json"], "9.0.1",
        cflags="-O2", workers=6,
    )
    assert json_recipe.env["MAKEFLAGS"] == "-j6"

    search_recipe = module_recipe(
        "valkey-search", pins.modules["valkey-json"], "9.0.1",
        cflags="-O2", workers=4,
    )
    assert "BUILD_TESTS=OFF" in search_recipe.build_command
    assert "make -j4 libsearch" in search_recipe.build_command

    bloom_recipe = module_recipe(
        "valkey-bloom", pins.modules["valkey-json"], "9.0.1",
        cflags="-O2", workers=2,
    )
    assert "cargo build --release -j 2" in bloom_recipe.build_command


def test_runtime_pull_mode_and_push_mapping(pins, profile, tmp_path):
    from fakes import FakeTransport

    from valkey_setup.application.publish import PullImages, PushImages
    from valkey_setup.domain.error import ConfigError, ImageNotFoundError
    from valkey_setup.domain.model.build import RegistryConfig, remote_image_tag

    # pull mode without a registry: refuses to build
    sandbox = FakeSandbox(version_output="v=9.0.1")
    core, modules = _builders(pins, sandbox, FakeRegistry(), FakeReporter())
    runtime = BuildRuntime(
        pins=pins, core_builder=core, module_builder=modules,
        sandbox=sandbox, registry=FakeRegistry(), reporter=FakeReporter(),
    )
    with pytest.raises(ImageNotFoundError, match="pull"):
        runtime.run(profile, source="pull")

    # auto with a configured registry and a remote image: pulls, no build
    registry = FakeRegistry()
    transport = FakeTransport(registry)
    config = RegistryConfig(namespace="reg.example.org", tls_verify=False)
    transport.remote_has.add(remote_image_tag(RUNTIME_TAG, config))
    sandbox = FakeSandbox(version_output="v=9.0.1")
    core, modules = _builders(pins, sandbox, registry, FakeReporter())
    puller = PullImages(pins=pins, transport=transport, reporter=FakeReporter())
    runtime = BuildRuntime(
        pins=pins, core_builder=core, module_builder=modules,
        sandbox=sandbox, registry=registry, reporter=FakeReporter(),
        puller=puller, registry_config=config,
    )
    assert runtime.run(profile, source="auto") == RUNTIME_TAG
    assert transport.pulls == [(remote_image_tag(RUNTIME_TAG, config), RUNTIME_TAG)]
    assert registry.image_exists(RUNTIME_TAG)
    assert sandbox.calls == []  # nothing compiled

    # push maps the local runtime tag to the configured namespace
    with pytest.raises(ConfigError, match="registry.toml"):
        PushImages(pins=pins, transport=transport, reporter=FakeReporter()).run(profile, None)
    remote = PushImages(pins=pins, transport=transport, reporter=FakeReporter()).run(profile, config)
    assert remote == remote_image_tag(RUNTIME_TAG, config)
    assert (RUNTIME_TAG, remote) in transport.pushes
