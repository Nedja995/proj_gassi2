"""Theme definitions — all visual constants in one place.

Every widget references theme properties instead of hardcoded values.
Swap themes = swap one object. No UI code changes needed.
"""

from pydantic import BaseModel


class Theme(BaseModel):
    """Complete visual theme definition."""

    name: str = "dark"

    # backgrounds
    bg_primary: str = "#1a1a2e"
    bg_header: str = "#16213e"
    bg_footer: str = "#16213e"
    bg_input: str = "#0f0f23"
    bg_button_hover: str = "#2a2a4e"

    # foregrounds
    fg_accent: str = "#00ff88"
    fg_text: str = "#cccccc"
    fg_dim: str = "#555555"
    fg_warning: str = "#ffaa00"
    fg_error: str = "#ff4444"
    fg_loading: str = "#ffaa00"
    fg_button: str = "#bbbbbb"
    fg_button_active: str = "#ffffff"

    # typography
    font_family: str = "Consolas"
    font_size_normal: int = 10
    font_size_small: int = 8
    font_size_title: int = 9

    # layout
    header_height: int = 22
    footer_height: int = 18
    window_width: int = 380
    window_height: int = 280
    window_min_width: int = 280
    window_min_height: int = 160
    toolbar_collapsed_height: int = 22
    padding_x: int = 6
    padding_y: int = 4

    # transparency
    window_alpha: float = 0.88
    window_alpha_locked: float = 0.60
    window_alpha_collapsed: float = 0.75

    # helpers — return font tuples for tkinter
    def font(self, size: str = "normal", bold: bool = False) -> tuple[str, int] | tuple[str, int, str]:
        sizes = {
            "normal": self.font_size_normal,
            "small": self.font_size_small,
            "title": self.font_size_title,
        }
        sz = sizes.get(size, self.font_size_normal)
        if bold:
            return (self.font_family, sz, "bold")
        return (self.font_family, sz)


# ── preset themes ─────────────────────────────────────────────────

DARK_THEME = Theme(name="dark")

MIDNIGHT_THEME = Theme(
    name="midnight",
    bg_primary="#0d1117",
    bg_header="#161b22",
    bg_footer="#161b22",
    bg_input="#0d1117",
    fg_accent="#58a6ff",
    fg_text="#c9d1d9",
    fg_dim="#484f58",
    fg_button="#8b949e",
)

FOREST_THEME = Theme(
    name="forest",
    bg_primary="#1b2a1b",
    bg_header="#0f1f0f",
    bg_footer="#0f1f0f",
    bg_input="#142014",
    fg_accent="#7ccd7c",
    fg_text="#b8d4b8",
    fg_dim="#4a6a4a",
    fg_button="#8aaa8a",
)

THEMES: dict[str, Theme] = {
    "dark": DARK_THEME,
    "midnight": MIDNIGHT_THEME,
    "forest": FOREST_THEME,
}
