"""list command for osxphotos CLI"""

import json

import click

import osxphotos

from .cli_params import JSON_OPTION


@click.command(name="list")
@JSON_OPTION
@click.pass_obj
@click.pass_context
def list_libraries(ctx, cli_obj, json_):
    """Print list of Photos libraries found on the system."""

    # implemented in _list_libraries so it can be called by other CLI functions
    # without errors due to passing ctx and cli_obj
    _list_libraries(json_=json_ or cli_obj.json, error=False)


def _list_libraries(json_=False, error=True):
    """Print list of Photos libraries found on the system.
    If json_ == True, print output as JSON (default = False)"""

    photo_libs = osxphotos.utils.list_photo_libraries()
    sys_lib = osxphotos.utils.get_system_library_path()
    last_lib = osxphotos.utils.get_last_library_path()

    if json_:
        libs = {
            "photo_libraries": photo_libs,
            "system_library": sys_lib,
            "last_library": last_lib,
        }
        click.echo(json.dumps(libs, ensure_ascii=False))
    else:
        last_lib_flag = sys_lib_flag = False

        for lib in photo_libs:
            if lib == sys_lib:
                click.echo(f"(*)\t{lib}", err=error)
                sys_lib_flag = True
            elif lib == last_lib:
                click.echo(f"(#)\t{lib}", err=error)
                last_lib_flag = True
            else:
                click.echo(f"\t{lib}", err=error)

        if sys_lib_flag or last_lib_flag:
            click.echo("\n", err=error)
        if sys_lib_flag:
            click.echo("(*)\tSystem Photos Library", err=error)
        if last_lib_flag:
            click.echo("(#)\tLast opened Photos Library", err=error)
