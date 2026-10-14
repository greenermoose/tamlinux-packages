#!/usr/bin/env python3
"""Build and inspect a development snapshot without changing pins or installation.

Hold exclusive tam-work claims in delivery and product before running. Reports
and command logs stay in the requested directory; only compact results print.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--product', type=Path)
    parser.add_argument('--report-dir', type=Path, required=True)
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    delivery = Path(__file__).resolve().parents[1]
    product = (args.product or delivery.parent / 'tamlinux').resolve(strict=True)
    report = args.report_dir.resolve()
    if any(report.is_relative_to(tree) for tree in (product, delivery)):
        parser.error("Keep report files outside the product/delivery source snapshots")
    report.mkdir(parents=True, exist_ok=True)

    def run(label, argv, accepted=(0,)):
        result = subprocess.run(argv, cwd=delivery, text=True, capture_output=True)
        (report / (label + '.stdout')).write_text(result.stdout)
        (report / (label + '.stderr')).write_text(result.stderr)
        if result.returncode not in accepted:
            raise RuntimeError(f'{label} exited {result.returncode}; see {report / (label + ".stderr")}')
        return result

    # JSON strings are Nix string literals after escaping Nix interpolation.
    def nix_string(value):
        return json.dumps(str(value)).replace('${', '\\${')

    expression = '''let
      assembly = builtins.getFlake DELIVERY;
      pkgs = import assembly.inputs.nixpkgs { system = "x86_64-linux"; };
      snapshot = path: name: builtins.path {
        inherit path name;
        filter = path: type: !(builtins.elem (builtins.baseNameOf path)
          [ ".git" "__pycache__" "result" ]);
      };
      product = { outPath = snapshot PRODUCT "tamlinux-development";
        rev = "development-uncommitted"; };
      delivery = snapshot DELIVERY "tamlinux-delivery-development";
      components = import (delivery + "/nix/packages/default.nix") {
        inherit pkgs; sources = assembly.inputs // { tamlinux = product; };
      };
      outputs = {
        commands = components.tamlinux-commands;
        shell = components.tamlinux-shell;
        plugins = components.tamlinux-plugins;
        tools = components.tamlinux-tools;
        tam = components.tam;
        integration = import (delivery + "/tests/installed-components.nix") {
          inherit pkgs components; productSource = product.outPath;
        };
      };
    in RESULT'''.replace('DELIVERY', nix_string(delivery)).replace('PRODUCT', nix_string(product))
    metadata = expression.replace('RESULT', '''{
      sourceSnapshot = product.outPath;
      deliverySnapshot = delivery;
      outputs = builtins.mapAttrs (_: value: value.outPath) outputs;
    }''')
    common = ['--impure', '--option', 'substituters', 'https://cache.nixos.org'] + (['--offline'] if args.offline else [])
    identities = json.loads(run('identities', ['nix', 'eval', '--json', *common,
                                              '--expr', metadata]).stdout)
    (report / 'identities.json').write_text(json.dumps(identities, indent=2) + '\n')
    # Build the already selected snapshots. A later edit cannot silently make
    # build results differ from the identities recorded above.
    pinned = expression.replace('builtins.getFlake ' + nix_string(delivery),
        'builtins.getFlake ' + nix_string(identities['deliverySnapshot']))
    pinned = pinned.replace('snapshot ' + nix_string(product) + ' "tamlinux-development"',
        'builtins.storePath ' + nix_string(identities['sourceSnapshot']))
    pinned = pinned.replace('snapshot ' + nix_string(delivery) + ' "tamlinux-delivery-development"',
        'builtins.storePath ' + nix_string(identities['deliverySnapshot']))
    built = run('build', ['nix', 'build', '--json', '--no-link', *common,
                         '--expr', pinned.replace('RESULT', 'builtins.attrValues outputs')])
    actual = {value for item in json.loads(built.stdout) for value in item['outputs'].values()}
    if actual != set(identities['outputs'].values()):
        raise RuntimeError('Built output identities differ from selected development snapshots')
    outputs = identities['outputs']
    # Run snapshot scripts: the evidence then belongs to the same recipe tuple.
    snapshot = Path(identities['deliverySnapshot'])
    probes = run('probes', [sys.executable, '-B', str(snapshot / 'tests/installed-desktop-helpers.py'),
                           '--commands', outputs['commands'], '--shell', outputs['shell']])
    audit_args = [sys.executable, '-B', str(snapshot / 'tools/clean-host-audit.py'),
                  '--format', 'compact', '--report', str(report / 'audit.json')]
    for kind in ('commands', 'shell', 'plugins', 'tools', 'tam'):
        audit_args += ['--output', kind + '=' + outputs[kind]]
    audit_run = run('audit', audit_args, accepted=(0, 1))
    audit = json.loads((report / 'audit.json').read_text())
    evidence = {'schema': 1, 'stage': 'Develop; no pin or activation changed',
                **identities, 'installedIntegration': outputs['integration'],
                'probes': json.loads(probes.stdout), 'auditExit': audit_run.returncode,
                'audit': audit,
                'limits': 'Isolated state, recorded host IPC and unavailable services; no clean-host or physical acceptance.'}
    (report / 'evidence.json').write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n')
    print(f"Build/integration passed; {evidence['probes']['passed']} isolated output probes passed.")
    print(f"Audit: {audit['filesScanned']} runtime files; "
          f"{len(audit['missingPackageCommands'])} unresolved lexical names; "
          f"{len(audit['inheritedIdentifierLocations'])} inherited locations; "
          f"ready={audit['candidateReady']}. Full inventory: {report / 'audit.json'}")
    print(f'Evidence: {report / "evidence.json"}')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError) as error:
        sys.exit(str(error))
