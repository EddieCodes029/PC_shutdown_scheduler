import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, ttk


@dataclass
class ScheduleInfo:
    target_time: datetime
    seconds: int
    mode_label: str
    force_close: bool


class ShutdownController:
    def schedule_shutdown(self, seconds: int, force_close: bool) -> None:
        command = ["shutdown", "/s", "/t", str(seconds)]
        if force_close:
            command.append("/f")
        self._run(command)

    def cancel_shutdown(self) -> None:
        self._run(["shutdown", "/a"])

    @staticmethod
    def _run(command: list[str]) -> None:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0:
            error = (completed.stderr or completed.stdout or "Unknown error").strip()
            raise RuntimeError(error)


class SchedulerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PC Shutdown Scheduler")
        self.root.geometry("620x520")
        self.root.minsize(560, 480)
        self.root.configure(bg="#f4f0e8")
        self.main_canvas: tk.Canvas | None = None

        self.controller = ShutdownController()
        self.current_schedule: ScheduleInfo | None = None

        self.mode_var = tk.StringVar(value="duration")
        self.hours_var = tk.StringVar(value="0")
        self.minutes_var = tk.StringVar(value="30")
        self.time_var = tk.StringVar(value="22:30")
        self.force_close_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(
            value="No shutdown is currently scheduled from this app."
        )
        self.helper_var = tk.StringVar(
            value="Set a duration or exact time, then schedule the shutdown."
        )

        self._configure_styles()
        self._build_ui()
        self._update_countdown()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Card.TFrame",
            background="#fffaf2",
            borderwidth=0,
            relief="flat",
        )
        style.configure(
            "Header.TLabel",
            background="#f4f0e8",
            foreground="#1d2a33",
            font=("Segoe UI Semibold", 22),
        )
        style.configure(
            "Body.TLabel",
            background="#fffaf2",
            foreground="#34424d",
            font=("Segoe UI", 11),
        )
        style.configure(
            "Hero.TLabel",
            background="#fffaf2",
            foreground="#1d2a33",
            font=("Segoe UI Semibold", 14),
        )
        style.configure(
            "Status.TLabel",
            background="#e7f0e7",
            foreground="#23412a",
            font=("Segoe UI Semibold", 11),
        )
        style.configure(
            "Muted.TLabel",
            background="#f4f0e8",
            foreground="#5f6b73",
            font=("Segoe UI", 10),
        )
        style.configure(
            "TButton",
            font=("Segoe UI Semibold", 10),
            padding=(12, 8),
            borderwidth=0,
        )
        style.map(
            "TButton",
            background=[("active", "#d88756"), ("!disabled", "#c46f3d")],
            foreground=[("!disabled", "#ffffff")],
        )
        style.configure(
            "Secondary.TButton",
            background="#d9e2d3",
            foreground="#1f2a1f",
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#c7d6bf"), ("!disabled", "#d9e2d3")],
            foreground=[("!disabled", "#1f2a1f")],
        )
        style.configure(
            "TRadiobutton",
            background="#fffaf2",
            foreground="#27323b",
            font=("Segoe UI", 10),
        )
        style.configure(
            "TCheckbutton",
            background="#fffaf2",
            foreground="#27323b",
            font=("Segoe UI", 10),
        )
        style.configure("TEntry", fieldbackground="#ffffff", padding=6)

    def _build_ui(self) -> None:
        outer = tk.Frame(self.root, bg="#f4f0e8")
        outer.pack(fill="both", expand=True)

        self.main_canvas = tk.Canvas(
            outer,
            bg="#f4f0e8",
            highlightthickness=0,
            bd=0,
        )
        scrollbar = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=self.main_canvas.yview,
        )
        self.main_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.main_canvas.pack(side="left", fill="both", expand=True)

        container = tk.Frame(self.main_canvas, bg="#f4f0e8", padx=24, pady=24)
        canvas_window = self.main_canvas.create_window(
            (0, 0),
            window=container,
            anchor="nw",
        )

        container.bind(
            "<Configure>",
            lambda event: self.main_canvas.configure(
                scrollregion=self.main_canvas.bbox("all")
            ),
        )
        self.main_canvas.bind(
            "<Configure>",
            lambda event: self.main_canvas.itemconfigure(canvas_window, width=event.width),
        )
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

        ttk.Label(container, text="PC Shutdown Scheduler", style="Header.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            container,
            text=(
                "Schedule a Windows shutdown after a duration or at a specific time. "
                "Use cancel anytime before it runs."
            ),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(6, 18))

        card = ttk.Frame(container, style="Card.TFrame", padding=20)
        card.pack(fill="x")

        ttk.Label(card, text="Schedule Mode", style="Hero.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w"
        )
        ttk.Radiobutton(
            card,
            text="After a duration",
            variable=self.mode_var,
            value="duration",
            command=self._toggle_mode,
        ).grid(row=1, column=0, sticky="w", pady=(14, 4))
        ttk.Radiobutton(
            card,
            text="At an exact time",
            variable=self.mode_var,
            value="clock",
            command=self._toggle_mode,
        ).grid(row=1, column=2, sticky="w", pady=(14, 4))

        self.duration_frame = ttk.Frame(card, style="Card.TFrame")
        self.duration_frame.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(8, 10))
        self.duration_frame.columnconfigure((0, 1, 2, 3), weight=1)

        ttk.Label(self.duration_frame, text="Hours", style="Body.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Entry(self.duration_frame, textvariable=self.hours_var, width=10).grid(
            row=1, column=0, sticky="ew", padx=(0, 12)
        )
        ttk.Label(self.duration_frame, text="Minutes", style="Body.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        ttk.Entry(self.duration_frame, textvariable=self.minutes_var, width=10).grid(
            row=1, column=1, sticky="ew"
        )

        quick_frame = ttk.Frame(self.duration_frame, style="Card.TFrame")
        quick_frame.grid(row=2, column=0, columnspan=4, sticky="w", pady=(12, 0))
        ttk.Label(quick_frame, text="Quick presets", style="Body.TLabel").pack(
            side="left", padx=(0, 8)
        )
        for label, total_minutes in [("15m", 15), ("30m", 30), ("1h", 60), ("2h", 120)]:
            ttk.Button(
                quick_frame,
                text=label,
                style="Secondary.TButton",
                command=lambda m=total_minutes: self._set_preset(m),
            ).pack(side="left", padx=(0, 6))

        self.clock_frame = ttk.Frame(card, style="Card.TFrame")
        self.clock_frame.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(8, 10))
        ttk.Label(
            self.clock_frame,
            text="Time (24-hour format, HH:MM)",
            style="Body.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.clock_frame, textvariable=self.time_var, width=14).grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )

        ttk.Checkbutton(
            card,
            text="Force-close apps during shutdown",
            variable=self.force_close_var,
        ).grid(row=4, column=0, columnspan=4, sticky="w", pady=(6, 2))

        ttk.Label(card, textvariable=self.helper_var, style="Body.TLabel").grid(
            row=5, column=0, columnspan=4, sticky="w", pady=(10, 14)
        )

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=6, column=0, columnspan=4, sticky="ew")
        ttk.Button(actions, text="Schedule Shutdown", command=self._schedule).pack(
            side="left"
        )
        ttk.Button(
            actions,
            text="Cancel Shutdown",
            style="Secondary.TButton",
            command=self._cancel_schedule,
        ).pack(side="left", padx=(10, 0))

        status_frame = ttk.Frame(container, style="Card.TFrame", padding=20)
        status_frame.pack(fill="x", pady=(18, 0))
        ttk.Label(status_frame, text="Status", style="Hero.TLabel").pack(anchor="w")
        tk.Label(
            status_frame,
            textvariable=self.status_var,
            justify="left",
            anchor="w",
            bg="#e7f0e7",
            fg="#23412a",
            font=("Segoe UI Semibold", 11),
            padx=14,
            pady=14,
            wraplength=520,
        ).pack(fill="x", pady=(12, 0))

        notes = ttk.Frame(container, style="Card.TFrame", padding=20)
        notes.pack(fill="both", expand=True, pady=(18, 0))
        ttk.Label(notes, text="Included Features", style="Hero.TLabel").pack(anchor="w")
        features = (
            "• Duration-based scheduling\n"
            "• Exact time scheduling (today or tomorrow automatically)\n"
            "• Quick preset buttons\n"
            "• Live countdown\n"
            "• One-click cancellation"
        )
        ttk.Label(notes, text=features, style="Body.TLabel").pack(anchor="w", pady=(10, 0))

        self._toggle_mode()

    def _toggle_mode(self) -> None:
        duration_enabled = self.mode_var.get() == "duration"
        self._set_frame_state(self.duration_frame, duration_enabled)
        self._set_frame_state(self.clock_frame, not duration_enabled)

        if duration_enabled:
            self.helper_var.set("The PC will shut down after the entered duration.")
        else:
            self.helper_var.set(
                "If the chosen time has already passed today, shutdown will be set for tomorrow."
            )

    def _set_frame_state(self, frame: ttk.Frame, enabled: bool) -> None:
        state = "!disabled" if enabled else "disabled"
        for child in frame.winfo_children():
            try:
                child.state([state])
            except tk.TclError:
                pass

    def _on_mousewheel(self, event: tk.Event) -> None:
        if self.main_canvas is None:
            return
        self.main_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _set_preset(self, total_minutes: int) -> None:
        self.mode_var.set("duration")
        self.hours_var.set(str(total_minutes // 60))
        self.minutes_var.set(str(total_minutes % 60))
        self._toggle_mode()

    def _schedule(self) -> None:
        try:
            schedule_info = self._build_schedule_info()
            try:
                self.controller.cancel_shutdown()
            except RuntimeError:
                pass
            self.controller.schedule_shutdown(
                seconds=schedule_info.seconds,
                force_close=schedule_info.force_close,
            )
        except ValueError as error:
            messagebox.showerror("Invalid input", str(error))
            return
        except RuntimeError as error:
            messagebox.showerror("Windows shutdown error", str(error))
            return

        self.current_schedule = schedule_info
        self.status_var.set(self._format_status(schedule_info))
        messagebox.showinfo(
            "Shutdown scheduled",
            f"Shutdown scheduled for {schedule_info.target_time.strftime('%I:%M %p on %d %b %Y')}.",
        )

    def _cancel_schedule(self) -> None:
        try:
            self.controller.cancel_shutdown()
        except RuntimeError as error:
            messagebox.showerror("Cancel failed", str(error))
            return

        self.current_schedule = None
        self.status_var.set("Scheduled shutdown cancelled.")
        messagebox.showinfo("Cancelled", "The scheduled shutdown has been cancelled.")

    def _build_schedule_info(self) -> ScheduleInfo:
        force_close = self.force_close_var.get()
        now = datetime.now()

        if self.mode_var.get() == "duration":
            hours = self._parse_non_negative_int(self.hours_var.get(), "hours")
            minutes = self._parse_non_negative_int(self.minutes_var.get(), "minutes")
            total_seconds = hours * 3600 + minutes * 60
            if total_seconds <= 0:
                raise ValueError("Enter a duration greater than zero.")
            target_time = now + timedelta(seconds=total_seconds)
            return ScheduleInfo(
                target_time=target_time,
                seconds=total_seconds,
                mode_label=f"after {hours}h {minutes}m",
                force_close=force_close,
            )

        raw_time = self.time_var.get().strip()
        try:
            parsed = datetime.strptime(raw_time, "%H:%M")
        except ValueError as error:
            raise ValueError("Enter the exact time in 24-hour HH:MM format.") from error

        target_time = now.replace(
            hour=parsed.hour,
            minute=parsed.minute,
            second=0,
            microsecond=0,
        )
        if target_time <= now:
            target_time += timedelta(days=1)

        total_seconds = int((target_time - now).total_seconds())
        return ScheduleInfo(
            target_time=target_time,
            seconds=total_seconds,
            mode_label=f"at {target_time.strftime('%I:%M %p')}",
            force_close=force_close,
        )

    @staticmethod
    def _parse_non_negative_int(raw_value: str, field_name: str) -> int:
        try:
            value = int(raw_value.strip())
        except ValueError as error:
            raise ValueError(f"Enter a whole number for {field_name}.") from error
        if value < 0:
            raise ValueError(f"{field_name.capitalize()} cannot be negative.")
        return value

    def _update_countdown(self) -> None:
        if self.current_schedule is not None:
            remaining = int((self.current_schedule.target_time - datetime.now()).total_seconds())
            if remaining <= 0:
                self.status_var.set("Shutdown time reached. Windows should now be processing the request.")
                self.current_schedule = None
            else:
                self.status_var.set(self._format_status(self.current_schedule, remaining))
        self.root.after(1000, self._update_countdown)

    def _format_status(
        self, schedule_info: ScheduleInfo, remaining_seconds: int | None = None
    ) -> str:
        remaining_seconds = (
            schedule_info.seconds if remaining_seconds is None else remaining_seconds
        )
        hours, remainder = divmod(remaining_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        countdown = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        force_note = " with force-close enabled" if schedule_info.force_close else ""
        return (
            f"Shutdown scheduled {schedule_info.mode_label}{force_note}.\n"
            f"Target: {schedule_info.target_time.strftime('%I:%M %p on %d %b %Y')}\n"
            f"Countdown: {countdown}"
        )


def main() -> int:
    if sys.platform != "win32":
        print("This app is intended for Windows because it uses the Windows shutdown command.")
        return 1

    root = tk.Tk()
    SchedulerApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
