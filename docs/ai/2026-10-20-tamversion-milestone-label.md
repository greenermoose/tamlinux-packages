# Display-only 0.4.4-m assembly — 2026-10-20

- Tool: Codex CLI `0.163.0`; model `gpt-6.1-sol`, dynamically checked.
- Transcript: Retained privately by the author.
- Prompt:
  > Please update 0.4.4 so that the top bar display says Tamlinux 0.4.4 instead of 0.4.4l. I know that is a change from the 0.4.4l that was approved to Run. Also, I've changed back my time format to 24 hour.
- Selected preparation:
  > Prepare display-only 0.4.4m (recommended).

The m assembly pins product `ef3bc33586b33057a5035f9cc6fcb76924b47dc9`.
Only the product input changes from the accepted l assembly. Tam command
0.31.1/corpus 0.32.1, libtam, tools, nixpkgs and Home Manager retain their
exact l input revisions. The runtime source change is confined to the
`fred.tamversion` milestone-label setting; package version metadata becomes m.

Native l and host-recovery companion h are intentionally retained with their
archive hashes in the delivery record. No native/session/boot/sleep inputs
change and no privileged reinstall is needed solely to match the user-package
letter. The separate workstation MSI repair is outside this candidate.

The standard shell/plugins/commands outputs and installed-components and
example-contract checks all build successfully. The product's widget checks
pass all 11 cases and the complete desktop suite passes 629 tests with one
historical adapter check skipped. These are preparation results, not physical
Test or Run acceptance. Existing delivery records and main/test refs remain
unchanged; the assembly is prepared on develop only.

Checked against: exact l/m flake-lock comparison, product source delta, the
standard five-output build result, delivery record and candidate consistency
check. Consumer-generation preparation, personal settings and activation
observations are retained separately by the operator.
