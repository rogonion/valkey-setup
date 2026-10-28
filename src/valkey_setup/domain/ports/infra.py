"""Fetcher, registry, and reporter ports."""

from pathlib import Path
from typing import Protocol

from valkey_setup.domain.model.build import SourcePin


class SourceFetcher(Protocol):
    """Fetches a pinned source tarball into the local cache, verifying it
    against its pinned sha256. An already-cached tarball is re-verified,
    not re-downloaded. Returns the cached archive path.
    """

    def fetch(self, pin: SourcePin) -> Path: ...


class ImageRegistry(Protocol):
    """Queries and manages local container images."""

    def image_exists(self, tag: str) -> bool: ...
    def prune_cache(self, cache_prefix: str) -> list[str]: ...


class Reporter(Protocol):
    """Progress and warning surface for build stages."""

    def info(self, message: str) -> None: ...
    def warn(self, message: str) -> None: ...
