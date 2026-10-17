{
  description = "MacBook configuration";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    darwin.url = "github:nix-darwin/nix-darwin";
    darwin.inputs.nixpkgs.follows = "nixpkgs";
    home-manager.url = "github:nix-community/home-manager";
    home-manager.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    {
      self,
      darwin,
      home-manager,
      ...
    }:
    let
      machine = {
        username = "ythosa";
      };
      macbook = darwin.lib.darwinSystem {
        modules = [
          ./modules/darwin/nix.nix
          ./modules/darwin/macos.nix
          ./modules/darwin/homebrew.nix
          home-manager.darwinModules.home-manager
          {
            nixpkgs.hostPlatform = "aarch64-darwin";
            users.users.${machine.username}.home = "/Users/${machine.username}";
            system = {
              primaryUser = machine.username;
              configurationRevision = self.rev or self.dirtyRev or null;
              stateVersion = 7;
            };
            home-manager = {
              useGlobalPkgs = true;
              useUserPackages = true;
              # Never replace an existing backup during activation.
              backupFileExtension = "before-home-manager";
              users.${machine.username} = ./home;
            };
          }
        ];
      };
    in
    {
      darwinConfigurations = {
        inherit macbook;
      };
      checks.aarch64-darwin = {
        macbook = macbook.config.system.build.toplevel;
      };
      formatter.aarch64-darwin = macbook.pkgs.nixfmt;
    };
}
