# 2026-10-31 — Docs prune inventory (public tamlinux-packages)

- **Status:** Executed in working tree; stamp for archived paths is
  `222dd92da4783b0b8173fdcefdbbd4dbe6ee6670` (HEAD before deletes). Filing cards:
  [`FILING-CARD.md`](FILING-CARD.md),
  [`plans/FILING-CARD.md`](plans/FILING-CARD.md),
  [`ai/FILING-CARD.md`](ai/FILING-CARD.md).
- **Scope:** Delivery README, deployment contract, clean-host/agent-skills
  clarify, first-extraction/SDDM/verification archive, superseded candidate
  plans, evidence JSON, closed AI logistics.
- **Method:** Rewrite living contracts → stamp HEAD → delete archives →
  FILING-CARD.

## Summary

| Area | Action |
| --- | --- |
| README, deployment.md, docs/README.md | Rewritten for current contract / 0.5.11 |
| clean-host.md, agent-skills.md | Trimmed; Omarchy cleanup labeled migration |
| first-extraction, verification, sddm-cutover | Archived |
| docs/plans except 0.5.11 | Archived |
| docs/evidence | Archived |
| docs/ai before console-first (except 0.4.8 release + nut) | Archived |
| AI_PROVENANCE.md | Slimmed; points at index + filing card |

Retrieve archived files with `git show 222dd92da4783b0b8173fdcefdbbd4dbe6ee6670:<path>`. Do not treat
filing-card entries as current guidance.
