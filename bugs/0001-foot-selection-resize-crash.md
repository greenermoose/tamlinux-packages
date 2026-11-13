# Bug 0001 — Foot crashes when a mouse selection is dragged across a window resize

- **Status:** Reported.
- **Severity:** High; the terminal window dies with SIGSEGV, ending its shell
  and anything running in it, and losing its scrollback.
- **Affected:** Foot 1.28.0 (Arch `foot 1.28.0-2`), the terminal the native
  contract requires. The same code is unchanged on upstream `master` as of
  2026-11-13. Older versions not checked.
- **Fixed:** None yet.
- **Next:** One more reproduction attempt with the corrected window
  contents below, when Fred chooses; then carry a self-retiring local patch
  and prepare an upstream report for Fred's approval.

## Reproduce

Not yet reproduced on purpose. Four attempts on 2026-11-13 did not crash.
They did confirm two of the three conditions the crash needs, and found why
the third was missing.

The crash needs all three:

1. **The selection stays in progress across the resize.** Confirmed. A
   Wayland protocol log of the test window showed the compositor send the
   keyboard-focus `leave` and the smaller `configure` in the same batch when
   the new window opened. The button stayed held throughout, and Fred saw
   the highlight keep following the mouse after the resize.
2. **The resize changes the rows' absolute numbers.** Missing in every
   attempt. A reflow packs the text into a fresh grid, which only renumbers
   rows if the old grid had freed rows, for example after the scrollback was
   erased (`CSI 3 J`, as `clear` and full-screen programs send). The test
   window printed 400 lines and erased its scrollback before its own first
   resizes, so those early reflows had already packed the grid. A debugger
   trace showed the grid offset at 20 both before and after the test resize,
   and the pivot was unchanged and still correct. In the real crash the
   terminal was a long-running session whose scrollback had been erased
   since its last resize.
3. **The drag direction flips after the resize.** `selection_update()` reads
   the pivot only when the direction changes (`selection.c:1179-1193`). The
   drag starts downward, and after the renumbering every row compares as
   above the stale pivot.

Next attempt (a test script, two Foot windows):

1. Open window A. Wait about two seconds so the window has settled, then
   have it print `seq 1 400`, erase the scrollback (`printf
   '\033[H\033[2J\033[3J'`), and print 60 short lines.
2. Press and hold the left button at the start of a line near the bottom,
   drag down and to the right two or three lines, and keep holding.
3. About seven seconds after A appears, open window B on the same
   workspace. The compositor splits the tile, so A shrinks and B takes
   keyboard focus.
4. Still holding, move the pointer up.

Expected crash point: `selection_update()` at `selection.c:1274`, reached
from `wl_pointer_motion()` (`input.c:2823`), reading through a NULL row
pointer (`segfault at 0`). Running A under gdb with a breakpoint on
`selection_update` that prints `selection.pivot`, `selection.coords` and
`grid->offset` shows whether condition 2 holds without waiting for a crash.

## Expected and actual

Expected: the selection either ends at the resize or carries on correctly at
the new size.

Actual (2026-11-13, observed once): Foot crashed with SIGSEGV. The core dump
(symbolized through Arch's debuginfod) proves the following:

- A character-wise selection was still in progress (`selection.ongoing`
  true) when a pointer-motion event arrived.
- The selection's start and end rows (21 and 22) were valid, but its pivot,
  the anchor where the drag began, was at row 218. The grid only had rows up
  to about 57 after the resize.
- The pointer was above the pivot, so `selection_update()` reversed the
  selection's direction and started it at the pivot (`selection.c:1187-1191`).
  It then looked up row 218, found NULL, and dereferenced it
  (`selection.c:1255`, `1274`).

How the pivot goes stale, from the 1.28.0 source:

- When a window resize reflows the text, `render.c` passes only
  `selection.coords.start` and `.end` as tracking points (`render.c:4389`,
  `4910`). The pivot is not updated.
- To keep that safe, the resize code ends ("finalizes") any ongoing selection
  first, but only on a seat whose **keyboard** focus is this terminal
  (`render.c:4853-4856`). A TODO a few lines below says the pivot must be
  added to the tracking points if selections are ever allowed to stay
  ongoing across a resize.
- The mouse drag belongs to **pointer** focus. When a new window takes
  keyboard focus at the moment it resizes the old one, the drag stays
  ongoing with the old pivot. The next pointer motion past the pivot
  crashes.

The trigger, as Fred reported: he was dragging a selection in the terminal
when an agent opened a new review window, about 70 ms before the crash. That
window would have resized the terminal and taken its keyboard focus. The
compositor does not log the resize itself, so the reproducer below has not
yet confirmed this sequence.

## Workaround

None needed day to day; it takes a drag in progress at the moment another
window opens. Avoid opening windows by script while you are dragging a
selection. An agent opening a review window is the likeliest source.

## Fix and verification

Candidate fixes, both small, in `render.c`:

1. Add `&term->selection.pivot.start` and `&term->selection.pivot.end` to
   both `tracking_points` arrays (what the upstream TODO asks for).
2. Or finalize the selection on resize for a seat whose `mouse_focus` is
   this terminal, not only its `kbd_focus`.

Option 1 fixes the cause; option 2 only widens the guard. Carry the chosen
fix as a self-retiring patch on Foot 1.28.0, run the reproducer above
against the patched build, and record the result here. Filing upstream
(Codeberg `dnkl/foot`) needs Fred's approval, a check of the project's
contribution rules, and an explicit statement of AI use.

Changing the compositor is not expected to retire this bug. The fault is in
Foot's own focus check. Any tiling compositor that resizes the existing
window and focuses the new one in the same moment can trigger it, and Sway
does both by default. The bug retires when Foot fixes it, or if Tamlinux
stops shipping Foot (open question Q27).

## Resolution

Open.
