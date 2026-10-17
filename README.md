# MacBook setup

Apps, macOS settings, and personal config files for **Apple Silicon Macs**.
Nix manages the system and config files; Homebrew installs apps. Your macOS username is detected automatically.

## Set up a Mac

### 1. Install the required tools

Open Terminal and run:

```sh
xcode-select --install
```

If the tools are already installed, continue. Otherwise, finish the installer. Then install [multi-user Nix for macOS](https://nixos.org/download/) and [Homebrew](https://docs.brew.sh/Installation). Follow their instructions for adding them to your shell.

Open a new Terminal window and run:

```sh
command -v nix brew git make
```

You should see four paths. If a tool is missing, finish its installation before continuing.

### 2. Download this repository

Run this in any folder where you keep projects:

```sh
git clone https://github.com/ythosa/macbook-nix.git
cd macbook-nix
```

### 3. Check the personal settings

- [home/git.nix](home/git.nix): Git name and email.
- [modules/darwin/macos.nix](modules/darwin/macos.nix): macOS preferences. Defaults include Moscow time, dark mode, and the application firewall turned off.

No username or folder paths need editing.

### 4. Apply the setup

```sh
make check
make setup
```

Run these as your normal macOS user. `make setup` asks for your password when it needs administrator access; typing the password shows no characters. Wait for the command to finish, then open a new Terminal window.

Run all commands below from this repository's folder. Use `make`, which supplies the detected username and required Nix flags.

## Common commands

| Command | What it does |
| --- | --- |
| `make` / `make check` | Run safety tests and validate the configuration |
| `make build` | Build without applying changes; output is linked at `result` |
| `make setup` / `make switch` | Build and apply settings, config files, and Brew apps |
| `make apps` | Install missing Brew apps without changing system settings |
| `make apps-check` | Check whether Brew apps are installed |
| `make brewfile` | Generate a local `Brewfile` from the app list |
| `make fmt` | Format Nix files; requires `rg` from ripgrep |
| `make update` | Update Nix dependencies in `flake.lock` |

## Change the setup

| What to change | Where to edit |
| --- | --- |
| Apps and fonts | [modules/darwin/homebrew.nix](modules/darwin/homebrew.nix) |
| Dock, Finder, trackpad, timezone, firewall | [modules/darwin/macos.nix](modules/darwin/macos.nix) |
| Shell, shortcuts, PATH, Node version manager | [home/shell.nix](home/shell.nix) |
| Git name, email, shortcuts, SSH URL rules | [home/git.nix](home/git.nix) |
| App config files | [dotfiles/](dotfiles/) and the rules below |
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

Linked files are read-only. Setup backs up replaced files with `.before-home-manager` and stops if that backup already exists.

**For Neovim, btop, tmux, and VS Code, existing files are kept, even if they contain app defaults.** To replace a copied config with this repository's version: close the app, move that specific file to a backup, then run `make switch`. Copy local edits back into `dotfiles/` to carry them to another Mac.

New apps can create configs normally. To include one in this setup, copy its config into `dotfiles/`, add an installation rule in `home/runtime-configs.nix`, and add the new file to Git. Keep caches, history, keys, and app data out of the repository.

## Finish manually

Restore account logins, licenses, SSH keys, macOS permissions, NVM Node versions, global npm/Go tools, and VS Code extensions yourself. Colima virtual machines are not copied. Enable Reduce Motion in System Settings if needed.

GitHub URLs use SSH after setup, so [set up GitHub SSH access](https://docs.github.com/en/authentication/connecting-to-github-with-ssh) before cloning plugins or other repositories.

For **Vim plugins**, install [Vundle](https://github.com/VundleVim/Vundle.vim#quick-start):

```sh
git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim
vim +PluginInstall +qall
```

For **tmux plugins**, install [TPM](https://github.com/tmux-plugins/tpm#installation):

```sh
git clone https://github.com/tmux-plugins/tpm.git ~/.tmux/plugins/tpm
```

Start tmux, then press **Ctrl+A**, release both keys, and press **Shift+I** to install plugins. If tmux was already running, first run `tmux source-file ~/.tmux.conf`. These keys assume the tmux config from this repository is installed. Skip a clone command if its destination already exists.

Private shell variables go in `~/.config/macbook-nix/private-env.sh` (or the same relative path under a custom config folder). Set its permissions with `chmod 600` and keep it outside Git. Files tracked here are copied into the Nix store; do not put secrets in them.

## Updates and problems

- **Update Nix dependencies:** run `make update`, review `git diff flake.lock`, then `make check` and `make switch`. Leave `system.stateVersion` and `home.stateVersion` unchanged during normal updates.
- **Update a Brew app:** run `brew upgrade NAME`. Brew apps and editor plugins are not pinned by `flake.lock`; setup does not run a general upgrade or remove unrelated apps.
- **An app download failed:** fix the connection or download issue, run `make apps`, then `make switch`. Some settings may already have been applied.
- **A `.before-home-manager` backup blocks setup:** compare it with the current file and keep the version you need before retrying. Do not overwrite backups blindly.
- **`Unexpected files in /etc`:** compare the listed files and back up anything important before following nix-darwin's instructions. Do not delete system files blindly.
- **You see `_nixbld` users or a `nixbld` group:** these are normal Nix build accounts.

To return to the previous Nix system version:

```sh
sudo /run/current-system/sw/bin/darwin-rebuild switch --rollback
```

Rollback does not restore Brew apps, editable config copies, or app data. It may also leave macOS settings that the previous version did not manage.
