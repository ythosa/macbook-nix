# MacBook setup

Apps, macOS settings, and personal config files for **Apple Silicon Macs**.
Nix manages settings, config files, Alacritty, and the Python SQL formatter; Homebrew installs the other apps. Your macOS username is detected automatically.

## Set up a Mac

This repository is private. First authenticate GitHub and clone it. For example, after [setting up your SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh):

```sh
mkdir -p ~/projects
git clone git@github.com:ythosa/macbook-nix.git ~/projects/macbook-nix
cd ~/projects/macbook-nix
```

From the repository folder, run this one setup command as your normal macOS user:

```sh
/bin/bash setup.sh
```

GitHub authentication and the initial clone are manual prerequisites. If macOS asks to install Command Line Tools while cloning, finish Apple's installer, then repeat `git clone`.

Setup installs missing Command Line Tools, [Homebrew](https://docs.brew.sh/Installation), and [upstream Nix](https://nixos.org/download/), applies the configuration, and installs Vim, tmux, and Neovim plugins. Existing tools and plugin repositories are kept. `/bin/bash setup.sh` also works before `make` is available.

Enter your password when asked. During Nix installation, allow Terminal to administer your computer if macOS asks. Command Line Tools install automatically with retries; if Apple's installer dialog opens, finish it. Setup waits for these dialogs. When it finishes, open a new Terminal window.

No username or folder paths need editing. The saved preferences include Moscow time, dark mode, and the application firewall turned off; see [Change the setup](#change-the-setup) to customize them.

Run the commands below from this repository's folder. Use `make`, which supplies the detected username and required Nix flags. Setup needs administrator access, available Apple installers, and a working connection to GitHub, Nix, Brew, and app download sites. It can be rerun after an interrupted download.

## Common commands

| Command | What it does |
| --- | --- |
| `make` / `make check` | Run safety tests and validate the configuration |
| `make build` | Build without applying changes; output is linked at `result` |
| `make setup` | Install missing tools, apply everything, and install editor plugins |
| `make switch` | Build and apply settings, config files, and Brew apps |
| `make apps` | Install missing Brew apps without changing system settings |
| `make apps-check` | Check whether Brew apps are installed |
| `make plugins` | Install missing Vim, tmux, and Neovim plugins |
| `make brewfile` | Generate a local `Brewfile` from the app list |
| `make fmt` | Format Nix files; requires `rg` from ripgrep |
| `make update` | Update Nix dependencies and the Neovim source version in `flake.lock` |

## Change the setup

| What to change | Where to edit |
| --- | --- |
| Apps and fonts | [modules/darwin/homebrew.nix](modules/darwin/homebrew.nix) |
| Alacritty and Python SQL formatter (Nix packages) | [home/default.nix](home/default.nix) |
| Dock, Finder, trackpad, timezone, firewall | [modules/darwin/macos.nix](modules/darwin/macos.nix) |
| Shell, shortcuts, PATH, Node version manager | [home/shell.nix](home/shell.nix) |
| Git name, email, shortcuts, SSH URL rules | [home/git.nix](home/git.nix) |
| App config files | [.config/](.config/) and the rules below |
| Neovim config | [ythosa/nvim-config](https://github.com/ythosa/nvim-config), pinned in `flake.lock` |
| Rules for installing config files | [home/runtime-configs.nix](home/runtime-configs.nix) |

Add new files to Git with `git add path/to/file` so Nix can see them. Then apply your changes:

```sh
make check
make switch
```

**Adding an app:** add its Brew name to `homebrew.nix`, then run the commands above. A config file alone does not install its app.

**Removing an app:** remove its entry from `homebrew.nix`, then uninstall it. Removing the entry alone leaves the installed app in place. Replace `NAME` with its Brew name:

```sh
HOMEBREW_NO_AUTOREMOVE=1 brew uninstall NAME        # command-line tool
HOMEBREW_NO_AUTOREMOVE=1 brew uninstall --cask NAME # Mac app
```

Choose the matching command. The flag keeps Brew from also removing other unused dependencies.

## Where to edit config files

| Configs | Where to edit | What setup does |
| --- | --- | --- |
| zsh, Git, clang-format, AeroSpace, Alacritty, k9s, Vim | In this repository, then `make switch` | Links files to the Nix-managed version |
| Neovim, btop, tmux, VS Code | In your home folder | Copies missing files once; keeps existing files |

Linked files are read-only. Setup moves replaced files into unique adjacent backup folders such as `.zshrc.before-home-manager.ABC123/`. Previous backups are kept. If a backup cannot be made, setup stops before replacing that file.

**For Neovim, btop, tmux, and VS Code, existing files are kept, even if they contain app defaults.** To replace a copied config with this repository's version: close the app, move that specific file to a backup, then run `make switch`. Copy local edits back into `.config/` to carry them to another Mac; Neovim changes belong in its separate repository.

New apps can create configs normally. To include one in this setup, copy its config into `.config/APP/`, add an installation rule in `home/runtime-configs.nix`, and add the new file to Git. Keep caches, history, keys, and app data out of the repository.

Neovim is fetched automatically from its own repository as a Nix source input. No Git submodule commands are needed. To update only its starter files, run `nix --extra-experimental-features 'nix-command flakes' flake update nvim-config`, review `flake.lock`, then run `make check` and `make switch`. Existing editable Neovim files are kept; the new source version is used for missing files and new Macs. A small [compatibility patch](home/nvim-compat.patch) preserves the fresh-Mac fixes until they are included upstream.

## Finish manually

Restore account logins, licenses, SSH keys, macOS permissions, NVM Node versions, additional npm/Go tools, and VS Code extensions yourself. Colima virtual machines are not copied. Enable Reduce Motion in System Settings if needed.

Public editor plugins are installed over HTTPS without an SSH key. Your normal GitHub URLs still use SSH after setup, so [set up GitHub SSH access](https://docs.github.com/en/authentication/connecting-to-github-with-ssh) for your repositories. GDB needs a code-signing certificate before it can debug macOS processes.

Kotlin's optional language server is enabled only if `kotlin-lsp` is installed.

Private shell variables go in `~/.config/macbook-nix/private-env.sh` (or the same relative path under a custom config folder). Set its permissions with `chmod 600` and keep it outside Git. Files tracked here are copied into the Nix store; do not put secrets in them.

## Updates and problems

- **Update Nix dependencies:** run `make update`, review `git diff flake.lock`, then `make check` and `make switch`. Leave `system.stateVersion` and `home.stateVersion` unchanged during normal updates.
- **PostgreSQL:** setup installs [version 18](https://formulae.brew.sh/formula/postgresql@18) for new Macs. Existing PostgreSQL 14 data and services are kept; database migration is separate.
- **Update a Brew app:** run `brew upgrade NAME`. Brew apps and editor plugins are not pinned by `flake.lock`; setup does not run a general upgrade or remove unrelated apps.
- **An app download failed:** fix the connection or download issue, run `make apps`, then `make switch`. Some settings may already have been applied.
- **`Unexpected files in /etc`:** compare the listed files and back up anything important before following nix-darwin's instructions. Do not delete system files blindly.
- **You see `_nixbld` users or a `nixbld` group:** these are normal Nix build accounts.
- **An existing Determinate or custom Nix installation:** migrate it separately; setup will not replace another Nix daemon or erase unknown system configuration.

To return to the previous Nix system version:

```sh
sudo /run/current-system/sw/bin/darwin-rebuild switch --rollback
```

Rollback does not restore Brew apps, editable config copies, or app data. It may also leave macOS settings that the previous version did not manage.
