{
  description = "Pinned Tamlinux packages and reusable user-layer deployment modules";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/d630516d328323b5440895ffcd3b273de93d88e7";
    home-manager = {
      url = "github:nix-community/home-manager/ab97a5d09e0f2aa7339cfd35ec5824fd6653e27c";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    tamlinux = {
      url = "github:greenermoose/tamlinux/a0b07c1ff792ff81ed27cb8b0d14aace6e24c0ef";
      flake = false;
    };
    tam = {
      url = "github:greenermoose/tam/6d060a9c20600e2768cfca5cbba5e0af9502d36b";
      flake = false;
    };
    libtam = {
      url = "github:greenermoose/libtam/02576574d4b1438a1edf510d7a1b357643d2cfcc";
      flake = false;
    };
    tamlinux-tools = {
      url = "github:greenermoose/tamlinux-tools/d8b0912733b1e92a0d3d1f5d039285ffb6b3e49d";
      flake = false;
    };
  };
  outputs =
    inputs@{
      self,
      nixpkgs,
      home-manager,
      tamlinux,
      ...
    }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      components = import ./nix/packages {
        inherit pkgs;
        sources = inputs;
      };
      example = home-manager.lib.homeManagerConfiguration {
        inherit pkgs;
        modules = [
          self.homeManagerModules.default
          ./examples/home.nix
        ];
      };
    in
    {
      lib.packageSets = pkgs: import ./nix/sets { inherit pkgs; };
      homeManagerModules.default = { lib, ... }: {
        imports = [ ./nix/modules ];
        tamlinux.shell.package = lib.mkDefault components.tamlinux-shell;
        tamlinux.shell.pluginPackage = lib.mkDefault components.tamlinux-plugins;
        tamlinux.shell.commandPackage = lib.mkDefault components.tamlinux-commands;
        tamlinux.developer.libraries = lib.mkDefault [ components.libtam pkgs.systemd.dev pkgs.libdrm pkgs.zlib.dev pkgs.ncurses.dev ];
        tamlinux.tools.tam = lib.mkDefault components.tam;
        tamlinux.tools.fileSelect = lib.mkDefault components.tamlinux-tools;
      };
      packages.${system} = components // {
        default = components.tam;
        example-home = example.activationPackage;
      };
      homeConfigurations.example = example;
      checks.${system} = components // {
        fresh-session = import ./tests/session-contract.nix { inherit pkgs home-manager components; };
        agent-skills = import ./tests/agent-skills.nix { inherit pkgs home-manager components; };
        clean-host-audit = import ./tests/clean-host-audit.nix { inherit pkgs; };
        developer-baseline = import ./tests/developer-baseline.nix { inherit pkgs; };
        example-contract = import ./tests/example-contract.nix { inherit pkgs example; };
        assembly-contract = import ./tests/assembly-contract.nix {
          inherit pkgs home-manager;
          module = self.homeManagerModules.default;
          sources = inputs;
        };
        installed-components = import ./tests/installed-components.nix {
          inherit pkgs components;
          productSource = tamlinux;
        };
      };
    };
}
