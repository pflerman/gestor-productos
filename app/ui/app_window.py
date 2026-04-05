"""Ventana principal — Gestor Productos."""

import logging
import tkinter as tk
from tkinter import ttk

from app.ui import theme
from app.ui.views.main_view import MainView
from app.ui.views.ia_view import IAView

logger = logging.getLogger(__name__)


class AppWindow(tk.Tk):
    """Ventana principal de Gestor Productos."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.title("Gestor Productos")
        self.geometry("1100x800")
        self.minsize(400, 300)
        self.configure(bg=theme.BG_PRIMARY)

        self._build()

    def _build(self) -> None:
        # Notebook con pestañas
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True)

        # Pestaña 1: Productos
        self._productos_view = MainView(self._notebook)
        self._notebook.add(self._productos_view, text="  📦 Productos  ")

        # Pestaña 2: IA
        self._ia_view = IAView(self._notebook)
        self._notebook.add(self._ia_view, text="  🤖 IA  ")
