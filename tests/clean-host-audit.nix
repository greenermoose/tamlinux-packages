{ pkgs }:
pkgs.runCommand "tamlinux-clean-host-audit-tests"
  { nativeBuildInputs = [ pkgs.python3 pkgs.binutils pkgs.stdenv.cc ]; }
  ''
    mkdir -p tools tests contracts
    cp ${../tools/clean-host-audit.py} tools/clean-host-audit.py
    cp ${../tools/independence-gate.py} tools/independence-gate.py
    cp ${../tools/compiled-qml-audit.py} tools/compiled-qml-audit.py
    cp ${./test_clean_host_audit.py} tests/test_clean_host_audit.py
    cp ${./test_independence_gate.py} tests/test_independence_gate.py
    cp ${./test_compiled_qml_audit.py} tests/test_compiled_qml_audit.py
    cp ${../contracts/arch-hyprland.json} contracts/arch-hyprland.json
    python3 -B -m unittest discover -s tests -p test_clean_host_audit.py -v
    python3 -B -m unittest discover -s tests -p test_independence_gate.py -v
    python3 -B -m unittest discover -s tests -p test_compiled_qml_audit.py -v
    mkdir -p $out
    cp contracts/arch-hyprland.json $out/
  ''
