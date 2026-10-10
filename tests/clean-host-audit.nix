{ pkgs }:
pkgs.runCommand "tamlinux-clean-host-audit-tests"
  { nativeBuildInputs = [ pkgs.python3 ]; }
  ''
    mkdir -p tools tests contracts
    cp ${../tools/clean-host-audit.py} tools/clean-host-audit.py
    cp ${./test_clean_host_audit.py} tests/test_clean_host_audit.py
    cp ${../contracts/arch-hyprland.json} contracts/arch-hyprland.json
    python3 -B -m unittest discover -s tests -p test_clean_host_audit.py -v
    mkdir -p $out
    cp contracts/arch-hyprland.json $out/
  ''
