import base64
import io
import math
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageFont


@dataclass
class Shape:
    kind: str
    coords: list[float]
    color: str
    width: int
    fill: str = ""
    text: str = ""
    font_size: int = 18
    image: Optional[Image.Image] = None
    item_id: Optional[int] = None
    photo: Optional[tk.PhotoImage] = None


@dataclass
class HistoryCommand:
    undo: Callable[[], None]
    redo: Callable[[], None]


class WhiteboardApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Whiteboard — Made by byte4day")
        self.root.minsize(900, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        self.zoom = 1.0
        self.tool = "pen"
        self.current_color = "#202124"
        self.shapes: list[Shape] = []
        self.history: list[HistoryCommand] = []
        self.history_index = 0
        self.saved_index = 0
        self.selected: Optional[Shape] = None
        self.selection_box: Optional[int] = None
        self.preview_shape: Optional[Shape] = None
        self.draw_start: Optional[tuple[float, float]] = None
        self.last_point: Optional[tuple[float, float]] = None
        self.move_start: Optional[tuple[float, float]] = None
        self.move_total = (0.0, 0.0)
        self.grid_ids: list[int] = []
        self.canvas_width = 2200
        self.canvas_height = 1500

        self.brush_size = tk.IntVar(value=4)
        self.eraser_size = tk.IntVar(value=24)
        self.outline_width = tk.IntVar(value=3)
        self.font_size = tk.IntVar(value=18)
        self.fill_shapes = tk.BooleanVar(value=False)
        self.grid_visible = tk.BooleanVar(value=False)
        self.status_text = tk.StringVar(value="Pen selected")
        self.zoom_text = tk.StringVar(value="100%")

        self.configure_style()
        self.create_menu()
        self.create_layout()
        self.bind_events()
        self.set_tool("pen")
        self.root.after(100, self.maximize_window)

    def configure_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background="#eef2f7")
        style.configure("Header.TFrame", background="#172033")
        style.configure("Toolbar.TFrame", background="#ffffff")
        style.configure("Canvas.TFrame", background="#cfd8e6")
        style.configure("Status.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#172033", foreground="#ffffff", font=("TkDefaultFont", 17, "bold"))
        style.configure("Subtitle.TLabel", background="#172033", foreground="#b8c4d9", font=("TkDefaultFont", 9))
        style.configure("Credit.TLabel", background="#172033", foreground="#7dd3fc", font=("TkDefaultFont", 9, "bold"))
        style.configure("ToolbarLabel.TLabel", background="#ffffff", foreground="#667085", font=("TkDefaultFont", 9, "bold"))
        style.configure("Status.TLabel", background="#ffffff", foreground="#667085", padding=(12, 7))
        style.configure("Tool.TButton", padding=(9, 7), background="#f8fafc", foreground="#344054")
        style.map("Tool.TButton", background=[("active", "#e0ecff")])
        style.configure("Selected.Tool.TButton", padding=(8, 6), background="#2563eb", foreground="#ffffff")
        style.map("Selected.Tool.TButton", background=[("active", "#1d4ed8")])
        style.configure("Action.TButton", padding=(8, 5), background="#f1f5f9", foreground="#344054")
        style.map("Action.TButton", background=[("active", "#e2e8f0")])
        style.configure("Primary.TButton", padding=(9, 5), background="#2563eb", foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#1d4ed8")])

    def create_menu(self) -> None:
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_canvas)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_image)
        file_menu.add_command(label="Save PNG...", accelerator="Ctrl+S", command=self.save_png)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit)

        edit_menu = tk.Menu(menu, tearoff=False)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Clear", command=self.clear_canvas)

        view_menu = tk.Menu(menu, tearoff=False)
        view_menu.add_command(label="Zoom In", accelerator="+", command=self.zoom_in)
        view_menu.add_command(label="Zoom Out", accelerator="-", command=self.zoom_out)
        view_menu.add_command(label="Reset Zoom", command=self.reset_zoom)
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Toggle Grid", accelerator="G", variable=self.grid_visible, command=self.toggle_grid)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="About", command=self.show_about)

        menu.add_cascade(label="File", menu=file_menu)
        menu.add_cascade(label="Edit", menu=edit_menu)
        menu.add_cascade(label="View", menu=view_menu)
        menu.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menu)

    def create_layout(self) -> None:
        shell = ttk.Frame(self.root, style="App.TFrame")
        shell.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(shell, style="Header.TFrame", padding=(20, 14))
        header.pack(side=tk.TOP, fill=tk.X)
        brand = ttk.Frame(header, style="Header.TFrame")
        brand.pack(side=tk.LEFT)
        ttk.Label(brand, text="◈  Whiteboard", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(brand, text="Sketch, explain, and bring ideas to life", style="Subtitle.TLabel").pack(anchor=tk.W, pady=(2, 0))

        header_actions = ttk.Frame(header, style="Header.TFrame")
        header_actions.pack(side=tk.RIGHT)
        ttk.Label(header_actions, text="Made by byte4day", style="Credit.TLabel").pack(side=tk.LEFT, padx=(0, 16))
        ttk.Button(header_actions, text="↶  Undo", style="Action.TButton", command=self.undo).pack(side=tk.LEFT, padx=3)
        ttk.Button(header_actions, text="↷  Redo", style="Action.TButton", command=self.redo).pack(side=tk.LEFT, padx=3)
        ttk.Button(header_actions, text="Save PNG", style="Primary.TButton", command=self.save_png).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Separator(shell, orient=tk.HORIZONTAL).pack(fill=tk.X)

        toolbar = ttk.Frame(shell, style="Toolbar.TFrame", padding=(16, 10))
        toolbar.pack(side=tk.TOP, fill=tk.X)

        tool_group = ttk.Frame(toolbar, style="Toolbar.TFrame")
        tool_group.pack(side=tk.LEFT)
        ttk.Label(tool_group, text="TOOLS", style="ToolbarLabel.TLabel").pack(side=tk.LEFT, padx=(0, 8))

        self.tool_buttons: dict[str, ttk.Button] = {}
        tools = [
            ("pen", "Pen"),
            ("eraser", "Eraser"),
            ("line", "Line"),
            ("rectangle", "Rectangle"),
            ("ellipse", "Circle"),
            ("arrow", "Arrow"),
            ("text", "Text"),
            ("select", "Select"),
        ]
        for name, label in tools:
            button = ttk.Button(tool_group, text=label, style="Tool.TButton", command=lambda value=name: self.set_tool(value))
            button.pack(side=tk.LEFT, padx=2)
            self.tool_buttons[name] = button

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12)

        settings_group = ttk.Frame(toolbar, style="Toolbar.TFrame")
        settings_group.pack(side=tk.LEFT)
        ttk.Label(settings_group, text="STYLE", style="ToolbarLabel.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(settings_group, text="Brush").pack(side=tk.LEFT)
        ttk.Spinbox(settings_group, from_=1, to=80, textvariable=self.brush_size, width=4).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Label(settings_group, text="Eraser").pack(side=tk.LEFT)
        ttk.Spinbox(settings_group, from_=4, to=160, textvariable=self.eraser_size, width=4).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Label(settings_group, text="Outline").pack(side=tk.LEFT)
        ttk.Spinbox(settings_group, from_=1, to=30, textvariable=self.outline_width, width=4).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Label(settings_group, text="Text").pack(side=tk.LEFT)
        ttk.Spinbox(settings_group, from_=8, to=120, textvariable=self.font_size, width=4).pack(side=tk.LEFT, padx=(4, 8))

        ttk.Checkbutton(settings_group, text="Fill", variable=self.fill_shapes).pack(side=tk.LEFT, padx=(2, 8))
        self.color_preview = tk.Label(settings_group, width=3, height=1, background=self.current_color, relief=tk.SOLID, borderwidth=1)
        self.color_preview.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(settings_group, text="Color", style="Action.TButton", command=self.choose_color).pack(side=tk.LEFT)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12)
        palette = ttk.Frame(toolbar, style="Toolbar.TFrame")
        palette.pack(side=tk.LEFT)
        ttk.Label(palette, text="COLORS", style="ToolbarLabel.TLabel").pack(side=tk.LEFT, padx=(0, 7))
        for color in ("#202124", "#2563eb", "#dc2626", "#16a34a", "#9333ea", "#f59e0b"):
            tk.Button(
                palette,
                background=color,
                activebackground=color,
                highlightbackground="#ffffff",
                highlightthickness=1,
                relief=tk.FLAT,
                width=2,
                height=1,
                cursor="hand2",
                command=lambda value=color: self.set_color(value),
            ).pack(side=tk.LEFT, padx=2)

        view_group = ttk.Frame(toolbar, style="Toolbar.TFrame")
        view_group.pack(side=tk.RIGHT)
        ttk.Button(view_group, text="Clear", style="Action.TButton", command=self.clear_canvas).pack(side=tk.LEFT, padx=2)
        ttk.Button(view_group, text="−", style="Action.TButton", width=3, command=self.zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(view_group, textvariable=self.zoom_text, style="Action.TButton", command=self.reset_zoom).pack(side=tk.LEFT, padx=2)
        ttk.Button(view_group, text="+", style="Action.TButton", width=3, command=self.zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(view_group, text="Grid", variable=self.grid_visible, command=self.toggle_grid).pack(side=tk.LEFT, padx=(8, 0))

        canvas_frame = ttk.Frame(shell, style="Canvas.TFrame", padding=2)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        self.canvas = tk.Canvas(
            canvas_frame,
            background="white",
            highlightthickness=0,
            cursor="crosshair",
            scrollregion=(0, 0, self.canvas_width, self.canvas_height),
        )
        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        status = ttk.Frame(shell, style="Status.TFrame")
        status.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(status, textvariable=self.status_text, style="Status.TLabel", anchor=tk.W).pack(side=tk.LEFT)
        ttk.Label(status, text="Shift: constrain  •  Middle mouse: pan  •  Ctrl + wheel: zoom", style="Status.TLabel", anchor=tk.E).pack(side=tk.RIGHT)

    def bind_events(self) -> None:
        self.canvas.bind("<ButtonPress-1>", self.on_left_press)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_release)
        self.canvas.bind("<ButtonPress-2>", self.pan_start)
        self.canvas.bind("<B2-Motion>", self.pan_move)
        self.canvas.bind("<ButtonPress-3>", self.pan_start)
        self.canvas.bind("<B3-Motion>", self.pan_move)
        self.canvas.bind("<Control-MouseWheel>", self.on_zoom_wheel)
        self.canvas.bind("<Control-Button-4>", lambda _: self.zoom_in())
        self.canvas.bind("<Control-Button-5>", lambda _: self.zoom_out())
        self.canvas.bind("<Configure>", lambda _: self.update_scrollregion())

        bindings = {
            "<Control-n>": self.new_canvas,
            "<Control-o>": self.open_image,
            "<Control-s>": self.save_png,
            "<Control-z>": self.undo,
            "<Control-y>": self.redo,
            "<Delete>": self.delete_selected,
            "<Escape>": self.cancel_action,
            "<Key-p>": lambda: self.set_tool("pen"),
            "<Key-e>": lambda: self.set_tool("eraser"),
            "<Key-r>": lambda: self.set_tool("rectangle"),
            "<Key-c>": lambda: self.set_tool("ellipse"),
            "<Key-l>": lambda: self.set_tool("line"),
            "<Key-a>": lambda: self.set_tool("arrow"),
            "<Key-t>": lambda: self.set_tool("text"),
            "<Key-v>": lambda: self.set_tool("select"),
            "<Key-g>": self.toggle_grid_key,
            "<plus>": self.zoom_in,
            "<equal>": self.zoom_in,
            "<minus>": self.zoom_out,
        }
        for sequence, command in bindings.items():
            self.root.bind(sequence, lambda event, action=command: self.run_binding(action))

    def run_binding(self, action: Callable[[], None]) -> str:
        focused = self.root.focus_get()
        if isinstance(focused, (tk.Entry, ttk.Entry, tk.Text)):
            return ""
        action()
        return "break"

    def maximize_window(self) -> None:
        try:
            self.root.state("zoomed")
        except tk.TclError:
            width = self.root.winfo_screenwidth()
            height = self.root.winfo_screenheight()
            self.root.geometry(f"{int(width * 0.9)}x{int(height * 0.85)}+30+30")

    def set_tool(self, tool: str) -> None:
        self.cancel_action()
        self.tool = tool
        for name, button in self.tool_buttons.items():
            button.configure(style="Selected.Tool.TButton" if name == tool else "Tool.TButton")
        cursors = {"select": "arrow", "text": "xterm"}
        self.canvas.configure(cursor=cursors.get(tool, "crosshair"))
        labels = {
            "pen": "Pen: drag to draw",
            "eraser": "Eraser: drag to erase",
            "line": "Line: drag to draw a line",
            "rectangle": "Rectangle: drag to draw a rectangle",
            "ellipse": "Circle: drag to draw an ellipse",
            "arrow": "Arrow: drag to draw an arrow",
            "text": "Text: click to place text",
            "select": "Select: click an object, then drag to move it",
        }
        self.status_text.set(labels[tool])

    def choose_color(self) -> None:
        result = colorchooser.askcolor(color=self.current_color, parent=self.root, title="Choose Drawing Color")
        if result and result[1]:
            self.set_color(result[1])

    def set_color(self, color: str) -> None:
        self.current_color = color
        self.color_preview.configure(background=color)
        self.status_text.set(f"Color set to {color.upper()}")

    def on_zoom_wheel(self, event: tk.Event) -> str:
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        return "break"

    def screen_to_world(self, event: tk.Event) -> tuple[float, float]:
        return self.canvas.canvasx(event.x) / self.zoom, self.canvas.canvasy(event.y) / self.zoom

    def is_shift_pressed(self, event: tk.Event) -> bool:
        return bool(event.state & 0x0001)

    def constrained_endpoint(self, start: tuple[float, float], end: tuple[float, float], event: tk.Event) -> tuple[float, float]:
        if not self.is_shift_pressed(event):
            return end
        dx, dy = end[0] - start[0], end[1] - start[1]
        if self.tool in {"line", "arrow"}:
            if abs(dx) >= abs(dy):
                return end[0], start[1]
            return start[0], end[1]
        length = max(abs(dx), abs(dy))
        return start[0] + math.copysign(length, dx or 1), start[1] + math.copysign(length, dy or 1)

    def on_left_press(self, event: tk.Event) -> None:
        point = self.screen_to_world(event)
        if self.tool == "text":
            self.place_text(point)
            return
        if self.tool == "select":
            self.select_at(event)
            return
        self.clear_selection()
        self.draw_start = point
        self.last_point = point

        if self.tool in {"pen", "eraser"}:
            color = "white" if self.tool == "eraser" else self.current_color
            width = self.eraser_size.get() if self.tool == "eraser" else self.brush_size.get()
            shape = Shape("freehand", [point[0], point[1], point[0], point[1]], color, width)
            self.preview_shape = shape
            self.create_item(shape)
        else:
            self.preview_shape = Shape(
                self.tool,
                [point[0], point[1], point[0], point[1]],
                self.current_color,
                self.outline_width.get(),
                self.current_color if self.fill_shapes.get() else "",
            )
            self.create_item(self.preview_shape)

    def on_left_drag(self, event: tk.Event) -> None:
        point = self.screen_to_world(event)
        if self.tool == "select" and self.selected and self.move_start:
            dx = point[0] - self.move_start[0]
            dy = point[1] - self.move_start[1]
            if dx or dy:
                self.canvas.move(self.selected.item_id, dx * self.zoom, dy * self.zoom)
                self.move_total = (self.move_total[0] + dx, self.move_total[1] + dy)
                self.move_start = point
                self.update_selection_box()
            return

        if not self.preview_shape or not self.draw_start:
            return

        if self.tool in {"pen", "eraser"}:
            self.preview_shape.coords.extend([point[0], point[1]])
        else:
            end = self.constrained_endpoint(self.draw_start, point, event)
            self.preview_shape.coords = [self.draw_start[0], self.draw_start[1], end[0], end[1]]
        self.update_item(self.preview_shape)

    def on_left_release(self, event: tk.Event) -> None:
        if self.tool == "select":
            if self.selected and (self.move_total[0] or self.move_total[1]):
                shape = self.selected
                dx, dy = self.move_total
                self.shift_model(shape, dx, dy)
                self.add_history(
                    HistoryCommand(
                        undo=lambda target=shape, x=dx, y=dy: self.move_shape(target, -x, -y),
                        redo=lambda target=shape, x=dx, y=dy: self.move_shape(target, x, y),
                    )
                )
                self.update_selection_box()
            self.move_start = None
            self.move_total = (0.0, 0.0)
            return

        if not self.preview_shape:
            return

        shape = self.preview_shape
        self.preview_shape = None
        self.draw_start = None
        self.last_point = None

        if shape.kind == "freehand" and len(shape.coords) < 4:
            self.delete_item(shape)
            return
        if shape.kind != "freehand" and shape.coords[:2] == shape.coords[2:]:
            self.delete_item(shape)
            return

        self.shapes.append(shape)
        self.add_history(
            HistoryCommand(
                undo=lambda target=shape: self.remove_shape(target),
                redo=lambda target=shape: self.restore_shape(target),
            )
        )

    def create_item(self, shape: Shape) -> None:
        coords = [value * self.zoom for value in shape.coords]
        if shape.kind == "freehand":
            shape.item_id = self.canvas.create_line(
                coords,
                fill=shape.color,
                width=max(1, shape.width * self.zoom),
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
                smooth=True,
                tags=("drawing",),
            )
        elif shape.kind == "line":
            shape.item_id = self.canvas.create_line(coords, fill=shape.color, width=max(1, shape.width * self.zoom), tags=("drawing",))
        elif shape.kind == "arrow":
            shape.item_id = self.canvas.create_line(
                coords,
                fill=shape.color,
                width=max(1, shape.width * self.zoom),
                arrow=tk.LAST,
                arrowshape=(12 * self.zoom, 15 * self.zoom, 5 * self.zoom),
                tags=("drawing",),
            )
        elif shape.kind == "rectangle":
            shape.item_id = self.canvas.create_rectangle(
                coords,
                outline=shape.color,
                fill=shape.fill,
                width=max(1, shape.width * self.zoom),
                tags=("drawing",),
            )
        elif shape.kind == "ellipse":
            shape.item_id = self.canvas.create_oval(
                coords,
                outline=shape.color,
                fill=shape.fill,
                width=max(1, shape.width * self.zoom),
                tags=("drawing",),
            )
        elif shape.kind == "text":
            shape.item_id = self.canvas.create_text(
                coords[0],
                coords[1],
                text=shape.text,
                fill=shape.color,
                font=("Arial", max(1, round(shape.font_size * self.zoom))),
                anchor=tk.NW,
                tags=("drawing",),
            )
        elif shape.kind == "image" and shape.image:
            width = max(1, round(shape.image.width * self.zoom))
            height = max(1, round(shape.image.height * self.zoom))
            display = shape.image.resize((width, height), Image.Resampling.LANCZOS)
            image_data = io.BytesIO()
            display.save(image_data, format="PNG")
            shape.photo = tk.PhotoImage(data=base64.b64encode(image_data.getvalue()))
            shape.item_id = self.canvas.create_image(coords[0], coords[1], image=shape.photo, anchor=tk.NW, tags=("drawing",))
        self.update_scrollregion()

    def update_item(self, shape: Shape) -> None:
        if shape.item_id is None:
            return
        if shape.kind == "image":
            self.delete_item(shape)
            self.create_item(shape)
            return
        self.canvas.coords(shape.item_id, *[value * self.zoom for value in shape.coords])

    def delete_item(self, shape: Shape) -> None:
        if shape.item_id is not None:
            self.canvas.delete(shape.item_id)
        shape.item_id = None
        shape.photo = None

    def remove_shape(self, shape: Shape) -> None:
        self.delete_item(shape)
        if shape in self.shapes:
            self.shapes.remove(shape)
        if self.selected is shape:
            self.clear_selection()

    def restore_shape(self, shape: Shape) -> None:
        if shape not in self.shapes:
            self.shapes.append(shape)
        if shape.item_id is None:
            self.create_item(shape)

    def shift_model(self, shape: Shape, dx: float, dy: float) -> None:
        for index in range(0, len(shape.coords), 2):
            shape.coords[index] += dx
            shape.coords[index + 1] += dy

    def move_shape(self, shape: Shape, dx: float, dy: float) -> None:
        self.shift_model(shape, dx, dy)
        if shape.kind == "image":
            self.delete_item(shape)
            self.create_item(shape)
        elif shape.item_id is not None:
            self.canvas.move(shape.item_id, dx * self.zoom, dy * self.zoom)
        self.update_selection_box()

    def place_text(self, point: tuple[float, float]) -> None:
        text = simpledialog.askstring("Add Text", "Enter text:", parent=self.root)
        if text is None or not text.strip():
            return
        shape = Shape("text", [point[0], point[1]], self.current_color, 1, text=text, font_size=self.font_size.get())
        self.create_item(shape)
        self.shapes.append(shape)
        self.add_history(
            HistoryCommand(
                undo=lambda target=shape: self.remove_shape(target),
                redo=lambda target=shape: self.restore_shape(target),
            )
        )

    def select_at(self, event: tk.Event) -> None:
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        candidates = self.canvas.find_overlapping(x - 5, y - 5, x + 5, y + 5)
        found: Optional[Shape] = None
        for item_id in reversed(candidates):
            for shape in reversed(self.shapes):
                if shape.item_id == item_id:
                    found = shape
                    break
            if found:
                break

        if found:
            self.selected = found
            self.move_start = self.screen_to_world(event)
            self.move_total = (0.0, 0.0)
            self.update_selection_box()
            self.status_text.set("Object selected. Drag to move, Delete to remove.")
        else:
            self.clear_selection()
            self.status_text.set("No object selected.")

    def update_selection_box(self) -> None:
        if self.selection_box is not None:
            self.canvas.delete(self.selection_box)
            self.selection_box = None
        if not self.selected or self.selected.item_id is None:
            return
        bbox = self.canvas.bbox(self.selected.item_id)
        if bbox:
            pad = 5
            self.selection_box = self.canvas.create_rectangle(
                bbox[0] - pad,
                bbox[1] - pad,
                bbox[2] + pad,
                bbox[3] + pad,
                outline="#2563eb",
                width=2,
                dash=(4, 3),
                tags=("selection",),
            )

    def clear_selection(self) -> None:
        if self.selection_box is not None:
            self.canvas.delete(self.selection_box)
            self.selection_box = None
        self.selected = None
        self.move_start = None

    def delete_selected(self) -> None:
        if not self.selected:
            return
        shape = self.selected
        self.remove_shape(shape)
        self.add_history(
            HistoryCommand(
                undo=lambda target=shape: self.restore_shape(target),
                redo=lambda target=shape: self.remove_shape(target),
            )
        )

    def add_history(self, command: HistoryCommand) -> None:
        del self.history[self.history_index:]
        self.history.append(command)
        self.history_index += 1
        self.update_title()

    def undo(self) -> None:
        if self.history_index == 0:
            self.status_text.set("Nothing to undo.")
            return
        self.clear_selection()
        self.history_index -= 1
        self.history[self.history_index].undo()
        self.update_title()
        self.status_text.set("Undo complete.")

    def redo(self) -> None:
        if self.history_index >= len(self.history):
            self.status_text.set("Nothing to redo.")
            return
        self.clear_selection()
        self.history[self.history_index].redo()
        self.history_index += 1
        self.update_title()
        self.status_text.set("Redo complete.")

    def clear_canvas(self) -> None:
        if not self.shapes:
            return
        if not messagebox.askyesno("Clear Canvas", "Clear all objects from the canvas?", parent=self.root):
            return
        old_shapes = self.shapes.copy()
        self.clear_selection()
        for shape in old_shapes:
            self.delete_item(shape)
        self.shapes.clear()
        self.add_history(
            HistoryCommand(
                undo=lambda targets=old_shapes: self.restore_many(targets),
                redo=lambda targets=old_shapes: self.remove_many(targets),
            )
        )
        self.status_text.set("Canvas cleared.")

    def restore_many(self, shapes: list[Shape]) -> None:
        for shape in shapes:
            self.restore_shape(shape)

    def remove_many(self, shapes: list[Shape]) -> None:
        for shape in shapes:
            self.remove_shape(shape)

    def cancel_action(self) -> None:
        if self.preview_shape:
            self.delete_item(self.preview_shape)
        self.preview_shape = None
        self.draw_start = None
        self.last_point = None
        self.move_start = None
        self.move_total = (0.0, 0.0)
        self.clear_selection()

    def pan_start(self, event: tk.Event) -> None:
        self.canvas.scan_mark(event.x, event.y)

    def pan_move(self, event: tk.Event) -> None:
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def zoom_in(self) -> None:
        self.set_zoom(min(4.0, self.zoom * 1.2))

    def zoom_out(self) -> None:
        self.set_zoom(max(0.2, self.zoom / 1.2))

    def reset_zoom(self) -> None:
        self.set_zoom(1.0)

    def set_zoom(self, value: float) -> None:
        if abs(value - self.zoom) < 0.0001:
            return
        factor = value / self.zoom
        self.clear_selection()
        self.canvas.scale("drawing", 0, 0, factor, factor)
        self.zoom = value
        self.zoom_text.set(f"{round(self.zoom * 100)}%")
        for shape in self.shapes:
            if shape.kind == "image":
                self.delete_item(shape)
                self.create_item(shape)
            elif shape.item_id is not None:
                width = shape.width * self.zoom
                if shape.kind == "freehand":
                    self.canvas.itemconfigure(shape.item_id, width=max(1, width))
                elif shape.kind in {"line", "arrow", "rectangle", "ellipse"}:
                    self.canvas.itemconfigure(shape.item_id, width=max(1, width))
                elif shape.kind == "text":
                    self.canvas.itemconfigure(shape.item_id, font=("Arial", max(1, round(shape.font_size * self.zoom))))
        self.draw_grid()
        self.update_scrollregion()
        self.status_text.set(f"Zoom: {round(self.zoom * 100)}%")

    def update_scrollregion(self) -> None:
        required_width = max(self.canvas_width * self.zoom, self.canvas.winfo_width() + 200)
        required_height = max(self.canvas_height * self.zoom, self.canvas.winfo_height() + 200)
        self.canvas.configure(scrollregion=(0, 0, required_width, required_height))

    def toggle_grid_key(self) -> None:
        self.grid_visible.set(not self.grid_visible.get())
        self.toggle_grid()

    def toggle_grid(self) -> None:
        self.draw_grid()
        self.status_text.set("Grid enabled." if self.grid_visible.get() else "Grid disabled.")

    def draw_grid(self) -> None:
        for item_id in self.grid_ids:
            self.canvas.delete(item_id)
        self.grid_ids.clear()
        if not self.grid_visible.get():
            return
        spacing = max(12, round(25 * self.zoom))
        scroll = self.canvas.cget("scrollregion").split()
        width = int(float(scroll[2]))
        height = int(float(scroll[3]))
        for x in range(0, width + spacing, spacing):
            self.grid_ids.append(self.canvas.create_line(x, 0, x, height, fill="#edf0f3", width=1, tags=("grid",)))
        for y in range(0, height + spacing, spacing):
            self.grid_ids.append(self.canvas.create_line(0, y, width, y, fill="#edf0f3", width=1, tags=("grid",)))
        self.canvas.tag_lower("grid")

    def new_canvas(self) -> None:
        if self.is_modified() and not messagebox.askyesno("New Canvas", "Discard unsaved changes and create a new canvas?", parent=self.root):
            return
        self.reset_document()
        self.status_text.set("New canvas created.")

    def reset_document(self) -> None:
        self.cancel_action()
        self.canvas.delete("drawing")
        self.shapes.clear()
        self.history.clear()
        self.history_index = 0
        self.saved_index = 0
        self.zoom = 1.0
        self.zoom_text.set("100%")
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self.draw_grid()
        self.update_title()

    def open_image(self) -> None:
        if self.is_modified() and not messagebox.askyesno("Open Image", "Discard unsaved changes and open an image?", parent=self.root):
            return
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Open Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("PNG files", "*.png"), ("JPEG files", "*.jpg *.jpeg")],
        )
        if not path:
            return
        try:
            with Image.open(path) as source:
                image = source.convert("RGBA").copy()
            self.reset_document()
            self.canvas_width = max(2200, image.width + 100)
            self.canvas_height = max(1500, image.height + 100)
            shape = Shape("image", [20, 20], "#000000", 1, image=image)
            self.create_item(shape)
            self.shapes.append(shape)
            self.history.clear()
            self.history_index = 0
            self.saved_index = 0
            self.update_title()
            self.status_text.set(f"Opened {Path(path).name}")
        except (OSError, ValueError) as error:
            messagebox.showerror("Open Failed", f"Unable to open this image.\n\n{error}", parent=self.root)

    def save_png(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Whiteboard as PNG",
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
        )
        if not path:
            return
        try:
            image = self.render_image()
            image.save(path, "PNG")
            self.saved_index = self.history_index
            self.update_title()
            self.status_text.set(f"Saved PNG: {Path(path).name}")
        except (OSError, ValueError) as error:
            messagebox.showerror("Save Failed", f"Unable to save the image.\n\n{error}", parent=self.root)

    def render_image(self) -> Image.Image:
        max_x = self.canvas.winfo_width() / self.zoom
        max_y = self.canvas.winfo_height() / self.zoom
        for shape in self.shapes:
            if shape.kind == "image" and shape.image:
                max_x = max(max_x, shape.coords[0] + shape.image.width + 20)
                max_y = max(max_y, shape.coords[1] + shape.image.height + 20)
            elif shape.coords:
                max_x = max(max_x, max(shape.coords[::2]) + 30)
                max_y = max(max_y, max(shape.coords[1::2]) + 30)

        width = max(1, int(max_x))
        height = max(1, int(max_y))
        result = Image.new("RGBA", (width, height), "white")
        draw = ImageDraw.Draw(result)

        for shape in self.shapes:
            coords = [round(value) for value in shape.coords]
            if shape.kind == "freehand":
                if len(coords) >= 4:
                    draw.line(coords, fill=shape.color, width=max(1, shape.width), joint="curve")
            elif shape.kind == "line":
                draw.line(coords, fill=shape.color, width=max(1, shape.width))
            elif shape.kind == "rectangle":
                draw.rectangle(coords, outline=shape.color, fill=shape.fill or None, width=max(1, shape.width))
            elif shape.kind == "ellipse":
                draw.ellipse(coords, outline=shape.color, fill=shape.fill or None, width=max(1, shape.width))
            elif shape.kind == "arrow":
                self.draw_arrow(draw, coords, shape.color, shape.width)
            elif shape.kind == "text":
                font = self.get_pil_font(shape.font_size)
                draw.text((coords[0], coords[1]), shape.text, fill=shape.color, font=font)
            elif shape.kind == "image" and shape.image:
                result.alpha_composite(shape.image, (coords[0], coords[1]))
        return result.convert("RGB")

    def draw_arrow(self, draw: ImageDraw.ImageDraw, coords: list[int], color: str, width: int) -> None:
        x1, y1, x2, y2 = coords
        draw.line((x1, y1, x2, y2), fill=color, width=max(1, width))
        angle = math.atan2(y2 - y1, x2 - x1)
        size = max(10, width * 4)
        left = (x2 - size * math.cos(angle - math.pi / 6), y2 - size * math.sin(angle - math.pi / 6))
        right = (x2 - size * math.cos(angle + math.pi / 6), y2 - size * math.sin(angle + math.pi / 6))
        draw.polygon([(x2, y2), left, right], fill=color)

    def get_pil_font(self, size: int) -> ImageFont.ImageFont:
        for font_name in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf"):
            try:
                return ImageFont.truetype(font_name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def is_modified(self) -> bool:
        return self.history_index != self.saved_index

    def update_title(self) -> None:
        prefix = "• " if self.is_modified() else ""
        self.root.title(f"{prefix}Whiteboard — Made by byte4day")

    def on_exit(self) -> None:
        if self.is_modified():
            answer = messagebox.askyesnocancel("Exit Whiteboard", "Save changes before exiting?", parent=self.root)
            if answer is None:
                return
            if answer:
                previous = self.saved_index
                self.save_png()
                if self.saved_index != self.history_index and previous != self.history_index:
                    return
        self.root.destroy()

    def show_about(self) -> None:
        messagebox.showinfo(
            "About Whiteboard",
            "Whiteboard\nMade by byte4day\n\nA modern Tkinter drawing application.\n\n"
            "Keyboard shortcuts:\nCtrl+N New   Ctrl+O Open   Ctrl+S Save\n"
            "Ctrl+Z Undo   Ctrl+Y Redo\nP Pen   E Eraser   R Rectangle   C Circle\n"
            "L Line   A Arrow   T Text   V Select\nG Grid   + / - Zoom",
            parent=self.root,
        )

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    WhiteboardApp().run()
