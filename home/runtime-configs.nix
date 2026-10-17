{
  config,
  lib,
  osConfig,
  ...
}:
let
  seeded = [
    ".config/btop/btop.conf"
    ".tmux.conf"
    "Library/Application Support/Code/User/settings.json"
  ]
  ++ map (path: lib.removePrefix "${toString ../dotfiles}/" (toString path)) (
    builtins.filter (path: builtins.baseNameOf path != "LICENSE") (
      lib.filesystem.listFilesRecursive ../dotfiles/.config/nvim
    )
  );
  seed =
    relative:
    let
      source = ../dotfiles + "/${relative}";
      destination =
        if lib.hasPrefix ".config/" relative then
          "${config.xdg.configHome}/${lib.removePrefix ".config/" relative}"
        else
          "${config.home.homeDirectory}/${relative}";
    in
    ''
      if [ ! -e ${lib.escapeShellArg destination} ] && [ ! -L ${lib.escapeShellArg destination} ]; then
        run mkdir -p ${lib.escapeShellArg (builtins.dirOf destination)}
        run install -m 0600 ${lib.escapeShellArg "${source}"} ${lib.escapeShellArg destination}
      fi
    '';
in
{
  home.file = {
    ".docker/cli-plugins/docker-compose".source =
      config.lib.file.mkOutOfStoreSymlink "${osConfig.homebrew.prefix}/opt/docker-compose/bin/docker-compose";
    ".clang-format".source = ../dotfiles/.clang-format;
    ".vimrc".source = ../dotfiles/.vimrc;
    "Library/Application Support/k9s" = {
      source = ../dotfiles/.config/k9s;
      recursive = true;
    };
  };
  xdg.configFile = lib.genAttrs [ "aerospace" "alacritty" ] (name: {
    source = ../dotfiles/.config + "/${name}";
    recursive = true;
  });
  home.activation.seedRuntimeConfigs = lib.hm.dag.entryAfter [ "linkGeneration" ] (
    lib.concatMapStringsSep "\n" seed seeded
  );
}
