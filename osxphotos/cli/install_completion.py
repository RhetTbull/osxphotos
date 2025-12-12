"""Install shell completion for osxphotos."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import click

from .click_rich_echo import rich_click_echo
from .common import get_data_dir


@click.command(name="install-completion")
@click.option(
    "--shell",
    type=click.Choice(["bash", "zsh", "fish"], case_sensitive=False),
    help="Shell type (auto-detected if not specified)",
)
def install_completion(shell: str | None):
    """Install shell completion for osxphotos.

    Installs tab completion for your shell. Supports bash, zsh, and fish.
    The shell type is auto-detected if not specified.

    After installation, restart your shell or source your shell config file
    for the changes to take effect.
    """
    # Auto-detect shell if not specified
    if not shell:
        shell = detect_shell()
        if not shell:
            rich_click_echo(
                "[error]Could not detect shell. Please specify --shell explicitly.[/error]"
            )
            sys.exit(1)
        rich_click_echo(f"Detected shell: {shell}")

    shell = shell.lower()

    # Use XDG data directory for completion files
    completion_dir = get_data_dir() / "shell-completion"
    completion_dir.mkdir(parents=True, exist_ok=True)

    # Determine shell-specific paths and settings
    home = Path.home()

    if shell == "bash":
        completion_file = completion_dir / "osxphotos-completion.bash"
        shell_config = home / ".bashrc"
        if sys.platform == "darwin" and not shell_config.exists():
            # macOS uses .bash_profile by default
            shell_config = home / ".bash_profile"
        source_line = f". {completion_file}\n"
        env_var = "_OSXPHOTOS_COMPLETE=bash_source"

    elif shell == "zsh":
        completion_file = completion_dir / "osxphotos-completion.zsh"
        shell_config = home / ".zshrc"
        source_line = f". {completion_file}\n"
        env_var = "_OSXPHOTOS_COMPLETE=zsh_source"

    elif shell == "fish":
        # Fish still uses its standard location for completions
        fish_completion_dir = home / ".config" / "fish" / "completions"
        fish_completion_dir.mkdir(parents=True, exist_ok=True)
        completion_file = fish_completion_dir / "osxphotos.fish"
        shell_config = None  # Fish auto-loads from completions directory
        source_line = None
        env_var = "_OSXPHOTOS_COMPLETE=fish_source"

    else:
        rich_click_echo(f"[error]Unsupported shell: {shell}[/error]")
        sys.exit(1)

    try:
        # Generate the completion script
        rich_click_echo(f"Generating completion script to {completion_file}...")

        result = subprocess.run(
            ["osxphotos"],
            env={**os.environ, env_var.split("=")[0]: env_var.split("=")[1]},
            capture_output=True,
            text=True,
            check=True,
        )

        completion_file.write_text(result.stdout)
        rich_click_echo("[success]✓[/success] Completion script generated")

        # Add source line to shell config (bash/zsh only)
        if shell_config and source_line:
            if shell_config.exists():
                config_content = shell_config.read_text()
                if source_line.strip() not in config_content:
                    rich_click_echo(f"Adding completion to {shell_config}...")
                    with shell_config.open("a") as f:
                        f.write(f"\n# osxphotos completion\n{source_line}")
                    rich_click_echo("[success]✓[/success] Added to shell config")
                else:
                    rich_click_echo(f"[warning]Completion already in {shell_config}[/warning]")
            else:
                rich_click_echo(
                    f"[warning]Shell config file {shell_config} not found. "
                    f"Please add this line manually:[/warning]\n  {source_line.strip()}"
                )

        rich_click_echo("\n[success]Installation complete![/success]")
        rich_click_echo(f"\nTo activate completion, run: [command]source {shell_config}[/command]")
        rich_click_echo("Or restart your shell.\n")

    except subprocess.CalledProcessError as e:
        rich_click_echo(f"[error]Failed to generate completion script: {e}[/error]")
        sys.exit(1)
    except Exception as e:
        rich_click_echo(f"[error]Installation failed: {e}[/error]")
        sys.exit(1)


def detect_shell() -> str | None:
    """Auto-detect the user's shell."""
    # Try SHELL environment variable
    shell_path = os.environ.get("SHELL", "")
    if shell_path:
        shell_name = Path(shell_path).name
        if shell_name in ["bash", "zsh", "fish"]:
            return shell_name

    # Try parent process (works in most cases)
    try:
        import psutil
        parent = psutil.Process(os.getppid())
        parent_name = parent.name()
        for shell in ["bash", "zsh", "fish"]:
            if shell in parent_name.lower():
                return shell
    except ImportError:
        pass
    except Exception:
        pass

    return None
