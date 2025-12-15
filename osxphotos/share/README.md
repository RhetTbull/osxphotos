# Shell Completion for osxphotos

osxphotos supports tab completion for bash, zsh, and fish shells. This provides auto-completion for commands, options, and arguments, making it easier to use the CLI.

## Quick Installation

The easiest way to install shell completion is using the built-in command:

```bash
osxphotos shell-completion
```

This will:
- Auto-detect your shell (bash, zsh, or fish)
- Generate the appropriate completion script
- Install it to the XDG-compliant location (`~/.local/share/osxphotos/shell-completion/`)
- Update your shell configuration file to source the completion

After installation, restart your shell or run:
- bash: `source ~/.bashrc` (or `~/.bash_profile` on macOS)
- zsh: `source ~/.zshrc`
- fish: completions are auto-loaded from `~/.config/fish/completions/`

## Manual Installation

If you prefer to install manually or the auto-detection doesn't work:

### Bash

```bash
# Create directory and generate completion
mkdir -p ~/.local/share/osxphotos/shell-completion
_OSXPHOTOS_COMPLETE=bash_source osxphotos > ~/.local/share/osxphotos/shell-completion/osxphotos-completion.bash

# Add to your ~/.bashrc (or ~/.bash_profile on macOS)
echo ". ~/.local/share/osxphotos/shell-completion/osxphotos-completion.bash" >> ~/.bashrc

# Reload
source ~/.bashrc
```

### Zsh

```bash
# Create directory and generate completion
mkdir -p ~/.local/share/osxphotos/shell-completion
_OSXPHOTOS_COMPLETE=zsh_source osxphotos > ~/.local/share/osxphotos/shell-completion/osxphotos-completion.zsh

# Add to your ~/.zshrc
echo ". ~/.local/share/osxphotos/shell-completion/osxphotos-completion.zsh" >> ~/.zshrc

# Reload
source ~/.zshrc
```

### Fish

```bash
# Generate and install
_OSXPHOTOS_COMPLETE=fish_source osxphotos > ~/.config/fish/completions/osxphotos.fish

# Fish auto-loads completions, just restart your shell or run:
fish_update_completions
```

## Using Pre-Generated Completion Files

This directory contains pre-generated completion files:
- `osxphotos-completion.bash` - for bash
- `osxphotos-completion.zsh` - for zsh
- `osxphotos.fish` - for fish

You can use these directly:

**Bash:**
```bash
mkdir -p ~/.local/share/osxphotos/shell-completion
cp osxphotos-completion.bash ~/.local/share/osxphotos/shell-completion/
echo ". ~/.local/share/osxphotos/shell-completion/osxphotos-completion.bash" >> ~/.bashrc
source ~/.bashrc
```

**Zsh:**
```bash
mkdir -p ~/.local/share/osxphotos/shell-completion
cp osxphotos-completion.zsh ~/.local/share/osxphotos/shell-completion/
echo ". ~/.local/share/osxphotos/shell-completion/osxphotos-completion.zsh" >> ~/.zshrc
source ~/.zshrc
```

**Fish:**
```bash
mkdir -p ~/.config/fish/completions
cp osxphotos.fish ~/.config/fish/completions/
```

## For Package Maintainers

If you're packaging osxphotos for distribution (Homebrew, apt, etc.), you can include these completion files in your package:

- **Homebrew:** Place completions in the appropriate `share/` directories
- **Debian/Ubuntu:** Install to `/usr/share/bash-completion/completions/`, `/usr/share/zsh/site-functions/`, etc.
- **System-wide install:** Use the locations expected by your package manager

## Regenerating Completion Files

To regenerate the completion files (for example, after adding new commands or options):

```bash
python scripts/generate_completions.py
```

This will update all completion files in this directory.

## How It Works

osxphotos uses Click's built-in shell completion system. Click dynamically generates completion scripts based on your CLI commands and options. This means:

- Completions are always up-to-date with your CLI structure
- All commands, options, and help text are included
- Custom types and parameters are handled automatically

The completion system provides:
- Command name completion
- Option name completion (including `--help`)
- Subcommand completion
- File and directory path completion where appropriate

## Uninstallation

To remove completions:

**Bash/Zsh:**
1. Remove the source line from your shell config (`~/.bashrc`, `~/.bash_profile`, or `~/.zshrc`)
2. Remove the completion files: `rm -rf ~/.local/share/osxphotos/shell-completion`

**Fish:**
```bash
rm ~/.config/fish/completions/osxphotos.fish
```

## Troubleshooting

**Completion not working:**
1. Make sure you've restarted your shell or sourced the config file
2. Check that the completion script is being sourced (add `echo "osxphotos completion loaded"` to the script for testing)
3. Verify the completion file exists in `~/.local/share/osxphotos/shell-completion/`
4. Try the manual installation method

**Wrong shell detected:**
Use the `--shell` option to specify explicitly:
```bash
osxphotos install-completion --shell zsh
```

**Permission errors:**
The installation needs to write to your home directory. Check file permissions for `~/.bashrc`, `~/.zshrc`, or `~/.config/fish/`.

**Files location:**
Completion files are stored in XDG-compliant locations:
- bash/zsh: `~/.local/share/osxphotos/shell-completion/`
- fish: `~/.config/fish/completions/`

## More Information

For more details on Click's shell completion system, see:
https://click.palletsprojects.com/en/8.1.x/shell-completion/
