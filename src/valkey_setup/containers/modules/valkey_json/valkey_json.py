from pathlib import Path
from typing import Optional

import typer

from .builder import ValkeyJsonBuilder
from valkey_setup.core import load_spec, BuildSpec

app = typer.Typer(help="Add native JSON support.")


@app.command("build", help="Build valkey json binaries from source (valkey json).")
def build(
        version: str = typer.Option("latest", "--version", "--v", help="Bloom version."),
        spec_file: Optional[Path] = typer.Option("configs/build.yaml", "--spec", "--s",
                                                 help="Path to build specification file."),
        cache_prefix: Optional[str] = typer.Option("", "--cache-prefix", "--c",
                                                   help="Optional. Custom prefix for generated images acting as cache layers.")
):
    """
    Build valkey json binaries from source (valkey json).

    :param version: Version of valkey json to build.
    :param spec_file: Path to build spec file.
    :param cache_prefix: Custom prefix for cache layers generated.

    :return:
    """
    config = load_spec(spec_file, BuildSpec)

    builder = ValkeyJsonBuilder(config, version, cache_prefix)
    builder.build()


@app.command("delete-cache", help="Delete cache images used to build valkey json binaries from source (valkey json).")
def delete_cache(
        spec_file: Optional[Path] = typer.Option("configs/build.yaml", "--spec", "--s",
                                                 help="Path to build specification file."),
        cache_prefix: Optional[str] = typer.Option("", "--cache-prefix", "--c",
                                                   help="Optional. Custom prefix for generated images acting as cache layers.")
):
    """
    Delete cache images used to build valkey json binaries from source (valkey json).

    :param spec_file: Path to build spec file.
    :param cache_prefix: Custom prefix for cache layers generated.

    :return:
    """
    config = load_spec(spec_file, BuildSpec)

    builder = ValkeyJsonBuilder(config, cache_prefix)

    builder.prune_cache_images()
