# Batch Change Read Nodes (Nuke)

A Python / PySide UI tool for **Foundry Nuke** that lets you edit properties on
**multiple selected `Read` nodes at once** from a single dialog — instead of
opening each node one by one.

Select all the Read nodes you want to change and hit **`Alt+R`**.

> Published on Nukepedia: [tools/python/ui/batch-change-read-nodes](https://www.nukepedia.com/tools/python/ui/batch-change-read-nodes/)

## What it does

The dialog mirrors Nuke's native *Read* node layout and lets you batch-apply:

- **Input Transform** — colorspace, `Premultiplied`, `Raw Data`, `Auto Alpha`
- **Format** and **Proxy Format**
- **Frame range** — first/last, `hold` / `loop` / `bounce` / `black` before/after,
  plus `expression` / `start at` / `offset` frame modes
- **Original range** — one click to reset first/last to each node's original
  range, or **refresh** the range by re-scanning the sequence on disk
- **Missing frames** — `error` / `black` / `checkerboard` / `nearest frame`
- **Localization policy** + an `Update` button
- **Reload** all selected reads in one go

Every field defaults to `-- keep value --`, so anything you leave untouched is
left as-is. Only the fields you actually change are written back to the nodes.

## Typical use case

You drop in a batch of PBR material sequences and need to change the color
**input transform** (or the start frame, e.g. `1001`) on all of them in one go —
without opening each Read node individually.

## Requirements

- **Foundry Nuke 14+** (uses PySide6). The Qt import block also falls back to
  PySide2, so it should work back to **Nuke 11–13**.
- Tested on **Windows**.

> ⚠️ **Version note (please confirm):** the code targets Nuke 11–13 (PySide2) and
> 14+ (PySide6), while the Nukepedia page currently lists **Nuke 16.0+ / Windows**.
> This is v1.01 and still needs further testing — update this line once you've
> confirmed the supported Nuke range.

## Installation

1. Copy `batch_change_read_nodes.py` to your Nuke scripts folder:

   ```
   ./nuke/scripts/
   ```

2. Add the following to your `menu.py` (same folder) — tweak the menu name and
   hotkey to your liking:

   ```python
   import nuke
   import batch_change_read_nodes

   # Create a custom menu bar entry
   custom_menu = nuke.menu('Nuke').addMenu('Custom Tools/scialpi')

   # Add the command with hotkey Alt + R
   custom_menu.addCommand(
       'Batch Change Read Nodes',
       'batch_change_read_nodes.batch_change_read_nodes()',
       'alt+r'
   )
   ```

3. Restart Nuke (or reload your menus).

## Usage

1. In the node graph, **select one or more `Read` nodes**.
2. Press **`Alt+R`** (or use *Custom Tools → scialpi → Batch Change Read Nodes*).
3. Set any field you want to change. Fields left at `-- keep value --` are
   untouched.
4. Click **OK** to apply to every selected Read node.

A line like `[Batch Read Nodes] Updated N Read node(s).` is printed to the Nuke
console when the changes are applied.

## Files

| File | Description |
|------|-------------|
| `batch_change_read_nodes.py` | The tool — self-contained, no dependencies beyond Nuke + PySide. |

## Notes & TODO

- **v1.01** — initial public release.
- Confirmed Nuke version range and cross-platform (macOS) testing still pending.
- Built and refined with the help of Google and a lot of testing.

## Credits

Created by **mi sci** · [Nukepedia listing](https://www.nukepedia.com/tools/python/ui/batch-change-read-nodes/)

## License

MIT — see [LICENSE](LICENSE).
