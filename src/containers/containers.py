import typer
from rich.console import Console
from .core import app as core_app
from .modules import app as modules_app
from .runtime import app as runtime_app

app = typer.Typer(help="Container components for the valkey stack.")
console = Console()

app.add_typer(core_app, name="core")
app.add_typer(modules_app, name="modules")
app.add_typer(runtime_app, name="runtime")
