"""
Splash screen with logo and fade-in animation.

Displays the DisC0ntrol logo centered on screen for a few seconds
before launching the main dashboard.
"""

import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk


# Logo display size
LOGO_SIZE = 180
# Total splash duration in ms
SPLASH_DURATION = 3000
# Fade-in steps
FADE_STEPS = 20
FADE_INTERVAL = 30  # ms per step


class SplashScreen(tk.Toplevel):
    """Frameless splash window with logo and app name."""

    def __init__(self, master):
        super().__init__(master)

        # Frameless, always on top, centered
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#1a1a2e")

        # Window size
        win_w, win_h = 340, 360

        # Center on screen
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # Canvas for drawing
        self._canvas = tk.Canvas(
            self, width=win_w, height=win_h,
            bg="#1a1a2e", highlightthickness=0,
        )
        self._canvas.pack(fill="both", expand=True)

        # Load logo
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "logo_Disc0ntrol.png"
        if logo_path.is_file():
            img = Image.open(logo_path).resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
            self._logo_image = ImageTk.PhotoImage(img)
        else:
            # Fallback: colored circle
            self._logo_image = None

        # Draw elements (initially transparent via alpha trick)
        cx = win_w // 2
        logo_y = 120

        if self._logo_image:
            self._logo_id = self._canvas.create_image(cx, logo_y, image=self._logo_image)
        else:
            self._logo_id = self._canvas.create_oval(
                cx - 60, logo_y - 60, cx + 60, logo_y + 60,
                fill="#27ae60", outline="",
            )

        # App name
        self._title_id = self._canvas.create_text(
            cx, logo_y + LOGO_SIZE // 2 + 30,
            text="DisC0ntrol",
            font=("Segoe UI Black", 26),
            fill="#ecf0f1",
        )

        # Subtitle
        self._sub_id = self._canvas.create_text(
            cx, logo_y + LOGO_SIZE // 2 + 62,
            text="Bot Dashboard",
            font=("Segoe UI", 12),
            fill="#7f8c8d",
        )

        # Start fade-in
        self._alpha = 0.0
        self.attributes("-alpha", 0.0)
        self.after(100, self._fade_in)

    def _fade_in(self, step=0):
        """Gradually increase window opacity."""
        if step <= FADE_STEPS:
            self._alpha = step / FADE_STEPS
            self.attributes("-alpha", self._alpha)
            self.after(FADE_INTERVAL, self._fade_in, step + 1)
        else:
            # Fully visible — schedule close
            remaining = SPLASH_DURATION - (FADE_STEPS * FADE_INTERVAL) - 100
            self.after(max(remaining, 500), self._fade_out)

    def _fade_out(self, step=0):
        """Gradually decrease window opacity then destroy."""
        if step <= FADE_STEPS:
            self._alpha = 1.0 - (step / FADE_STEPS)
            self.attributes("-alpha", self._alpha)
            self.after(FADE_INTERVAL, self._fade_out, step + 1)
        else:
            self.destroy()
