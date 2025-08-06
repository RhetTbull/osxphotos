import click
import os
from osxphotos.mcp_server.server import run

@click.command("mcp-server")
@click.option("--allow-write", is_flag=True, help="Enable write operations.")
@click.option("--http", type=str, help="Bind to a host and port for HTTP transport (e.g., 'localhost:8080').")
@click.option("--token-env", type=str, help="Environment variable containing the bearer token for HTTP authentication.")
def cli(allow_write, http, token_env):
    """Run the osxphotos MCP server."""
    if allow_write:
        os.environ["OSXPHOTOS_MCP_ALLOW_WRITE"] = "1"

    token = os.environ.get(token_env) if token_env else None

    if http:
        try:
            host, port_str = http.split(":")
            port = int(port_str)
        except ValueError:
            click.echo("Invalid --http format. Use 'host:port'.", err=True)
            return
        
        run(transport="streamable-http", host=host, port=port, token=token)
    else:
        run(transport="stdio")
