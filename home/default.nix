{ pkgs, ... }:
{
  imports = [
    ./shell.nix
    ./git.nix
    ./runtime-configs.nix
  ];
  home.stateVersion = "26.05";
  # Conform needs the Python sqlfmt; Homebrew's sqlfmt is a different tool.
  home.packages = [ pkgs.python3Packages.sqlfmt ];

  targets.darwin.currentHostDefaults = {
    "com.apple.controlcenter".BatteryShowPercentage = true;
    NSGlobalDomain."com.apple.mouse.tapBehavior" = 1;
  };
}
