#!/usr/bin/env python3
"""Generate shell completion files for osxphotos.

This script generates static completion files for bash, zsh, and fish.
These can be distributed with the package or used for documentation.

Run this script from the repository root:
    python scripts/generate_completions.py
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def generate_completion(shell: str, output_dir: Path) -> None:
    """Generate completion file for a specific shell."""
    print(f"Generating {shell} completion...")

    env_var = f"_OSXPHOTOS_COMPLETE={shell}_source"

    if shell == "fish":
        output_file = output_dir / "osxphotos.fish"
    else:
        output_file = output_dir / f"osxphotos-completion.{shell}"

    try:
        result = subprocess.run(
            ["osxphotos"],
            env={**os.environ, env_var.split("=")[0]: env_var.split("=")[1]},
            capture_output=True,
            text=True,
            check=True,
        )

        output_file.write_text(result.stdout)
        print(f"  ✓ Created {output_file}")

    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to generate {shell} completion: {e}")
        raise
    except FileNotFoundError:
        print("  ✗ osxphotos command not found. Make sure it's installed in your environment.")
        raise


def main():
    """Generate all completion files."""
    # Create output directory
    repo_root = Path(__file__).parent.parent
    output_dir = repo_root / "completions"
    output_dir.mkdir(exist_ok=True)

    print(f"Generating completion files in {output_dir}\n")

    # Generate completions for each shell
    for shell in ["bash", "zsh", "fish"]:
        generate_completion(shell, output_dir)

    print("\nCompletion files generated successfully!")
    print(f"\nFiles are in: {output_dir}")
    print("\nUsers can install these with:")
    print("  bash: source completions/osxphotos-completion.bash")
    print("  zsh:  source completions/osxphotos-completion.zsh")
    print("  fish: cp completions/osxphotos.fish ~/.config/fish/completions/")
    print("\nOr use: osxphotos install-completion")


if __name__ == "__main__":
    main()
