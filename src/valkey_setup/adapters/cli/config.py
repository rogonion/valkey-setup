"""pins.toml / profiles.toml loading and project-root discovery (CLI boundary)."""

import tomllib
from pathlib import Path

from pydantic import ValidationError

from valkey_setup.domain.error import ConfigError
from valkey_setup.domain.model.build import Pins, Profiles, RegistryConfig

PINS_FILE = "pins.toml"
PROFILES_FILE = "profiles.toml"


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from ``start`` (default: cwd) to the folder holding pins.toml."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / PINS_FILE).exists():
            return candidate
    raise ConfigError(f"could not locate {PINS_FILE}: run from the valkey-setup project root (or below it)")


def _load_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc


def load_pins(root: Path) -> Pins:
    try:
        return Pins.model_validate(_load_toml(root / PINS_FILE))
    except ValidationError as exc:
        raise ConfigError(f"invalid {root / PINS_FILE}: {exc}") from exc


def load_profiles(root: Path) -> Profiles:
    path = root / PROFILES_FILE
    data = _load_toml(path)
    profiles_raw = data.pop("profiles", None)
    if profiles_raw is None:
        raise ConfigError(f"invalid {path}: missing [profiles] table")
    for key, spec in profiles_raw.items():
        spec.setdefault("name", key)
    try:
        profiles = Profiles.model_validate(
            {"default": data.get("default", "default"), "profiles": profiles_raw}
        )
    except ValidationError as exc:
        raise ConfigError(f"invalid {path}: {exc}") from exc
    if profiles.default not in profiles.profiles:
        raise ConfigError(f"invalid {path}: default profile {profiles.default!r} is not defined")
    return profiles


def resolve_profile(root: Path, name: str | None):
    """Load pins + profiles and pick the profile by name (or the default)."""
    pins = load_pins(root)
    profiles = load_profiles(root)
    try:
        profile = profiles.resolve(name)
    except KeyError:
        available = ", ".join(profiles.names()) or "(none)"
        raise ConfigError(f"unknown profile {name!r}; available: {available}") from None
    unknown = [m for m in profile.modules if m not in pins.modules]
    if unknown:
        raise ConfigError(
            f"profile {profile.name!r} lists unpinned module(s): {', '.join(unknown)}"
        )
    return pins, profile

REGISTRY_FILE = "registry.toml"


def load_registry_config(root: Path) -> RegistryConfig | None:
    """Load the user-local registry.toml (git-ignored); None when absent."""
    path = root / REGISTRY_FILE
    if not path.exists():
        return None
    try:
        data = tomllib.loads(path.read_text())
        return RegistryConfig.model_validate(data.get("registry", {}))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc
    except ValidationError as exc:
        raise ConfigError(f"invalid {path}: {exc}") from exc
