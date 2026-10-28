"""Shared fixtures: pin and profile models used across the suite."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from valkey_setup.domain.model.build import (  # noqa: E402
    ModulePin,
    Pins,
    Profile,
    SourcePin,
)


@pytest.fixture
def pins() -> Pins:
    return Pins(
        valkey=SourcePin(
            version="9.0.1",
            archive="valkey-9.0.1.tar.gz",
            url="https://example.org/valkey-9.0.1.tar.gz",
            sha256="a" * 64,
        ),
        modules={
            "valkey-json": ModulePin(
                version="1.0.2",
                archive="valkey-json-1.0.2.tar.gz",
                url="https://example.org/valkey-json-1.0.2.tar.gz",
                sha256="b" * 64,
                artifact="valkeyjson.so",
                build_packages=["cmake", "gcc-c++"],
            ),
        },
    )


@pytest.fixture
def profile() -> Profile:
    return Profile(
        name="default",
        base_image="registry.example.org/base:1.0",
        prefix="/usr/local/valkey",
        build_packages=["gcc", "make"],
        build_flags=["BUILD_TLS=yes", "MALLOC=jemalloc"],
        runtime_packages=["shadow", "libjemalloc2"],
        uid=999,
        gid=999,
        data_dir="/var/lib/valkey/data",
        config_dir="/usr/share/valkey/config",
        ports=[6379],
        resources="resources",
        modules=["valkey-json"],
    )
