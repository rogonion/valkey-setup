from pathlib import Path
from typing import Optional

import typer

from .builder import ValkeySearchBuilder
from valkey_setup.core import load_spec, BuildSpec

app = typer.Typer(help="Add vector similarity search support.")


@app.command("build", help="Build valkey search binaries from source (valkey search).")
def build(
        version: str = typer.Option("latest", "--version", "--v", help="Bloom version."),
        spec_file: Optional[Path] = typer.Option("configs/build.yaml", "--spec", "--s",
                                                 help="Path to build specification file."),
        cache_prefix: Optional[str] = typer.Option("", "--cache-prefix", "--c",
                                                   help="Optional. Custom prefix for generated images acting as cache layers.")
):
    """
    Build valkey search binaries from source (valkey search).

    :param version: Version of valkey search to build.
    :param spec_file: Path to build spec file.
    :param cache_prefix: Custom prefix for cache layers generated.

    :return:
    """
    config = load_spec(spec_file, BuildSpec)

    builder = ValkeySearchBuilder(config, version, cache_prefix)
    builder.build()


@app.command("delete-cache", help="Delete cache images used to build valkey search binaries from source (valkey search).")
def delete_cache(
        spec_file: Optional[Path] = typer.Option("configs/build.yaml", "--spec", "--s",
                                                 help="Path to build specification file."),
        cache_prefix: Optional[str] = typer.Option("", "--cache-prefix", "--c",
                                                   help="Optional. Custom prefix for generated images acting as cache layers.")
):
    """
    Delete cache images used to build valkey search binaries from source (valkey search).

    :param spec_file: Path to build spec file.
    :param cache_prefix: Custom prefix for cache layers generated.

    :return:
    """
    config = load_spec(spec_file, BuildSpec)

    builder = ValkeySearchBuilder(config, cache_prefix)

    builder.prune_cache_images()
