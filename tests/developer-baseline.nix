{ pkgs }:
pkgs.runCommand "tamlinux-developer-baseline"
  {
    nativeBuildInputs = (import ../nix/sets { inherit pkgs; }).developer;
  }
  ''
    cat > hello.c <<'EOF'
    #include <stdio.h>
    #include <stdlib.h>
    int main(void) {
      char *p = malloc(16);
      if (!p) return 1;
      snprintf(p, 16, "tamlinux C");
      puts(p);
      free(p);
      return 0;
    }
    EOF
    gcc -std=c11 -Wall -Wextra -Werror hello.c -o hello
    test "$(./hello)" = 'tamlinux C'
    command -v as ld make git bash curl nano
    test -s ${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt
    mkdir -p $out
    cp hello.c hello $out/
  ''
