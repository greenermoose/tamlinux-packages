{ pkgs, components }:
pkgs.runCommand "tamlinux-installed-components"
  {
    nativeBuildInputs = [ pkgs.stdenv.cc ];
  }
  ''
    ${components.tam}/bin/tam --version | grep -q 'libtam 0.2.0'
    ${components.tam}/bin/tam show --pipe welcome | grep -q 'Welcome'
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
