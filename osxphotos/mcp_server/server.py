from mcp.server.fastmcp import FastMCP, Context, Image
from .schemas import QueryOptionsLike, PhotoInfoExportOptions
from . import resources, tools_readonly, tools_write, prompts

mcp = FastMCP("osxphotos-mcp")

# --- Resources ---
mcp.resource("osxphotos://library/default")(resources.library_default)
mcp.resource("osxphotos://album/{uuid}")(resources.album_json)
mcp.resource("osxphotos://photo/{uuid}")(resources.photo_json)
mcp.resource("osxphotos://photo/{uuid}/thumb")(resources.photo_thumb)

# --- Tools (safe) ---
mcp.tool()(tools_readonly.list_albums)
mcp.tool()(tools_readonly.search_photos)
mcp.tool()(tools_readonly.photo_info)
from mcp.server.fastmcp import FastMCP, Context, Image
from .schemas import QueryOptionsLike, PhotoInfoExportOptions
from . import resources, tools_readonly, tools_write, prompts

mcp = FastMCP("osxphotos-mcp")

# --- Authentication ---
def auth_handler(token: str, ctx: Context) -> bool:
    """Simple bearer token authentication."""
    return ctx.server.expected_token == token

# --- Resources ---
mcp.resource("osxphotos://library/default")(resources.library_default)
mcp.resource("osxphotos://album/{uuid}")(resources.album_json)
mcp.resource("osxphotos://photo/{uuid}")(resources.photo_json)
mcp.resource("osxphotos://photo/{uuid}/thumb")(resources.photo_thumb)

# --- Tools (safe) ---
mcp.tool()(tools_readonly.list_albums)
mcp.tool()(tools_readonly.search_photos)
mcp.tool()(tools_readonly.photo_info)
mcp.tool()(tools_readonly.estimate_export)

# --- Tools (write) loaded conditionally (env/flag) ---
if tools_write.write_enabled():
    mcp.tool()(tools_write.export_photos)
    mcp.tool()(tools_write.add_keywords)
    mcp.tool()(tools_write.create_album)
    mcp.tool()(tools_write.add_to_album)
    mcp.tool()(tools_write.write_exif)

def run(transport: str = "stdio", host: str = None, port: int = None, token: str = None):
    """
    Runs the MCP server with the specified transport and options.

    :param transport: The transport to use ('stdio' or 'streamable-http').
    :param host: The host to bind to for HTTP transport.
    :param port: The port to bind to for HTTP transport.
    :param token: The bearer token to use for authentication.
    """
    mcp.prompt(title="Caption Helper")(prompts.caption_from_context)
    mcp.prompt(title="Smart Album Query")(prompts.smart_album_query)

    if token:
        mcp.server.expected_token = token
        mcp.auth(auth_handler)
        
    mcp.run(transport=transport, host=host, port=port)


# --- Tools (write) loaded conditionally (env/flag) ---
if tools_write.write_enabled():
    mcp.tool()(tools_write.export_photos)
    mcp.tool()(tools_write.add_keywords)
    mcp.tool()(tools_write.create_album)
    mcp.tool()(tools_write.add_to_album)
    mcp.tool()(tools_write.write_exif)

# --- Prompts ---
mcp.prompt(title="Caption Helper")(prompts.caption_from_context)
mcp.prompt(title="Smart Album Query")(prompts.smart_album_query)

def run(transport: str = "stdio", **kwargs):
    mcp.run(transport=transport, **kwargs)
