#!/bin/bash
# Set up the editable Neovim checkout and missing editor plugins.
set -euo pipefail

clone_missing() (
  local repository=$1 destination=$2 attempt clone_status=1
  if [[ -e "$destination" || -L "$destination" ]]; then
    if [[ ! -d "$destination/.git" && ! -f "$destination/.git" ]]; then
      echo "Plugin path exists but is not a Git checkout: $destination" >&2
      return 1
    fi
    return
  fi
  mkdir -p "$(dirname "$destination")"
  plugin_clone_dir=$(mktemp -d "$(dirname "$destination")/.macbook-nix-plugin.XXXXXX")
  trap 'rm -rf "$plugin_clone_dir"' EXIT
  for attempt in 1 2 3; do
    if git clone --filter=blob:none "$repository" "$plugin_clone_dir/checkout"; then
      if [[ -e "$destination" || -L "$destination" ]]; then
        echo "Plugin path appeared during download: $destination" >&2
        return 1
      fi
      # Rename atomically; never merge a download into an existing checkout.
      /usr/bin/python3 -c 'import os, sys; os.rename(sys.argv[1], sys.argv[2])' \
        "$plugin_clone_dir/checkout" "$destination"
      return
    else
      clone_status=$?
      rm -rf "$plugin_clone_dir/checkout"
      if [[ $attempt != 3 ]]; then
        echo "Plugin download failed; retrying ($attempt/3): $repository" >&2
        sleep 1
      fi
    fi
  done
  return "$clone_status"
)

ensure_nvim_config() (
  local destination="$1/nvim" checkout_root origin
  if [[ -L "$destination" || ( -e "$destination" && ! -d "$destination" ) ]]; then
    echo "Neovim config path must be a regular directory: $destination" >&2
    return 1
  fi

  if [[ -e "$destination/.git" || -L "$destination/.git" ]]; then
    if ! checkout_root=$(git -C "$destination" rev-parse --show-toplevel) || \
      [[ "$checkout_root" != "$(cd "$destination" && pwd -P)" ]]; then
      echo "Neovim config is not a valid Git checkout: $destination" >&2
      return 1
    fi

    origin=$(git -C "$destination" config --local --get remote.origin.url) || origin=
    case "$origin" in
      https://github.com/ythosa/nvim-config|https://github.com/ythosa/nvim-config.git|\
      git@github.com:ythosa/nvim-config|git@github.com:ythosa/nvim-config.git|\
      ssh://git@github.com/ythosa/nvim-config|ssh://git@github.com/ythosa/nvim-config.git)
        return ;;
      *)
        echo "Neovim config has an unexpected origin: $destination ($origin)" >&2
        return 1 ;;
    esac
  fi

  mkdir -p "$1"
  nvim_clone_dir=$(mktemp -d "$1/.macbook-nix-nvim.XXXXXX")
  trap 'rm -rf "$nvim_clone_dir"' EXIT
  clone_missing https://github.com/ythosa/nvim-config.git "$nvim_clone_dir/checkout"
  git -C "$nvim_clone_dir/checkout" config remote.origin.pushurl git@github.com:ythosa/nvim-config.git

  if [[ -d "$destination" && ! -L "$destination" ]]; then
    if [[ -e "$destination/.git" || -L "$destination/.git" ]]; then
      echo "Neovim Git metadata appeared during download: $destination" >&2
      return 1
    fi
    # Adopt existing files without copying, restoring, or replacing any of them.
    /usr/bin/python3 -c 'import os, sys; os.rename(sys.argv[1], sys.argv[2])' \
      "$nvim_clone_dir/checkout/.git" "$destination/.git"
  elif [[ -e "$destination" || -L "$destination" ]]; then
    echo "Neovim config path changed during download: $destination" >&2
    return 1
  else
    /usr/bin/python3 -c 'import os, sys; os.rename(sys.argv[1], sys.argv[2])' \
      "$nvim_clone_dir/checkout" "$destination"
  fi
)

install_vim_plugins() {
  local user_home=$1
  clone_missing https://github.com/VundleVim/Vundle.vim.git "$user_home/.vim/bundle/Vundle.vim"
  # Ignore the missing theme during the first load, then check each install's
  # status: Vundle's interactive PluginInstall command does not fail on errors.
  MACBOOK_NIX_VIMRC="$user_home/.vimrc" \
  MACBOOK_NIX_VUNDLE="$user_home/.vim/bundle/Vundle.vim" \
  vim -Nu NONE -i NONE -n -es -S /dev/stdin <<'VIM'
set nomore
execute 'set runtimepath^=' . fnameescape($MACBOOK_NIX_VUNDLE)
execute 'silent! source ' . fnameescape($MACBOOK_NIX_VIMRC)
if !exists('g:vundle#bundles')
  cquit 1
endif
for plugin in g:vundle#bundles
  if vundle#installer#install(0, plugin.name_spec) ==# 'error'
    cquit 1
  endif
endfor
call vundle#installer#helptags(g:vundle#bundles)
qall
VIM
  # Check a normal startup now that the theme and plugin manager exist.
  vim -Nu "$user_home/.vimrc" -i NONE -n -es -c qall
}

install_tmux_plugins() (
  local user_home=$1
  clone_missing https://github.com/tmux-plugins/tpm.git "$user_home/.tmux/plugins/tpm"
  plugin_socket_dir=$(mktemp -d "${TMPDIR:-/tmp}/macbook-nix-tmux.XXXXXX")
  trap 'tmux -S "$plugin_socket_dir/socket" kill-server >/dev/null 2>&1 || true; rm -rf "$plugin_socket_dir"' EXIT
  # A separate server keeps setup out of existing sessions and shell startup.
  tmux -S "$plugin_socket_dir/socket" -f /dev/null new-session -d -s setup '/bin/sleep 3600'
  tmux -S "$plugin_socket_dir/socket" set-environment -g TMUX_PLUGIN_MANAGER_PATH "$user_home/.tmux/plugins/"
  TMUX="$plugin_socket_dir/socket,0,0" "$user_home/.tmux/plugins/tpm/bin/install_plugins"
)

install_nvim_plugins() {
  local config_home=$1 data_home=$2
  XDG_CONFIG_HOME="$config_home" XDG_DATA_HOME="$data_home" \
    nvim --headless -u "$config_home/nvim/init.lua" \
    -c 'lua local ok, err = pcall(function() require("lazy").install({wait=true,show=false,clear=false,lockfile=true}); assert(vim.v.errmsg == "" and not require("lazy.manage.checker").has_errors(), "Neovim plugin installation failed: " .. vim.v.errmsg) end); if not ok then vim.api.nvim_err_writeln(tostring(err)); vim.cmd("cquit 1") end' \
    -c qall
}

setup_plugins() (
  local user_home=$1 plugin_username config_home
  plugin_username=$(id -un)
  config_home=${XDG_CONFIG_HOME:-$user_home/.config}
  # Public configs and plugins must work before GitHub SSH keys are restored.
  # These process-local settings leave the user's Git configuration untouched.
  export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0
  export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/etc/profiles/per-user/$plugin_username/bin:${GOBIN:-$user_home/go/bin}:$user_home/.local/bin:$PATH"
  ensure_nvim_config "$config_home"
  install_vim_plugins "$user_home"
  install_tmux_plugins "$user_home"
  install_nvim_plugins "$config_home" "${XDG_DATA_HOME:-$user_home/.local/share}"
)

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  if [[ $(id -u) == 0 ]]; then
    echo 'Run plugin setup as your normal macOS user, without sudo.' >&2
    exit 1
  fi
  setup_plugins "$HOME"
fi
