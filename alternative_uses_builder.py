"""
Alternative Uses Builder

A small Tkinter behavioral experiment where participants arrange simple shapes
to depict as many uses for a brick as they can imagine.

Run:
    python alternative_uses_builder.py
"""

from __future__ import annotations

import csv
import json
import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import messagebox, ttk


APP_TITLE = "Alternative Uses Builder"
DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass
class ExperimentConfig:
    """Configuration switches kept in one place for later experiment variants."""

    idea_limit: int | None = None
    countdown_seconds: int | None = None
    stress_condition: bool = False
    warning_sounds_enabled: bool = False
    ai_hints_enabled: bool = False
    eeg_markers_enabled: bool = False


class ExperimentHooks:
    """No-op extension points for timers, stressors, hints, and EEG markers."""

    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config

    def on_experiment_start(self, participant_id: str) -> None:
        pass

    def on_idea_start(self, idea_number: int) -> None:
        pass

    def on_submit(self, record: dict[str, Any]) -> None:
        pass

    def send_eeg_marker(self, marker: str) -> None:
        if self.config.eeg_markers_enabled:
            # Add serial/parallel-port/LSL marker code here later.
            print(f"EEG marker: {marker}")


@dataclass
class ShapeItem:
    """A draggable, resizable, rotatable shape on the workspace."""

    shape_id: int
    kind: str
    cx: float
    cy: float
    width: float
    height: float
    angle: float = 0.0
    color: str = "#4f7cff"
    canvas_id: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "shape_id": self.shape_id,
            "kind": self.kind,
            "cx": round(self.cx, 2),
            "cy": round(self.cy, 2),
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "angle": round(self.angle, 2),
        }


@dataclass
class IdeaState:
    """Per-idea behavioral data accumulated until the participant submits."""

    idea_number: int
    started_at_wall: datetime = field(default_factory=datetime.now)
    started_at_perf: float = field(default_factory=time.perf_counter)
    mouse_positions: list[dict[str, float]] = field(default_factory=list)
    total_mouse_distance: float = 0.0
    move_count: int = 0
    resize_count: int = 0
    rotation_count: int = 0


class DataLogger:
    """Append one CSV row per submitted idea."""

    headers = [
        "participant_id",
        "first_name",
        "last_name",
        "tamu_email",
        "phone_number",
        "idea_number",
        "description",
        "time_spent_seconds",
        "number_of_shapes_used",
        "number_of_moves",
        "mouse_positions_json",
        "total_mouse_distance_px",
        "rotation_count",
        "resize_count",
        "idea_started_at",
        "submitted_at",
        "shape_layout_json",
    ]

    def __init__(self, participant_info: dict[str, str]) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        participant_id = participant_info["participant_id"]
        safe_id = "".join(ch for ch in participant_id if ch.isalnum() or ch in "-_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = DATA_DIR / f"alternative_uses_{safe_id}_{timestamp}.csv"

        with self.path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.headers)
            writer.writeheader()

    def append(self, row: dict[str, Any]) -> None:
        with self.path.open("a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.headers)
            writer.writerow(row)


class AlternativeUsesBuilder(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1120x760")
        self.minsize(980, 680)

        self.config_model = ExperimentConfig()
        self.hooks = ExperimentHooks(self.config_model)
        self.data_logger: DataLogger | None = None
        self.participant_id = ""
        self.participant_info: dict[str, str] = {}
        self.participant_fields: dict[str, tk.StringVar] = {}
        self.idea_number = 0
        self.total_ideas = 0
        self.current_state: IdeaState | None = None
        self.in_practice_round = False

        self.canvas: tk.Canvas | None = None
        self.description_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.submit_button: ttk.Button | None = None

        self.shapes: dict[int, ShapeItem] = {}
        self.next_shape_id = 1
        self.selected_shape_id: int | None = None
        self.selection_box: int | None = None
        self.resize_handle: int | None = None
        self.rotate_handle: int | None = None
        self.palette_ghost_id: int | None = None

        self.active_action: str | None = None
        self.active_palette_kind: str | None = None
        self.drag_start_x = 0.0
        self.drag_start_y = 0.0
        self.action_start_shape: ShapeItem | None = None
        self.last_mouse_point: tuple[float, float] | None = None

        self.palette_width = 175
        self.workspace_bounds = (205, 25, 1070, 555)

        self.show_welcome_screen()

    def clear_screen(self) -> None:
        for child in self.winfo_children():
            child.destroy()

    def show_welcome_screen(self) -> None:
        self.clear_screen()
        frame = ttk.Frame(self, padding=32)
        frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(frame, text=APP_TITLE, font=("Helvetica", 28, "bold"))
        title.pack(pady=(34, 12))

        prompt = ttk.Label(
            frame,
            text="A shape-building task for creative uses of a brick.",
            font=("Helvetica", 15),
        )
        prompt.pack(pady=(0, 24))

        form = ttk.Frame(frame)
        form.pack(pady=8)

        field_specs = [
            ("participant_id", "ID", datetime.now().strftime("P%Y%m%d%H%M%S")),
            ("first_name", "First Name", ""),
            ("last_name", "Last Name", ""),
            ("tamu_email", "TAMU Email (preferred)", ""),
            ("phone_number", "Phone Number", ""),
        ]
        self.participant_fields = {}
        first_entry: ttk.Entry | None = None
        for row_index, (key, label, default) in enumerate(field_specs):
            ttk.Label(form, text=label).grid(
                row=row_index, column=0, sticky=tk.E, padx=(0, 12), pady=7
            )
            variable = tk.StringVar(value=default)
            self.participant_fields[key] = variable
            entry = ttk.Entry(form, textvariable=variable, width=36)
            entry.grid(row=row_index, column=1, sticky=tk.W, pady=7)
            if first_entry is None:
                first_entry = entry

        ttk.Label(
            form,
            text="Phone format: 979-743-2299",
            font=("Helvetica", 10),
        ).grid(row=5, column=1, sticky=tk.W, pady=(0, 6))

        if first_entry is not None:
            first_entry.focus_set()

        ttk.Button(frame, text="Start", command=self.start_experiment).pack(pady=28)

    def start_experiment(self) -> None:
        participant_info = self.collect_participant_info()
        if participant_info is None:
            return

        self.participant_info = participant_info
        self.participant_id = participant_info["participant_id"]
        self.data_logger = DataLogger(participant_info)
        self.hooks.on_experiment_start(self.participant_id)
        self.show_instructions_screen()

    def collect_participant_info(self) -> dict[str, str] | None:
        labels = {
            "participant_id": "ID",
            "first_name": "First Name",
            "last_name": "Last Name",
            "phone_number": "Phone Number",
        }
        info = {
            key: variable.get().strip()
            for key, variable in self.participant_fields.items()
        }
        missing = [label for key, label in labels.items() if not info.get(key)]
        if missing:
            messagebox.showinfo(
                "Missing information",
                "Please complete: " + ", ".join(missing),
            )
            return None

        email = info["tamu_email"].lower()
        if email and not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", email):
            messagebox.showinfo(
                "Check email",
                "Please enter a valid email address or leave the field blank.",
            )
            return None

        phone_number = self.normalize_phone_number(info["phone_number"])
        if phone_number is None:
            messagebox.showinfo(
                "Check phone number",
                "Please enter the phone number in this format: 979-743-2299.",
            )
            return None

        info["tamu_email"] = email
        info["phone_number"] = phone_number
        self.participant_fields["phone_number"].set(phone_number)
        return info

    def normalize_phone_number(self, value: str) -> str | None:
        if re.fullmatch(r"\d{3}-\d{3}-\d{4}", value):
            return value

        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) == 10:
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"

        return None

    def show_instructions_screen(self) -> None:
        self.clear_screen()
        frame = ttk.Frame(self, padding=42)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Instructions", font=("Helvetica", 26, "bold")).pack(
            anchor=tk.W, pady=(40, 20)
        )

        instruction_text = (
            "Using only the shapes on the screen, create as many different uses "
            "for a brick as possible.\n\n"
            "Drag shapes from the side panel into the workspace. Move shapes by "
            "dragging them. Select a shape to reveal resize and rotation handles.\n\n"
            "After each idea, type a short description such as \"phone stand,\" "
            "\"doorstop,\" \"hammer,\" or \"small house,\" then press Submit Idea. "
            "The workspace will reset for the next idea.\n\n"
            "You will complete one short practice round first. Practice data is "
            "not saved to the experiment CSV."
        )
        ttk.Label(
            frame,
            text=instruction_text,
            font=("Helvetica", 15),
            wraplength=840,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 32))

        button_row = ttk.Frame(frame)
        button_row.pack(anchor=tk.W)
        ttk.Button(button_row, text="Start Practice", command=self.start_practice_round).pack(
            side=tk.LEFT
        )

    def start_practice_round(self) -> None:
        self.in_practice_round = True
        self.show_task_screen(practice=True)

    def start_actual_experiment(self) -> None:
        self.in_practice_round = False
        self.show_task_screen(practice=False)

    def show_task_screen(self, practice: bool = False) -> None:
        self.clear_screen()
        self.in_practice_round = practice
        if not practice:
            self.idea_number = 0
            self.total_ideas = 0

        outer = ttk.Frame(self, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)

        top_row = ttk.Frame(outer)
        top_row.pack(fill=tk.X, pady=(0, 10))
        screen_title = "Practice Round" if practice else APP_TITLE
        ttk.Label(top_row, text=screen_title, font=("Helvetica", 18, "bold")).pack(
            side=tk.LEFT
        )
        end_text = "Skip Practice" if practice else "End Experiment"
        end_command = self.finish_practice_round if practice else self.finish_experiment
        ttk.Button(top_row, text=end_text, command=end_command).pack(
            side=tk.RIGHT
        )

        self.canvas = tk.Canvas(
            outer,
            width=1080,
            height=580,
            background="#f6f7fb",
            highlightthickness=1,
            highlightbackground="#ccd2dd",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Motion>", self.on_mouse_motion)
        self.canvas.bind("<Configure>", self.redraw_canvas)

        bottom = ttk.Frame(outer)
        bottom.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(bottom, text="Idea description").pack(side=tk.LEFT)
        description_entry = ttk.Entry(bottom, textvariable=self.description_var)
        description_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        description_entry.bind("<Return>", lambda _event: self.submit_idea())
        submit_text = "Finish Practice" if practice else "Submit Idea"
        self.submit_button = ttk.Button(
            bottom, text=submit_text, command=self.submit_idea
        )
        self.submit_button.pack(side=tk.LEFT)

        ttk.Label(outer, textvariable=self.status_var).pack(anchor=tk.W, pady=(8, 0))

        self.start_next_idea()

    def start_next_idea(self) -> None:
        if self.in_practice_round:
            self.current_state = IdeaState(idea_number=0)
            self.description_var.set("")
            self.clear_workspace()
            self.status_var.set(
                "Practice: try dragging, moving, resizing, and rotating. "
                "This round will not be saved."
            )
            self.redraw_canvas()
            return

        self.idea_number += 1
        self.current_state = IdeaState(idea_number=self.idea_number)
        self.hooks.on_idea_start(self.idea_number)
        self.hooks.send_eeg_marker(f"idea_{self.idea_number}_start")
        self.description_var.set("")
        self.clear_workspace()
        self.status_var.set(f"Idea {self.idea_number}: build a new use for a brick.")
        self.redraw_canvas()

    def clear_workspace(self) -> None:
        self.shapes.clear()
        self.selected_shape_id = None
        self.selection_box = None
        self.resize_handle = None
        self.rotate_handle = None
        self.active_action = None
        self.active_palette_kind = None
        self.last_mouse_point = None

    def redraw_canvas(self, _event: tk.Event | None = None) -> None:
        if self.canvas is None:
            return
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1080)
        height = max(canvas.winfo_height(), 580)
        self.workspace_bounds = (
            self.palette_width + 30,
            25,
            width - 25,
            height - 25,
        )

        self.draw_palette(canvas, height)
        self.draw_workspace(canvas)

        for shape in self.shapes.values():
            self.draw_shape(shape)
        self.draw_selection()

    def draw_palette(self, canvas: tk.Canvas, height: int) -> None:
        canvas.create_rectangle(
            0,
            0,
            self.palette_width,
            height,
            fill="#e9edf5",
            outline="#c6cede",
            tags=("palette_panel",),
        )
        canvas.create_text(
            20,
            28,
            text="Shapes",
            anchor=tk.W,
            font=("Helvetica", 15, "bold"),
            fill="#1f2a44",
        )
        canvas.create_text(
            20,
            55,
            text="Drag into workspace",
            anchor=tk.W,
            font=("Helvetica", 10),
            fill="#59657a",
        )

        palette_shapes = [
            ("square", 52, 115, 55, 55, "#4f7cff"),
            ("rectangle", 118, 115, 76, 42, "#f59e0b"),
            ("circle", 52, 205, 58, 58, "#10b981"),
            ("triangle", 118, 205, 70, 58, "#ef4444"),
        ]
        for kind, cx, cy, w, h, color in palette_shapes:
            tags = ("palette_shape", f"palette:{kind}")
            self.create_shape_graphic(canvas, kind, cx, cy, w, h, 0, color, tags)
            canvas.create_text(
                cx,
                cy + 47,
                text=kind.title(),
                anchor=tk.N,
                font=("Helvetica", 9),
                fill="#3a4556",
            )

    def draw_workspace(self, canvas: tk.Canvas) -> None:
        x1, y1, x2, y2 = self.workspace_bounds
        canvas.create_rectangle(x1, y1, x2, y2, fill="white", outline="#bac3d2", width=2)
        canvas.create_text(
            (x1 + x2) / 2,
            y1 + 22,
            text="Workspace",
            fill="#9aa4b7",
            font=("Helvetica", 12),
        )

    def draw_shape(self, shape: ShapeItem) -> None:
        if self.canvas is None:
            return
        shape.canvas_id = self.create_shape_graphic(
            self.canvas,
            shape.kind,
            shape.cx,
            shape.cy,
            shape.width,
            shape.height,
            shape.angle,
            shape.color,
            ("shape", f"shape:{shape.shape_id}"),
        )

    def create_shape_graphic(
        self,
        canvas: tk.Canvas,
        kind: str,
        cx: float,
        cy: float,
        width: float,
        height: float,
        angle: float,
        color: str,
        tags: tuple[str, ...],
    ) -> int:
        if kind == "circle":
            return canvas.create_oval(
                cx - width / 2,
                cy - height / 2,
                cx + width / 2,
                cy + height / 2,
                fill=color,
                outline="#172033",
                width=2,
                tags=tags,
            )

        if kind == "triangle":
            points = [(0, -height / 2), (-width / 2, height / 2), (width / 2, height / 2)]
        else:
            points = [
                (-width / 2, -height / 2),
                (width / 2, -height / 2),
                (width / 2, height / 2),
                (-width / 2, height / 2),
            ]

        rotated = self.rotated_points(points, cx, cy, angle)
        flat = [coord for point in rotated for coord in point]
        return canvas.create_polygon(
            flat,
            fill=color,
            outline="#172033",
            width=2,
            tags=tags,
        )

    def rotated_points(
        self, points: list[tuple[float, float]], cx: float, cy: float, angle: float
    ) -> list[tuple[float, float]]:
        radians = math.radians(angle)
        cos_a = math.cos(radians)
        sin_a = math.sin(radians)
        return [
            (cx + px * cos_a - py * sin_a, cy + px * sin_a + py * cos_a)
            for px, py in points
        ]

    def draw_selection(self) -> None:
        if self.canvas is None or self.selected_shape_id is None:
            return
        shape = self.shapes.get(self.selected_shape_id)
        if shape is None:
            return

        pad = 10
        x1 = shape.cx - shape.width / 2 - pad
        y1 = shape.cy - shape.height / 2 - pad
        x2 = shape.cx + shape.width / 2 + pad
        y2 = shape.cy + shape.height / 2 + pad

        self.selection_box = self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline="#1d4ed8",
            dash=(5, 3),
            width=2,
            tags=("selection",),
        )
        self.resize_handle = self.canvas.create_rectangle(
            x2 - 7,
            y2 - 7,
            x2 + 7,
            y2 + 7,
            fill="#1d4ed8",
            outline="white",
            tags=("resize_handle",),
        )
        self.rotate_handle = self.canvas.create_oval(
            shape.cx - 8,
            y1 - 36,
            shape.cx + 8,
            y1 - 20,
            fill="#0f766e",
            outline="white",
            tags=("rotate_handle",),
        )
        self.canvas.create_line(
            shape.cx,
            y1,
            shape.cx,
            y1 - 20,
            fill="#0f766e",
            width=2,
            tags=("selection",),
        )

    def on_canvas_press(self, event: tk.Event) -> None:
        if self.canvas is None:
            return
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.active_action = None
        self.action_start_shape = None

        clicked_id = self.find_canvas_item(event.x, event.y)
        clicked_tags = self.canvas.gettags(clicked_id) if clicked_id else ()

        if "resize_handle" in clicked_tags and self.selected_shape_id is not None:
            self.active_action = "resize"
            self.action_start_shape = self.copy_shape(self.shapes[self.selected_shape_id])
            return

        if "rotate_handle" in clicked_tags and self.selected_shape_id is not None:
            self.active_action = "rotate"
            self.action_start_shape = self.copy_shape(self.shapes[self.selected_shape_id])
            return

        palette_kind = self.palette_kind_from_tags(clicked_tags)
        if palette_kind:
            self.active_action = "palette"
            self.active_palette_kind = palette_kind
            self.draw_palette_ghost(event.x, event.y)
            return

        shape_id = self.shape_id_from_tags(clicked_tags)
        if shape_id is not None:
            self.selected_shape_id = shape_id
            self.active_action = "move"
            self.action_start_shape = self.copy_shape(self.shapes[shape_id])
            self.redraw_canvas()
            return

        if self.in_workspace(event.x, event.y):
            self.selected_shape_id = None
            self.redraw_canvas()

    def on_canvas_drag(self, event: tk.Event) -> None:
        if self.canvas is None or self.active_action is None:
            return

        if self.active_action == "palette":
            self.draw_palette_ghost(event.x, event.y)
            return

        if self.selected_shape_id is None:
            return
        shape = self.shapes.get(self.selected_shape_id)
        if shape is None or self.action_start_shape is None:
            return

        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        if self.active_action == "move":
            shape.cx = self.action_start_shape.cx + dx
            shape.cy = self.action_start_shape.cy + dy
            self.keep_shape_in_workspace(shape)
        elif self.active_action == "resize":
            new_width = max(20, self.action_start_shape.width + dx * 2)
            new_height = max(20, self.action_start_shape.height + dy * 2)
            if shape.kind == "square":
                size = max(new_width, new_height)
                new_width = size
                new_height = size
            elif shape.kind == "circle":
                diameter = max(new_width, new_height)
                new_width = diameter
                new_height = diameter
            shape.width = min(new_width, 320)
            shape.height = min(new_height, 320)
            self.keep_shape_in_workspace(shape)
        elif self.active_action == "rotate":
            start_angle = math.atan2(
                self.drag_start_y - self.action_start_shape.cy,
                self.drag_start_x - self.action_start_shape.cx,
            )
            current_angle = math.atan2(event.y - shape.cy, event.x - shape.cx)
            shape.angle = self.action_start_shape.angle + math.degrees(
                current_angle - start_angle
            )

        self.redraw_canvas()

    def on_canvas_release(self, event: tk.Event) -> None:
        if self.canvas is None:
            return

        if self.active_action == "palette" and self.active_palette_kind:
            if self.in_workspace(event.x, event.y):
                self.add_shape(self.active_palette_kind, event.x, event.y)
            self.delete_palette_ghost()
        elif (
            self.active_action == "move"
            and self.current_state is not None
            and self.action_start_shape is not None
            and self.selected_shape_id is not None
        ):
            shape = self.shapes[self.selected_shape_id]
            moved_distance = self.distance(
                shape.cx,
                shape.cy,
                self.action_start_shape.cx,
                self.action_start_shape.cy,
            )
            if moved_distance > 3:
                self.current_state.move_count += 1
        elif (
            self.active_action == "resize"
            and self.current_state is not None
            and self.action_start_shape is not None
            and self.selected_shape_id is not None
        ):
            shape = self.shapes[self.selected_shape_id]
            if (
                abs(shape.width - self.action_start_shape.width) > 3
                or abs(shape.height - self.action_start_shape.height) > 3
            ):
                self.current_state.resize_count += 1
        elif (
            self.active_action == "rotate"
            and self.current_state is not None
            and self.action_start_shape is not None
            and self.selected_shape_id is not None
        ):
            shape = self.shapes[self.selected_shape_id]
            if abs(shape.angle - self.action_start_shape.angle) > 2:
                self.current_state.rotation_count += 1

        self.active_action = None
        self.active_palette_kind = None
        self.action_start_shape = None
        self.palette_ghost_id = None
        self.redraw_canvas()

    def on_mouse_motion(self, event: tk.Event) -> None:
        if self.current_state is None:
            return
        now = round(time.perf_counter() - self.current_state.started_at_perf, 4)
        point = {"t": now, "x": float(event.x), "y": float(event.y)}
        self.current_state.mouse_positions.append(point)

        if self.last_mouse_point is not None:
            last_x, last_y = self.last_mouse_point
            self.current_state.total_mouse_distance += self.distance(
                event.x, event.y, last_x, last_y
            )
        self.last_mouse_point = (float(event.x), float(event.y))

    def add_shape(self, kind: str, x: float, y: float) -> None:
        color_map = {
            "square": "#4f7cff",
            "rectangle": "#f59e0b",
            "circle": "#10b981",
            "triangle": "#ef4444",
        }
        default_size = {
            "square": (62, 62),
            "rectangle": (95, 52),
            "circle": (66, 66),
            "triangle": (78, 70),
        }
        width, height = default_size[kind]
        shape = ShapeItem(
            shape_id=self.next_shape_id,
            kind=kind,
            cx=x,
            cy=y,
            width=width,
            height=height,
            color=color_map[kind],
        )
        self.next_shape_id += 1
        self.keep_shape_in_workspace(shape)
        self.shapes[shape.shape_id] = shape
        self.selected_shape_id = shape.shape_id

    def draw_palette_ghost(self, x: float, y: float) -> None:
        if self.canvas is None or self.active_palette_kind is None:
            return
        self.delete_palette_ghost()
        self.palette_ghost_id = self.create_shape_graphic(
            self.canvas,
            self.active_palette_kind,
            x,
            y,
            64,
            64,
            0,
            "#8aa4ff",
            ("palette_ghost",),
        )

    def delete_palette_ghost(self) -> None:
        if self.canvas is not None and self.palette_ghost_id is not None:
            self.canvas.delete(self.palette_ghost_id)
        self.palette_ghost_id = None

    def keep_shape_in_workspace(self, shape: ShapeItem) -> None:
        x1, y1, x2, y2 = self.workspace_bounds
        half_w = shape.width / 2
        half_h = shape.height / 2
        shape.cx = min(max(shape.cx, x1 + half_w), x2 - half_w)
        shape.cy = min(max(shape.cy, y1 + half_h), y2 - half_h)

    def submit_idea(self) -> None:
        if self.current_state is None:
            return

        description = self.description_var.get().strip()
        if not description:
            messagebox.showinfo(
                "Description needed",
                "Please type a short description before submitting this idea.",
            )
            return

        if self.in_practice_round:
            self.finish_practice_round()
            return

        if self.data_logger is None:
            return

        submitted_at = datetime.now()
        elapsed = time.perf_counter() - self.current_state.started_at_perf
        shape_layout = [shape.as_dict() for shape in self.shapes.values()]

        row = {
            **self.participant_info,
            "idea_number": self.current_state.idea_number,
            "description": description,
            "time_spent_seconds": round(elapsed, 3),
            "number_of_shapes_used": len(self.shapes),
            "number_of_moves": self.current_state.move_count,
            "mouse_positions_json": json.dumps(self.current_state.mouse_positions),
            "total_mouse_distance_px": round(self.current_state.total_mouse_distance, 2),
            "rotation_count": self.current_state.rotation_count,
            "resize_count": self.current_state.resize_count,
            "idea_started_at": self.current_state.started_at_wall.isoformat(
                timespec="seconds"
            ),
            "submitted_at": submitted_at.isoformat(timespec="seconds"),
            "shape_layout_json": json.dumps(shape_layout),
        }

        self.data_logger.append(row)
        self.hooks.on_submit(row)
        self.hooks.send_eeg_marker(f"idea_{self.current_state.idea_number}_submit")

        self.total_ideas += 1
        if (
            self.config_model.idea_limit is not None
            and self.total_ideas >= self.config_model.idea_limit
        ):
            self.finish_experiment()
            return

        self.start_next_idea()

    def finish_practice_round(self) -> None:
        self.current_state = None
        self.clear_workspace()
        self.clear_screen()

        frame = ttk.Frame(self, padding=42)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Practice Complete", font=("Helvetica", 28, "bold")).pack(
            pady=(95, 14)
        )
        ttk.Label(
            frame,
            text="The next round is the actual experiment. Practice data was not saved.",
            font=("Helvetica", 15),
            wraplength=720,
        ).pack(pady=10)
        ttk.Button(
            frame,
            text="Start Actual Experiment",
            command=self.start_actual_experiment,
        ).pack(pady=28)

    def finish_experiment(self) -> None:
        data_path = self.data_logger.path if self.data_logger is not None else None
        self.current_state = None
        self.clear_screen()

        frame = ttk.Frame(self, padding=42)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Task Complete", font=("Helvetica", 28, "bold")).pack(
            pady=(95, 14)
        )
        ttk.Label(
            frame,
            text=f"Total ideas submitted: {self.total_ideas}",
            font=("Helvetica", 18),
        ).pack(pady=10)
        if data_path is not None:
            ttk.Label(
                frame,
                text=f"Data saved to: {data_path}",
                font=("Helvetica", 12),
            ).pack(pady=10)
        ttk.Button(frame, text="Close", command=self.destroy).pack(pady=28)

    def find_canvas_item(self, x: float, y: float) -> int | None:
        if self.canvas is None:
            return None
        found = self.canvas.find_overlapping(x, y, x, y)
        return found[-1] if found else None

    def palette_kind_from_tags(self, tags: tuple[str, ...]) -> str | None:
        for tag in tags:
            if tag.startswith("palette:"):
                return tag.split(":", 1)[1]
        return None

    def shape_id_from_tags(self, tags: tuple[str, ...]) -> int | None:
        for tag in tags:
            if tag.startswith("shape:"):
                return int(tag.split(":", 1)[1])
        return None

    def in_workspace(self, x: float, y: float) -> bool:
        x1, y1, x2, y2 = self.workspace_bounds
        return x1 <= x <= x2 and y1 <= y <= y2

    def copy_shape(self, shape: ShapeItem) -> ShapeItem:
        return ShapeItem(
            shape_id=shape.shape_id,
            kind=shape.kind,
            cx=shape.cx,
            cy=shape.cy,
            width=shape.width,
            height=shape.height,
            angle=shape.angle,
            color=shape.color,
            canvas_id=shape.canvas_id,
        )

    def distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        return math.hypot(x2 - x1, y2 - y1)


def main() -> None:
    app = AlternativeUsesBuilder()
    app.mainloop()


if __name__ == "__main__":
    main()
