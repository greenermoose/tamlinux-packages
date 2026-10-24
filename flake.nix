{
  description = "Pinned Tamlinux packages and reusable user-layer deployment modules";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/8ce4ef6cb6f871616146b9fe26d2a5ae594e94fe";
    home-manager = {
      url = "github:nix-community/home-manager/150f9ce4ddd41544ea42eb9d6043a75bd615fa24";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    tamlinux = {
      url = "github:greenermoose/tamlinux/73efb4a98a9be6fe6a690455008645b0f7b016fd";
      flake = false;
    };
    tam = {
      url = "github:greenermoose/tam/eea4509277590380469f83a84939a14c285c107c";
      flake = false;
    };
    libtam = {
      url = "github:greenermoose/libtam/a051ebf457e41a27d47d273bdab291430cabd7ad";
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
