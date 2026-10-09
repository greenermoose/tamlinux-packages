{ ... }:
{
  home.username = "alex";
  home.homeDirectory = "/home/alex";
  home.stateVersion = "25.05";
  programs.home-manager.enable = true;
  manual.manpages.enable = false;
  tamlinux.developer.enable = true;
  tamlinux.shell = {
    enable = true;
    layoutSource = ./layout.json;
    settingsSource = ./settings.json;
  };
}
