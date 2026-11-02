# Curated terminal games and simulations

Tamlinux boots visibly to a text virtual terminal (VT) before optional
graphics. The curated terminal games and simulations packaged here provide
intellectually substantive exploration directly from that text console,
addressing computer science, cognition, natural sciences, society, and
complex emergent systems.

This document records the curated subset packaged for candidate 0.6.1 under
decision D214. The full research catalog of candidates is in the dated
investigation report.

## Packaging and module integration

The package set is exposed through:
- **Flake package set:** `(lib.packageSets pkgs).terminalGames` in `flake.nix`
- **Home Manager module:** `tamlinux.terminalGames` in `nix/modules/games.nix`

`tamlinux.terminalGames.enable` defaults to `tamlinux.session.enable`, so
console-first workstation profiles receive the curated set automatically. Minimal
profiles can disable it explicitly:

```nix
tamlinux.terminalGames.enable = false;
```

When enabled, the curated executables are linked into the Home Manager profile
(`~/.nix-profile/bin`) and are immediately executable from any VT session or via
`start`.

## Curated selection and rationale

| Title | Command | Intellectual domain | Primary insight | License |
| :--- | :--- | :--- | :--- | :--- |
| **Cataclysm: DDA** | `cataclysm-dda` | Systems physiology, thermodynamics | Detailed metabolic biochemistry, encumbrance, vehicle engineering | CC-BY-SA-3.0 / GPL-2.0+ |
| **Frotz** | `frotz <story>` | Cognition, linguistics, AI modeling | Distributed robotics (*Suspended*), interrogation theory of mind (*Spider and Web*), longitudinal social decay (*A Mind Forever Voyaging*) | GPL-2.0+ |
| **BSD Games** | `trek`, `adventure`, `atc`, `wump` | History, physics, operations research | Operations research under uncertainty (`trek`), Colossal Cave exploration (`adventure`), air traffic control (`atc`), topological deduction (`wump`) | BSD-3-Clause |
| **Astroterm** | `astroterm` | Astronomy, celestial mechanics | Real-time Keplerian orbital calculations, precession, Yale Bright Star Catalog (9,000+ stars) | GPL-3.0+ |
| **Curse of War** | `curseofwar` | Macroeconomics, logistics, war | Infrastructure-driven warfare, logistical draw, demographic exhaustion | GPL-3.0+ |
| **GNU Go** | `gnugo --mode curses` | Combinatorics, spatial cognition | Emergent strategic depth, territorial balance, intuition vs tactical sacrifice | GPL-3.0+ |
| **pMARS** | `pmars` | Computer science, virtual machines | Core War assembly (Redcode), self-modifying code, instruction pointer combat | GPL-2.0+ |
| **Bastet** | `bastet` | AI, game tree heuristics | Minimax adversarial search calculating worst-case tetromino drop | GPL-3.0+ |
| **cbonsai** | `cbonsai` | Algorithmic botany, fractals | Procedural bonsai growth using Lindenmayer systems (L-systems) | GPL-3.0+ |
| **VMS Empire** | `vms-empire` | 4X grand strategy, logistics | Industrial production cycles, supply lines, strategic fog of war | GPL-2.0+ |
| **NetHack** | `nethack` | Emergent physical causality | Consistent object-oriented causal physics (conductivity, petrification, reflection) | Nethack GPL |

## Console operational guide

Each title runs within the kernel DRM/KMS framebuffer console (`/dev/tty1`–`tty6`)
without X11 or Wayland dependencies.

### 1. Cataclysm: Dark Days Ahead (`cataclysm-dda`)
- **Package source:** `pkgs.cataclysmDDA.stable.curses` (built strictly for terminal curses; no SDL window).
- **Execution:** Run `cataclysm-dda`.
- **Navigation:** Number pad or vi keys (`h`, `j`, `k`, `l`, `y`, `u`, `b`, `n`). Press `?` for keybindings.
- **Save and Exit:** Press `S` to save and quit, or `Q` to quit without saving.
- **VT Note:** Uses standard ANSI colors. For best character border alignment, a 16-pixel console font (e.g. `Lat2-Terminus16` or `ter-v16n`) is recommended in `/etc/vconsole.conf`.

### 2. Frotz (`frotz`)
- **Package source:** `pkgs.frotz` (ncurses Z-machine interpreter).
- **Execution:** `frotz /path/to/story.z5` (or `.z8`).
- **Interaction:** Natural language text parser (e.g. `examine console`, `ask Iris about sensors`, `wait`).
- **Save and Exit:** Type `save` to save state; type `quit` to exit to the shell.
- **VT Note:** Zero graphical requirements; standard POSIX terminal scrollback and text input.

### 3. BSD Games (`bsdgames`)
- **Package source:** `pkgs.bsdgames`.
- **Key commands:**
  - `trek` — Super Star Trek simulation. Command abbreviations: `pha` (phasers), `tor` (torpedoes), `war` (warp drive), `shi` (shields). Exit by typing `quit`.
  - `adventure` — The original Colossal Cave exploration simulation. Exit with `quit`.
  - `atc` — Real-time air traffic control vectoring simulation. Exit via `q` when safe or `Ctrl+C`.
  - `wump` — Hunt the Wumpus topological deduction. Exit via prompt.

### 4. Astroterm (`astroterm`)
- **Package source:** `pkgs.astroterm`.
- **Execution:** Run `astroterm`.
- **Controls:** Arrow keys or `h`/`j`/`k`/`l` to pan the celestial sphere; `+`/`-` to zoom; `t` to adjust time rate; `q` to exit.
- **VT Note:** Computes real-time astronomical positions using system UTC clock and local coordinates.

### 5. Curse of War (`curseofwar`)
- **Package source:** `pkgs.curseofwar`.
- **Execution:** Run `curseofwar`. Quick skirmish against bots: `curseofwar -i4 -q1 -dee`.
- **Controls:** Arrow keys or `h`/`j`/`k`/`l` to move cursor; `R` or `V` to upgrade infrastructure (Village $\rightarrow$ Town $\rightarrow$ Castle); `Space` to place/remove a rally flag; `q` to quit.

### 6. GNU Go (`gnugo`)
- **Package source:** `pkgs.gnugo`.
- **Execution:** `gnugo --mode curses` (or plain ASCII: `gnugo`).
- **Controls:** Coordinate entry (e.g. `D4`, `Q16`) or curses cursor placement; `quit` to exit.

### 7. pMARS (`pmars`)
- **Package source:** `pkgs.pmars`.
- **Execution:** `pmars -e /path/to/warrior1.red /path/to/warrior2.red` (the `start` menu launches the curses debugger with bundled sample warriors automatically).
- **Controls:** `s` or Space to step cycle, `g` to go, `q` to quit the debugger.

### 8. Bastet (`bastet`)
- **Package source:** `pkgs.bastet`.
- **Execution:** Run `bastet`.
- **Controls:** Arrow keys (Left/Right to move, Up to rotate, Down to drop); `p` to pause; `q` or `Ctrl+C` to quit.

### 9. cbonsai (`cbonsai`)
- **Package source:** `pkgs.cbonsai`.
- **Execution:** `cbonsai -l` (live step-by-step growth animation) or `cbonsai -i` (infinite generation).
- **Controls:** `q` or `Ctrl+C` to exit.

### 10. VMS Empire (`vms-empire`)
- **Package source:** `pkgs.vms-empire`.
- **Execution:** Run `vms-empire`.
- **Controls:** Standard wargame commands; `Q` to quit.

### 11. NetHack (`nethack`)
- **Package source:** `pkgs.nethack`.
- **Execution:** Run `nethack`.
- **Controls:** Vi movement keys (`h`, `j`, `k`, `l`, `y`, `u`, `b`, `n`); `S` to save and quit; `#quit` to exit.

## Hardware compatibility

All eleven packaged titles compile and evaluate cleanly against `nixpkgs` on `x86_64-linux` and require minimal memory and CPU resources:
- **Modern desktop workstation:** High-resolution DRM/KMS console, full 16-color ANSI rendering, ample storage and RAM.
- **Low-spec laptop baseline:** Modest dual-core hardware; all text-mode applications run with minimal memory footprint (typically under 20–50 MB RSS) and zero GPU shader requirements.
- **Rugged portable hardware:** High-contrast text rendering in VT remains legible on outdoor or field displays without compositor overhead.
