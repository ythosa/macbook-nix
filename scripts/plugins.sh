#!/bin/bash
# Install missing editor plugins without changing existing repositories.
set -euo pipefail

clone_missing() {
  local repository=$1 destination=$2
  if [[ -e "$destination" || -L "$destination" ]]; then
    if [[ ! -d "$destination/.git" && ! -f "$destination/.git" ]]; then
      echo "Plugin path exists but is not a Git checkout: $destination" >&2
      return 1
    fi
    return
  fi
  mkdir -p "$(dirname "$destination")"
  git clone --filter=blob:none "$repository" "$destination"
}

install_vim_plugins() {
  local user_home=$1
  clone_missing https://github.com/VundleVim/Vundle.vim.git "$user_home/.vim/bundle/Vundle.vim"
  # Ignore the missing theme during the first load, then check each install's
  # status: Vundle's interactive PluginInstall command does not fail on errors.
  MACBOOK_NIX_VIMRC="$user_home/.vimrc" \
  MACBOOK_NIX_VUNDLE="$user_home/.vim/bundle/Vundle.vim" \
  vim -Nu NONE -i NONE -n -es <<'VIM'
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
    -c 'lua local ok, err = pcall(function() require("lazy").install({wait=true,show=false,clear=false}); assert(vim.v.errmsg == "" and not require("lazy.manage.checker").has_errors(), "Neovim plugin installation failed: " .. vim.v.errmsg) end); if not ok then vim.api.nvim_err_writeln(tostring(err)); vim.cmd("cquit 1") end' \
    -c qall
}

setup_plugins() (
  local user_home=$1
  # Public plugins must work before the user restores their GitHub SSH keys.
  # These process-local settings leave the user's Git configuration untouched.
  export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0
  export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
  install_vim_plugins "$user_home"
  install_tmux_plugins "$user_home"
  install_nvim_plugins "${XDG_CONFIG_HOME:-$user_home/.config}" "${XDG_DATA_HOME:-$user_home/.local/share}"
)

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  if [[ $(id -u) == 0 ]]; then
    echo 'Run plugin setup as your normal macOS user, without sudo.' >&2
    exit 1
  fi
  setup_plugins "$HOME"
fi
