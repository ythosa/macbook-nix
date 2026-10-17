#!/bin/bash
# Works before Git, Python, Homebrew or Nix have been installed.

fail() { printf 'setup: %s\n' "$*" >&2; exit 1; }

command_line_tools_ready() {
    xcode-select -p >/dev/null 2>&1 &&
        xcrun --find git >/dev/null 2>&1 &&
        xcrun --find make >/dev/null 2>&1 &&
        xcrun --find python3 >/dev/null 2>&1
}

ensure_command_line_tools() {
    if command_line_tools_ready; then return; fi
    printf 'Install Command Line Tools in the Apple dialog. Setup will wait.\n'
    local install_message
    if ! install_message=$(LC_ALL=C xcode-select --install 2>&1); then
        if [[ $install_message != *"install requested"* && $install_message != *"already requested"* ]]; then
            fail "$install_message"
        fi
    fi
    printf '%s\n' "$install_message"
    until command_line_tools_ready; do sleep 5; done
}

run_installer() {
    local url="$1" interpreter="$2"
    shift 2
    local installer
    installer=$(mktemp "${TMPDIR:-/tmp}/macbook-nix-installer.XXXXXX")
    if ! curl -fsSL --retry 3 "$url" -o "$installer"; then
        rm -f "$installer"
        return 1
    fi
    # A piped bootstrap has no terminal on stdin; installers still need one.
    local status=0
    "$interpreter" "$installer" "$@" </dev/tty || status=$?
    rm -f "$installer"
    return "$status"
}

load_brew() {
    if ! command -v brew >/dev/null && [[ -x /opt/homebrew/bin/brew ]]; then
        export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
    fi
    command -v brew >/dev/null || return 1
    [[ $(brew --prefix) == /opt/homebrew ]] || fail 'Homebrew must use its Apple Silicon prefix: /opt/homebrew.'
    local brew_environment
    brew_environment=$(brew shellenv bash) || return 1
    eval "$brew_environment"
}

ensure_brew() {
    if load_brew; then return; fi
    run_installer https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh /bin/bash
    load_brew || fail 'Homebrew installation did not finish.'
}

load_nix() {
    if ! command -v nix >/dev/null; then
        if [[ -r /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh ]]; then
            # The upstream startup script is not written for nounset shells.
            set +u
            . /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
            set -u
        fi
    fi
    command -v nix >/dev/null
}

ensure_nix() {
    if load_nix; then return; fi
    run_installer https://nixos.org/nix/install /bin/sh --daemon
    load_nix || fail 'Nix installation did not finish.'
}

checkout_repo() {
    local destination="$1"
    if [[ -e "$destination" ]]; then
        [[ -f "$destination/flake.nix" && -f "$destination/Makefile" && -e "$destination/.git" ]] ||
            fail "Destination already exists and is not this checkout: $destination"
        [[ $(git -C "$destination" config --get remote.origin.url) =~ ^(https://github.com/|git@github.com:)ythosa/macbook-nix(\.git)?$ ]] ||
            fail "Destination belongs to another repository: $destination"
    else
        mkdir -p "$(dirname "$destination")"
        # Public bootstrap must not require a restored SSH key.
        GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
            git clone https://github.com/ythosa/macbook-nix.git "$destination"
    fi
}

setup_main() {
    [[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || fail 'An Apple Silicon Mac is required.'
    [[ $(id -u) != 0 ]] || fail 'Run setup as your normal macOS user, without sudo.'
    [[ ! -x /usr/local/bin/determinate-nixd ]] ||
        fail 'This setup manages upstream Nix. An existing Determinate installation needs a separate migration.'
    local script_directory destination
    script_directory=$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" && pwd -P)
    destination="${1:-$script_directory}"
    if [[ ! -f "$destination/flake.nix" ]]; then
        destination="${1:-$HOME/projects/macbook-nix}"
    fi
    sudo -v
    ensure_command_line_tools
    ensure_brew
    ensure_nix
    checkout_repo "$destination"
    cd "$destination"
    make check
    make switch
    make plugins
    printf '\nSetup complete. Open a new Terminal window.\n'
}

# Sourcing exposes helpers to isolated tests. Piping also works on a clean Mac.
if [[ -z ${BASH_SOURCE[0]:-} || ${BASH_SOURCE[0]} == "$0" ]]; then
    set -euo pipefail
    setup_main "$@"
fi
