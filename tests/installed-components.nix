{ pkgs, components, productSource }:
pkgs.runCommand "tamlinux-installed-components"
  {
    nativeBuildInputs = [ pkgs.stdenv.cc pkgs.python3 pkgs.jq ];
  }
  ''
    ${components.tam}/bin/tam --version | grep -q 'tam command 0.25.0'
    if ${components.tam}/bin/tam --version | grep -q '(dev '; then
      echo 'Packaged tam must not carry a development build stamp' >&2
      exit 1
    fi
    ${components.tam}/bin/tam --version | grep -q 'libtam 0.2.0'
    test -x ${components.tam}/bin/tam-man
    printf '<p>Assembly stdin probe</p>\n' | ${components.tam}/bin/tam show - --pipe | grep -q 'Assembly stdin probe'
    ${components.tam}/bin/tam show --pipe welcome | grep -q 'Welcome'
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
    test "$(./consumer)" = '0.2.0'
    mkdir -p $out
    cp consumer consumer.c $out/
  ''
