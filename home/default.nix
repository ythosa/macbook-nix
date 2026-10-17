{
  imports = [
    ./shell.nix
    ./git.nix
    ./runtime-configs.nix
  ];
  home.stateVersion = "26.05";

  targets.darwin.currentHostDefaults = {
    "com.apple.controlcenter".BatteryShowPercentage = true;
    NSGlobalDomain."com.apple.mouse.tapBehavior" = 1;
  };
}
