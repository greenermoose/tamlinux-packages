{
  description = "Pinned Tamlinux packages and reusable user-layer deployment modules";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/8ce4ef6cb6f871616146b9fe26d2a5ae594e94fe";
    home-manager = {
      url = "github:nix-community/home-manager/150f9ce4ddd41544ea42eb9d6043a75bd615fa24";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    tamlinux = {
      url = "github:greenermoose/tamlinux/f618970456ef05b1514506efb3bc7458cab7fa1d";
      flake = false;
    };
    tam = {
      url = "github:greenermoose/tam/efbd1037b1fab10375e8c729d7dd793358123217";
      flake = false;
    };
    libtam = {
      url = "github:greenermoose/libtam/c081708b5ed2c8ade4ecdf171cebc110c2cb316f";
      flake = false;
    };
    tamlinux-tools = {
      url = "github:greenermoose/tamlinux-tools/194d6750f42a0a03911661dbdca4c5d1637542cd";
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
        tamlinux.shell.source = lib.mkDefault tamlinux;
        tamlinux.shell.sourceRevision = lib.mkDefault tamlinux.rev;
      };
      packages.${system} = components // {
        default = components.tam;
        example-home = example.activationPackage;
      };
      homeConfigurations.example = example;
      checks.${system} = components // {
        developer-baseline = import ./tests/developer-baseline.nix { inherit pkgs; };
        example-contract = import ./tests/example-contract.nix { inherit pkgs example; };
        shell-test-guard = import ./tests/shell-test-guard.nix { inherit pkgs example; };
        installed-components = import ./tests/installed-components.nix { inherit pkgs components; };
      };
    };
}
