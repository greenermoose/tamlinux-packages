{ pkgs, example }:
let
  guard = pkgs.writeShellScript "shell-test-guard" example.config.home.activation.checkShellTest.data;
  revision = example.config.tamlinux.shell.sourceRevision;
in
pkgs.runCommand "tamlinux-shell-test-guard" { } ''
  export XDG_STATE_HOME="$TMPDIR/state"
  mkdir -p "$XDG_STATE_HOME/tamlinux"
  stateFile="$XDG_STATE_HOME/tamlinux/shell-deploy.json"
  ${guard}
  printf '%s\n' '{"previousGeneration":"retained"}' > "$stateFile"
  ${guard}
  printf '%s\n' '{"testedCommit":"${revision}"}' > "$stateFile"
  ${guard}
  printf '%s\n' '{"testedCommit":"other-candidate"}' > "$stateFile"
  if ${guard} > guard.log 2>&1; then
    echo 'Activation accepted a replacement for pending Test' >&2
    exit 1
  fi
  ${pkgs.gnugrep}/bin/grep -q 'would be replaced' guard.log
  printf '%s\n' '{broken' > "$stateFile"
  if ${guard} > guard.log 2>&1; then
    echo 'Activation accepted unreadable Test state' >&2
    exit 1
  fi
  ${pkgs.gnugrep}/bin/grep -q 'Cannot verify' guard.log
  mkdir -p "$out"
''
