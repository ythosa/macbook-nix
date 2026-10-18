{
  config,
  lib,
  nvim-config,
  osConfig,
  pkgs,
  ...
}:
let
  nvimSource = pkgs.applyPatches {
    name = "nvim-config";
    src = nvim-config;
    patches = [ ./nvim-compat.patch ];
  };
  seeded = [
    {
      source = ../.config/btop/btop.conf;
      destination = "${config.xdg.configHome}/btop/btop.conf";
    }
    {
      source = ../.config/tmux/tmux.conf;
      destination = "${config.home.homeDirectory}/.tmux.conf";
    }
    {
      source = ../.config/vscode/settings.json;
      destination = "${config.home.homeDirectory}/Library/Application Support/Code/User/settings.json";
    }
  ]
  ++
    map
      (
        source:
        let
          relative = lib.removePrefix "${nvim-config}/" (toString source);
        in
        {
          source = "${nvimSource}/${relative}";
          destination = "${config.xdg.configHome}/nvim/${relative}";
        }
      )
      (
        builtins.filter (
          source:
          !(builtins.elem (builtins.baseNameOf source) [
            "LICENSE"
            "README.md"
            ".vimrc"
          ])
        ) (lib.filesystem.listFilesRecursive nvim-config.outPath)
      );
  seed =
    { source, destination }:
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
    ".clang-format".source = ../.config/clang-format/config.yaml;
    ".vimrc".source = ../.config/vim/vimrc;
    "Library/Application Support/k9s" = {
      source = ../.config/k9s;
      recursive = true;
    };
  };
  xdg.configFile = lib.genAttrs [ "aerospace" "alacritty" ] (name: {
    source = ../.config + "/${name}";
    recursive = true;
  });
  home.activation.seedRuntimeConfigs = lib.hm.dag.entryAfter [ "linkGeneration" ] (
    lib.concatMapStringsSep "\n" seed seeded
  );
}
