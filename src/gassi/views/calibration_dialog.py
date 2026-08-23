"""Calibration dialog — runs CalibrationService and shows results.

Shows a progress indicator while calibration runs in a background thread
(CalibrationService.run() is synchronous but calls asyncio.run internally).
Displays per-region accept/reject results with confidence scores.
"""

import logging
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable

from gassi.core.calibration_service import CalibrationResult, CalibrationService
from gassi.core.theme.theme import Theme

logger = logging.getLogger(__name__)

_WIDTH = 480
_HEIGHT = 360


class CalibrationDialog(tk.Toplevel):
    """Modal dialog that runs HUD auto-calibration and displays results."""

    def __init__(
        self,
        parent: tk.Misc,
        theme: Theme,
        calibration_service: CalibrationService,
        game_id: str,
        on_complete: Callable[[CalibrationResult], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._service = calibration_service
        self._game_id = game_id
        self._on_complete = on_complete
        t = theme

        self.title("GASSI — HUD Calibration")
        self.geometry(f"{_WIDTH}x{_HEIGHT}")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(bg=t.bg_primary)
        self.transient(parent)
        self.grab_set()

        # header
        tk.Label(
            self, text="HUD Auto-Calibration",
            bg=t.bg_primary, fg=t.fg_accent,
            font=t.font("normal", bold=True),
        ).pack(pady=(16, 4))

        tk.Label(
            self,
            text="Captures full screen → Gemini detects HUD regions → OCR validates each.",
            bg=t.bg_primary, fg=t.fg_dim, font=t.font("small"),
            wraplength=_WIDTH - 32,
        ).pack(pady=(0, 12))

        # status label
        self._status_var = tk.StringVar(value="Ready to calibrate.")
        tk.Label(
            self, textvariable=self._status_var,
            bg=t.bg_primary, fg=t.fg_text, font=t.font("normal"),
        ).pack()

        # progress bar
        self._progress = ttk.Progressbar(
            self, mode="indeterminate", length=_WIDTH - 64,
        )
        self._progress.pack(pady=8)

        # results text area
        result_frame = tk.Frame(self, bg=t.bg_primary)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))

        self._result_text = tk.Text(
            result_frame, bg=t.bg_input, fg=t.fg_text,
            font=t.font("small"), bd=0, padx=8, pady=6,
            state=tk.DISABLED, height=8, wrap=tk.WORD,
        )
        _scroll = ttk.Scrollbar(result_frame, command=self._result_text.yview)
        self._result_text.configure(yscrollcommand=_scroll.set)
        _scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._result_text.tag_configure("accepted", foreground=t.fg_accent)
        self._result_text.tag_configure("rejected", foreground=t.fg_error)
        self._result_text.tag_configure("info", foreground=t.fg_dim)
        self._result_text.tag_configure("error", foreground=t.fg_error)

        # buttons
        btn_frame = tk.Frame(self, bg=t.bg_primary)
        btn_frame.pack(fill=tk.X, padx=16, pady=(0, 16))

        self._calibrate_btn = tk.Button(
            btn_frame, text="Start Calibration",
            bg=t.bg_header, fg=t.fg_accent,
            font=t.font("normal", bold=True),
            bd=0, activebackground=t.bg_button_hover,
            cursor="hand2", padx=12, pady=4,
            command=self._start_calibration,
        )
        self._calibrate_btn.pack(side=tk.LEFT)

        self._clear_btn = tk.Button(
            btn_frame, text="Clear User Calibration",
            bg=t.bg_header, fg=t.fg_dim,
            font=t.font("small"),
            bd=0, activebackground=t.bg_button_hover,
            cursor="hand2", padx=8, pady=4,
            command=self._clear_calibration,
        )
        self._clear_btn.pack(side=tk.LEFT, padx=(8, 0))

        tk.Button(
            btn_frame, text="Close",
            bg=t.bg_header, fg=t.fg_button,
            font=t.font("normal"),
            bd=0, activebackground=t.bg_button_hover,
            cursor="hand2", padx=8, pady=4,
            command=self.destroy,
        ).pack(side=tk.RIGHT)

        self._center_on_parent(parent)
        self.bind("<Escape>", lambda _e: self.destroy())

    # ── calibration ───────────────────────────────────────────────────

    def _start_calibration(self) -> None:
        self._calibrate_btn.config(state=tk.DISABLED)
        self._clear_btn.config(state=tk.DISABLED)
        self._status_var.set("Capturing screen and contacting Gemini…")
        self._progress.start(12)
        self._clear_result_text()

        thread = threading.Thread(target=self._run_in_thread, daemon=True)
        thread.start()

    def _run_in_thread(self) -> None:
        """Run calibration in background thread, post result to tkinter."""
        result = self._service.run(self._game_id)
        self.after(0, self._on_calibration_done, result)

    def _on_calibration_done(self, result: CalibrationResult) -> None:
        self._progress.stop()
        self._calibrate_btn.config(state=tk.NORMAL)
        self._clear_btn.config(state=tk.NORMAL)

        if result.error:
            self._status_var.set("Calibration failed.")
            self._append_result(f"Error: {result.error}\n", "error")
        else:
            self._status_var.set(result.summary)
            self._append_result(
                f"Completed in {result.duration_seconds:.1f}s\n\n", "info"
            )
            for r in result.accepted:
                self._append_result(
                    f"✓  {r.region.label}  (conf={r.ocr_confidence:.2f})\n",
                    "accepted",
                )
            if result.rejected:
                self._append_result("\n", "info")
                for r in result.rejected:
                    self._append_result(
                        f"✗  {r.region.label}  — {r.rejection_reason}\n",
                        "rejected",
                    )

            if result.success:
                self._append_result(
                    "\nUser calibration saved. Restart GASSI to apply.\n", "info"
                )

        if self._on_complete:
            self._on_complete(result)

    def _clear_calibration(self) -> None:
        self._service.clear_user_calibration(self._game_id)
        self._status_var.set("User calibration cleared — manifest defaults will be used.")
        self._clear_result_text()
        self._append_result("hud_regions_user.yaml deleted.\n", "info")

    # ── helpers ───────────────────────────────────────────────────────

    def _append_result(self, text: str, tag: str = "") -> None:
        self._result_text.config(state=tk.NORMAL)
        self._result_text.insert(tk.END, text, tag)
        self._result_text.config(state=tk.DISABLED)
        self._result_text.see(tk.END)

    def _clear_result_text(self) -> None:
        self._result_text.config(state=tk.NORMAL)
        self._result_text.delete("1.0", tk.END)
        self._result_text.config(state=tk.DISABLED)

    def _center_on_parent(self, parent: tk.Misc) -> None:
        self.update_idletasks()
        try:
            px = parent.winfo_x() + (parent.winfo_width() - _WIDTH) // 2
            py = parent.winfo_y() + (parent.winfo_height() - _HEIGHT) // 2
            self.geometry(f"+{max(px, 0)}+{max(py, 0)}")
        except tk.TclError:
            pass
