"""Ventana principal — Gestor Productos."""

import logging
import tkinter as tk

from app.ui import theme
from app.ui.views.main_view import MainView

logger = logging.getLogger(__name__)


class AppWindow(tk.Tk):
    """Ventana principal de Gestor Productos."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.title("Gestor Productos")
        self.geometry("1100x800")
        self.minsize(800, 600)
        self.configure(bg=theme.BG_PRIMARY)

        self._build()

    def _build(self) -> None:
        self._view = MainView(self)
        self._view.pack(fill="both", expand=True)
