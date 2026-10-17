{
  lib,
  pkgs,
  ...
}:
{
  # Upstream Nix is pinned by the nixpkgs input in flake.lock.
  nix.package = pkgs.nix;
  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];
  programs.zsh.enable = true;

  # Keep the macOS shell file; user customization belongs in Home Manager.
  environment.etc."zshrc".enable = false;

  # Migrate a link created by an earlier generation to an ordinary file before
  # nix-darwin cleans up links whose targets are absent from the new /etc/static.
  # Leave existing regular files alone.
  system.activationScripts.preActivation.text = lib.mkAfter ''
    if [[ -L /etc/zshrc && $(readlink /etc/zshrc) == /etc/static/zshrc ]]; then
      zshrcCopy=$(mktemp /etc/zshrc.nix-migration.XXXXXX)
      if ! cp -pL /etc/zshrc "$zshrcCopy"; then
        rm -f "$zshrcCopy"
        exit 1
      fi
      if [[ -L /etc/zshrc && $(readlink /etc/zshrc) == /etc/static/zshrc ]]; then
        mv -f "$zshrcCopy" /etc/zshrc
      else
        rm -f "$zshrcCopy"
      fi
    fi
  '';
}
