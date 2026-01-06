import typer
from rich.console import Console
from .valkey_json import app as valkeyjson_app
from .valkey_search import app as valkeysearch_app
from .valkey_bloom import app as valkeybloom_app

app = typer.Typer(help="Modules for the valkey stack.")

console = Console()

app.add_typer(valkeyjson_app, name="valkey-json")
app.add_typer(valkeysearch_app, name="valkey-search")
app.add_typer(valkeybloom_app, name="valkey-bloom")
