"""valkey-setup: pinned from-source Valkey builder; images are the artifact store."""

__version__ = "0.2.0"


def main() -> None:
    """Console-script entry point."""
    from valkey_setup.adapters.cli.main import app

    app()
