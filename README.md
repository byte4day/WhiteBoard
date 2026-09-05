# Whiteboard

A polished desktop drawing board built with Python and Tkinter. Create quick sketches, annotate ideas, add shapes and text, then export the canvas as a PNG.

Made by **byte4day**.

## Features

- Pen and eraser tools
- Lines, arrows, rectangles, circles, and text
- Object selection, movement, and deletion
- Adjustable brush, eraser, outline, and text sizes
- Fillable shapes and a quick color palette
- Undo and redo
- Zoom, pan, optional grid, and keyboard shortcuts
- Open an image onto the canvas and export drawings to PNG

## Run locally

Requires Python 3.10+ and Pillow.

```bash
python -m pip install Pillow
python app.py
```

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+N` / `Ctrl+O` / `Ctrl+S` | New, open image, save PNG |
| `Ctrl+Z` / `Ctrl+Y` | Undo / redo |
| `P`, `E`, `R`, `C`, `L`, `A`, `T`, `V` | Pen, eraser, rectangle, circle, line, arrow, text, select |
| `G` | Toggle grid |
| `+` / `-` | Zoom in / out |
| `Delete` | Delete selected object |
| `Shift` while drawing | Constrain a shape |

Use the middle mouse button (or right mouse button) to pan the canvas.

## License

This project is available for personal and educational use.
