#!/usr/bin/env bash
# Exercise tam against its installed output and the selected runtime manuals.
set -euo pipefail

tam=${1:?usage: tam-package-navigation.sh TAM KNOWLEDGE INFOPATH MANPATH}
knowledge=${2:?usage: tam-package-navigation.sh TAM KNOWLEDGE INFOPATH MANPATH}
infopath=${3:?usage: tam-package-navigation.sh TAM KNOWLEDGE INFOPATH MANPATH}
manpath=${4:?usage: tam-package-navigation.sh TAM KNOWLEDGE INFOPATH MANPATH}
command_version=${5:?expected command version is required}
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

export HOME="$tmp/home"
export XDG_CONFIG_HOME="$tmp/config"
export XDG_STATE_HOME="$tmp/state"
if [[ ${TAM_PACKAGE_NATURAL_ENV:-0} == 1 ]]; then
    unset TAM_KNOWLEDGE_DIR INFOPATH MANPATH
else
    export TAM_KNOWLEDGE_DIR="$knowledge"
    export INFOPATH="$infopath"
    export MANPATH="$manpath"
fi
mkdir -p "$HOME" "$XDG_CONFIG_HOME" "$XDG_STATE_HOME"
cd "$tmp"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'ok - %s\n' "$1"; }

version=$(<"$knowledge/version")
"$tam" --version | grep -Fxq "tam command $command_version" \
    || fail 'packaged command version is wrong'
"$tam" --version | grep -Fq "knowledge corpus $version" \
    || fail 'packaged corpus version is wrong'
pass 'installed command and corpus versions'

"$tam" show --pipe | grep -q 'The Tamlinux User Guide' \
    || fail 'packaged guide root did not render'
"$tam" show welcome --pipe | grep -q 'Welcome to Tamlinux' \
    || fail 'packaged welcome page did not render'
pass 'guide root and welcome page resolve from the package'

"$tam" search --pipe 'change file owner' | grep -qi 'permissions' \
    || fail 'packaged guide search did not find permissions content'
pass 'guide search resolves indexed packaged content'

"$tam" man tam --pipe | grep -q 'tam - terminal entry point' \
    || fail 'tam man did not render its packaged manual'
pass 'tam man helper resolves the packaged manual'

"$tam" info coreutils --pipe | grep -q 'GNU Coreutils' \
    || fail 'tam info did not render the Coreutils manual'
"$tam" info coreutils 'head invocation' --pipe \
    | grep -q 'Output the first part of files' \
    || fail 'tam info node lookup did not use runtime Info manuals'
"$tam" show info:coreutils/head\ invocation --pipe \
    | grep -q 'head invocation' \
    || fail 'virtual Info URI did not resolve from the packaged command'
pass 'Info helpers and virtual Info URI resolve runtime manuals'
