{ pkgs, components, productSource }:
pkgs.runCommand "tamlinux-installed-components"
  {
    nativeBuildInputs = [ pkgs.stdenv.cc pkgs.python3 pkgs.jq pkgs.pkg-config pkgs.binutils pkgs.systemd pkgs.gnumake pkgs.zlib pkgs.ncurses ];
  }
  ''
    ${components.tam}/bin/tam --version | grep -Fxq 'tam command ${components.tam.version}'
    ${components.tam}/bin/tam --version | grep -Fxq 'knowledge corpus ${components.tam.corpusVersion}'
    if ${components.tam}/bin/tam --version | grep -q '(dev '; then
      echo 'Packaged tam must not carry a development build stamp' >&2
      exit 1
    fi
    ${components.tam}/bin/tam --version | grep -Fxq 'libtam ${components.libtam.version}'
    test -x ${components.tam}/bin/tam-man
    printf '<p>Assembly stdin probe</p>\n' | ${components.tam}/bin/tam show - --pipe | grep -q 'Assembly stdin probe'
    ${components.tam}/bin/tam show --pipe welcome | grep -q 'Welcome'
    ${pkgs.lib.optionalString (pkgs.lib.elem "tam-nut" components.tamlinux-commands.passthru.names) ''
      env -i PATH=/not-a-provider ${components.tamlinux-commands}/bin/tam-nut --help | grep -q 'Tamlinux bootstrap'
      ${components.tamlinux-commands}/bin/tam-fleet --help | grep -q 'reconcile'
      ${components.tamlinux-commands}/bin/tam-deploy --help | grep -q 'init'
    ''}
    ${components.tam}/bin/tam explain --pipe SDDM | grep -Fq 'Display Managers: SDDM'
    cmp ${components.tam}/share/tamlinux/knowledge/ecosystem/sddm.html \
      ${components.tam.src}/knowledge/ecosystem/sddm.html
    TAM_PLUGIN_STORAGE_ROOT=${components.tamlinux-plugins}/share/tamlinux/plugins \
      ${pkgs.python3}/bin/python3 -B ${productSource}/desktop/tests/test_plugin_storage.py
    ${pkgs.lib.optionalString (pkgs.lib.elem "tam-shell" components.tamlinux-commands.passthru.names) ''
      ${pkgs.python3}/bin/python3 -B ${./installed-desktop-helpers.py} \
        --commands ${components.tamlinux-commands} --shell ${components.tamlinux-shell} \
        --capture-fixtures ${./fixtures/capture}
    ''}
    set +e
    ${components.tamlinux-tools}/bin/tam-file-select --bogus >stdout 2>stderr
    status=$?
    set -e
    test "$status" = 2
    grep -q 'unknown option --bogus' stderr
    cat > consumer.c <<'EOF'
    #include <tam.h>
    #include <stdio.h>
    int main(void) { puts(tam_version()); return 0; }
    EOF
    cc consumer.c -I${components.libtam}/include -L${components.libtam}/lib \
      -Wl,-rpath,${components.libtam}/lib -ltam -o consumer
    test "$(./consumer)" = '${components.libtam.version}'
    ${pkgs.lib.optionalString (builtins.pathExists "${productSource}/commands/tam-monitor/native.c") ''
      export HOME="$TMPDIR/empty-home"
      mkdir -p "$HOME"
      export PKG_CONFIG_PATH="${components.libtam}/lib/pkgconfig:${pkgs.systemd.dev}/lib/pkgconfig:${pkgs.zlib.dev}/lib/pkgconfig:${pkgs.ncurses.dev}/lib/pkgconfig"
      test "$(pkg-config --variable=prefix libtam-display-session)" = "${components.libtam}"
      pkg-config --atleast-version=0.4.0 libtam-display-session
      cat > display-consumer.c <<'EOF'
    #include <tam_display_session.h>
    int main(void) { return tam_display_session_device(0) != -1; }
    EOF
      cc display-consumer.c $(pkg-config --cflags --libs libtam-display-session) -o display-consumer
      ./display-consumer
      cc display-consumer.c -I${components.libtam}/include \
        ${components.libtam}/lib/libtam-display-session.a ${components.libtam}/lib/libtam-display.a \
        $(pkg-config --libs libsystemd) -o display-consumer-prefix
      ./display-consumer-prefix
      cp -R ${productSource}/commands/tam-monitor "$TMPDIR/monitor-source"
      chmod -R u+w "$TMPDIR/monitor-source"
      make -C "$TMPDIR/monitor-source" LIBTAM_PREFIX=
      make -C "$TMPDIR/monitor-source" LIBTAM_PREFIX=${components.libtam}
      cp -R ${components.tam.src} "$TMPDIR/tam-source"
      chmod -R u+w "$TMPDIR/tam-source"
      make -C "$TMPDIR/tam-source" command LIBTAM_PREFIX=
      make -C "$TMPDIR/tam-source" clean
      make -C "$TMPDIR/tam-source" command LIBTAM_PREFIX=${components.libtam}
      if readelf -d ${components.tam}/bin/.tam-wrapped | grep -Eqi 'systemd|dbus|Qt|gtk'; then
        echo 'Core tam acquired an unintended desktop or display dependency' >&2; exit 1
      fi
      monitor=${components.tamlinux-commands}/bin/.tam-monitor-wrapped
      test -f "$monitor"
      for binary in ${components.tam}/bin/.tam-wrapped ${components.tamlinux-tools}/bin/tam-file-select "$monitor"; do
        readelf -n "$binary" | grep -q 'Build ID:'
        readelf -SW "$binary" | grep -q '\.debug_info'
      done
      readelf -n "$monitor" | grep -q 'Build ID:'
      readelf -S "$monitor" | grep -q '\.debug_info'
      readelf -sW "$monitor" | grep -q tam_display_state_keep
      if readelf -d "$monitor" | grep -Eqi 'python|dbus|Qt|gtk'; then
        echo 'Unexpected monitor dependency' >&2; exit 1
      fi
      cd "$TMPDIR"
      env -i HOME="$HOME" PATH=${pkgs.lib.makeBinPath [ pkgs.coreutils pkgs.gnugrep ]} \
        ${components.tamlinux-commands}/bin/tam-monitor --help | grep -q tam-monitor
    ''}
    mkdir -p $out
    cp consumer consumer.c $out/
  ''
