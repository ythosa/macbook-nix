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

Setup installs missing Command Line Tools, [Homebrew](https://docs.brew.sh/Installation), and [upstream Nix](https://nixos.org/download/), applies the configuration, clones the editable Neovim config, and installs Vim, tmux, and Neovim plugins. Existing tools and plugin repositories are kept. `/bin/bash setup.sh` also works before `make` is available.

Enter your password when asked. During Nix installation, allow Terminal to administer your computer if macOS asks. Command Line Tools install automatically with retries; if Apple's installer dialog opens, finish it. Setup waits for these dialogs. When it finishes, open a new Terminal window.

No username or folder paths need editing. The saved preferences include Moscow time, dark mode, and the application firewall turned off; see [Change the setup](#change-the-setup) to customize them.

Run the commands below from this repository's folder. Use `make`, which supplies the detected username and required Nix flags. Setup needs administrator access, available Apple installers, and a working connection to GitHub, Nix, Brew, and app download sites. It can be rerun after an interrupted download.

## Common commands

| Command | What it does |
| --- | --- |
| `make` / `make check` | Run safety tests and validate the configuration |
| `make build` | Build without applying changes; output is linked at `result` |
| `make setup` | Install missing tools, apply everything, and install editor plugins |
| `make switch` | Build and apply settings, managed configs, and Brew apps; leaves Neovim alone |
| `make apps` | Install missing Brew apps without changing system settings |
| `make apps-check` | Check whether Brew apps are installed |
| `make plugins` | Clone Neovim config if needed and install missing editor plugins |
| `make brewfile` | Generate a local `Brewfile` from the app list |
| `make fmt` | Format Nix files; requires `rg` from ripgrep |
| `make update` | Update Nix dependencies in `flake.lock` |

## Change the setup

| What to change | Where to edit |
| --- | --- |
| Apps and fonts | [modules/darwin/homebrew.nix](modules/darwin/homebrew.nix) |
| Alacritty and Python SQL formatter (Nix packages) | [home/default.nix](home/default.nix) |
| Dock, Finder, trackpad, timezone, firewall | [modules/darwin/macos.nix](modules/darwin/macos.nix) |
| Shell, shortcuts, PATH, Node version manager | [home/shell.nix](home/shell.nix) |
| Git name, email, editor, shortcuts, SSH URL rules | [home/git.nix](home/git.nix) |
| App config files | [.config/](.config/) and the rules below |
| Neovim config | Your Git checkout at `~/.config/nvim` ([ythosa/nvim-config](https://github.com/ythosa/nvim-config)) |
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
| btop, tmux, VS Code | In your home folder | Copies missing files once; keeps existing files |
| Neovim | Directly in `~/.config/nvim`, then commit and push there | Keeps a normal editable Git checkout |

Linked files are read-only. Setup moves replaced files into unique adjacent backup folders such as `.zshrc.before-home-manager.ABC123/`. Previous backups are kept. If a backup cannot be made, setup stops before replacing that file.

**For btop, tmux, and VS Code, existing files are kept, even if they contain app defaults.** To replace a copied config with this repository's version: close the app, move that specific file to a backup, then run `make switch`. Copy local edits back into `.config/` to carry them to another Mac.

New apps can create configs normally. To include one in this setup, copy its config into `.config/APP/`, add an installation rule in `home/runtime-configs.nix`, and add the new file to Git. Keep caches, history, keys, and app data out of the repository.

`make setup` and `make plugins` clone Neovim config into `~/.config/nvim`, or `$XDG_CONFIG_HOME/nvim` when set. An existing plain config folder receives only `.git`: its files, edits, and deletions are preserved. Existing clones keep their branch and remotes. Repeated setup does not pull or reset local changes; normal plugin installation can update `lazy-lock.json`. `make switch` does not manage Neovim.

Edit, commit, and push directly in that checkout. Replace `path/to/file` with the file you changed:

```sh
cd "${XDG_CONFIG_HOME:-$HOME/.config}/nvim"
git add path/to/file
git commit -m "Update Neovim config"
git push
```

Update manually with `git pull --ff-only` in the same folder. Initial cloning uses HTTPS; new or adopted checkouts store an HTTPS fetch URL and an SSH push URL. Use your normal GitHub SSH authentication for pushes.

## Finish manually

Restore account logins, licenses, SSH keys, macOS permissions, NVM Node versions, additional npm/Go tools, and VS Code extensions yourself. Colima virtual machines are not copied. Enable Reduce Motion in System Settings if needed.

Public editor plugins are installed over HTTPS without an SSH key. Your normal GitHub URLs still use SSH after setup, so [set up GitHub SSH access](https://docs.github.com/en/authentication/connecting-to-github-with-ssh) for your repositories. GDB needs a code-signing certificate before it can debug macOS processes.

Kotlin's optional language server is enabled only if `kotlin-lsp` is installed.

Private shell variables go in `~/.config/macbook-nix/private-env.sh` (or the same relative path under a custom config folder). Set its permissions with `chmod 600` and keep it outside Git. Files tracked here are copied into the Nix store; do not put secrets in them.

## Updates and problems

- **Update Nix dependencies:** run `make update`, review `git diff flake.lock`, then `make check` and `make switch`. Leave `system.stateVersion` and `home.stateVersion` unchanged during normal updates.
- **PostgreSQL:** setup installs [version 18](https://formulae.brew.sh/formula/postgresql@18) for new Macs. Existing PostgreSQL 14 data and services are kept; database migration is separate.
- **Update a Brew app:** run `brew upgrade NAME`. Brew apps and editor plugins are not pinned by `flake.lock`; setup does not run a general upgrade or remove unrelated apps.
- **An app download failed:** fix the connection and rerun `make setup`. It keeps installed apps and continues with the remaining setup steps. Some settings may already have been applied.
- **`Unexpected files in /etc`:** compare the listed files and back up anything important before following nix-darwin's instructions. Do not delete system files blindly.
- **You see `_nixbld` users or a `nixbld` group:** these are normal Nix build accounts.
- **An existing Determinate or custom Nix installation:** migrate it separately; setup will not replace another Nix daemon or erase unknown system configuration.

To return to the previous Nix system version:

```sh
sudo /run/current-system/sw/bin/darwin-rebuild switch --rollback
```

Rollback does not restore Brew apps, editable configs, Git checkouts, or app data. It may also leave macOS settings that the previous version did not manage.

## Verification

An earlier revision was tested on 2026-10-18 in an Apple Silicon VM running macOS 26.6.2, initially without Command Line Tools, Homebrew, or Nix. Full setup, repeated setup, and checks after a power cycle passed: all Brew dependencies, Nix daemon, shell, personal config contents, and editor plugins.

This was a resumed installation: interrupted downloads required retries. The VM image's stricter Gatekeeper policy was restored to the standard App Store and known developers mode, and Codex completions were reinstalled after that correction. Gatekeeper remained enabled. GitHub authentication, the initial clone, and macOS permission prompts were not automated.
