# The module installs shell, plugins and commands from one product revision.
{ pkgs, home-manager, module, sources }:
let
  product = {
    outPath = ./fixtures/product;
    rev = "0000000000000000000000000000000000000000";
  };
  components = import ../nix/packages {
    inherit pkgs;
    sources = sources // { tamlinux = product; };
  };
  hm = home-manager.lib.homeManagerConfiguration {
    inherit pkgs;
    modules = [
      module
      {
        home.username = "alex";
        home.homeDirectory = "/home/alex";
        home.stateVersion = "25.05";
        manual.manpages.enable = false;
        tamlinux.developer.enable = true;
        tamlinux.shell = {
          enable = true;
          package = components.tamlinux-shell;
          pluginPackage = components.tamlinux-plugins;
          commandPackage = components.tamlinux-commands;
          plugins = [ "fred.demo" ];
        };
      }
    ];
  };
  c = hm.config;
  files = "${hm.activationPackage}/home-files";
in
assert components.tamlinux-plugins.passthru.ids == [ "fred.demo" "fred.other" ];
assert components.tamlinux-commands.passthru.names == [ "tam-demo" ];
assert c.home.file.".local/share/tamlinux/shell-revision".text == "${product.rev}\n";
pkgs.runCommand "tamlinux-assembly-contract" { } ''
  set -eu
  resolve() { readlink -f "$1"; }
  case "$(resolve ${files}/.local/share/tamlinux/shell)" in
    ${components.tamlinux-shell}/share/tamlinux/shell) ;;
    *) echo "shell does not resolve into the shell package" >&2; exit 1 ;;
  esac
  case "$(resolve ${files}/.config/tamlinux/plugins/fred.demo)" in
    ${components.tamlinux-plugins}/share/tamlinux/plugins/fred.demo) ;;
    *) echo "plugin does not resolve into the plugin package" >&2; exit 1 ;;
  esac
  test ! -e ${files}/.config/tamlinux/plugins/fred.other
  case "$(resolve ${files}/.local/bin/tam-demo)" in
    ${components.tamlinux-commands}/bin/tam-demo) ;;
    *) echo "command does not resolve into the command package" >&2; exit 1 ;;
  esac
  test "$(${files}/.local/bin/tam-demo)" = demo
  test -x ${files}/.local/bin/tam-menu
  test -f ${files}/.config/tamlinux/menu/default.jsonc
  test ! -e ${files}/.local/bin/tam-protocol-shadow
  mkdir -p $out
''
