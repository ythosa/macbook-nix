{
  description = "MacBook configuration";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    darwin.url = "github:nix-darwin/nix-darwin";
    darwin.inputs.nixpkgs.follows = "nixpkgs";
    home-manager.url = "github:nix-community/home-manager";
    home-manager.inputs.nixpkgs.follows = "nixpkgs";
    nvim-config = {
      url = "github:ythosa/nvim-config";
      flake = false;
    };
  };

  outputs =
    {
      self,
      darwin,
      home-manager,
      nvim-config,
      ...
    }:
    let
      username =
        let
          user = builtins.getEnv "MACBOOK_NIX_USERNAME";
        in
        if user == "" || user == "root" then
          throw "Run make from your macOS user account; it detects the login automatically."
        else
          user;
      macbook = darwin.lib.darwinSystem {
        modules = [
          ./modules/darwin/nix.nix
          ./modules/darwin/macos.nix
          ./modules/darwin/homebrew.nix
          home-manager.darwinModules.home-manager
          {
            nixpkgs.hostPlatform = "aarch64-darwin";
            users.users.${username}.home = "/Users/${username}";
            system = {
              primaryUser = username;
              configurationRevision = self.rev or self.dirtyRev or null;
              stateVersion = 7;
            };
            home-manager = {
              useGlobalPkgs = true;
              useUserPackages = true;
              extraSpecialArgs = { inherit nvim-config; };
              # Source it so a failed backup stops activation before replacement.
              backupCommand = "source ${./scripts/backup-config.sh}";
              users.${username} = ./home;
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
