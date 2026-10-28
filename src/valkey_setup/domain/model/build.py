"""Pydantic models for pinned upstream sources and build profiles.

Pins and profiles are loaded and validated at the CLI boundary from
``pins.toml`` and ``profiles.toml``; valid state is trusted inside the
pipeline (one versions file, checksums pinned, no floating versions).
"""

import os

from pydantic import BaseModel, Field

ARTIFACT_REPOSITORY = "localhost/valkey-setup"
CACHE_PREFIX_TEMPLATE = "valkey-setup/cache/{profile}"


class SourcePin(BaseModel):
    """One pinned upstream source tarball."""

    version: str
    archive: str = Field(pattern=r"\.tar\.gz$")
    url: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @property
    def source_dir(self) -> str:
        """Directory name the tarball extracts to."""
        return self.archive.removesuffix(".tar.gz")


class ModulePin(SourcePin):
    """A pinned loadable module and how its artifact is named."""

    artifact: str = Field(pattern=r"\.so$")
    build_packages: list[str] = Field(default_factory=list)
    runtime_packages: list[str] = Field(default_factory=list)


class Pins(BaseModel):
    """The complete pinned version set: valkey core plus modules."""

    valkey: SourcePin
    modules: dict[str, ModulePin] = Field(default_factory=dict)

    def labels(self) -> dict[str, str]:
        return {
            "org.valkey-setup.valkey.version": self.valkey.version,
            "org.valkey-setup.valkey.sha256": self.valkey.sha256,
        }

    def module_versions(self, profile: "Profile") -> dict[str, str]:
        return {name: self.modules[name].version for name in profile.modules}


class Profile(BaseModel):
    """One named build configuration of the pinned valkey source.

    Selects the build sandbox (base image), build and runtime packages,
    make flags, the install prefix, and the runtime image shape.
    """

    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    base_image: str
    prefix: str = Field(pattern=r"^/[A-Za-z0-9_./-]+$")
    build_packages: list[str]
    build_flags: list[str] = Field(default_factory=list)
    runtime_packages: list[str] = Field(default_factory=list)
    uid: int = Field(ge=1, le=65535)
    gid: int = Field(ge=1, le=65535)
    data_dir: str = Field(pattern=r"^/")
    config_dir: str = Field(pattern=r"^/")
    ports: list[int] = Field(default_factory=list)
    resources: str = "resources"
    modules: list[str] = Field(default_factory=list)
    jobs: int | None = Field(default=None, ge=1)

    def labels(self) -> dict[str, str]:
        return {
            "org.valkey-setup.profile": self.name,
            "org.valkey-setup.prefix": self.prefix,
            "org.valkey-setup.uid": str(self.uid),
            "org.valkey-setup.gid": str(self.gid),
            "org.valkey-setup.modules": ",".join(self.modules),
        }


class Profiles(BaseModel):
    """The complete profile set, plus the profile used when none is named."""

    default: str = "default"
    profiles: dict[str, Profile]

    def resolve(self, name: str | None) -> Profile:
        key = name or self.default
        if key not in self.profiles:
            raise KeyError(key)
        return self.profiles[key]

    def names(self) -> list[str]:
        return list(self.profiles)


def core_image_tag(pins: Pins, profile: Profile) -> str:
    """Tag of the core artifact image (compiled valkey, no modules)."""
    return f"{ARTIFACT_REPOSITORY}/valkey:{pins.valkey.version}-{profile.name}"


def module_image_tag(pins: Pins, profile: Profile, module: str) -> str:
    """Tag of a module artifact image (built .so under the prefix)."""
    return (
        f"{ARTIFACT_REPOSITORY}/module/{module}:"
        f"{pins.modules[module].version}-{profile.name}"
    )


def runtime_image_tag(pins: Pins, profile: Profile) -> str:
    """Tag of the assembled runtime image."""
    return f"{ARTIFACT_REPOSITORY}/runtime:{pins.valkey.version}-{profile.name}"


def cache_prefix(profile: Profile, scope: str = "core") -> str:
    """Layer-cache image prefix for a profile's intermediate steps."""
    return f"{CACHE_PREFIX_TEMPLATE.format(profile=profile.name)}/{scope}"


def effective_jobs(profile: Profile, override: int | None = None) -> int:
    """Parallel compile jobs: CLI override > profile.jobs > half the CPUs.

    Compile parallelism is bounded deliberately: unbounded make -j on a
    memory-constrained host starves during large C++ builds (gRPC).
    """
    if override is not None and override >= 1:
        return override
    if profile.jobs is not None:
        return profile.jobs
    return max(1, (os.cpu_count() or 1) // 2)
