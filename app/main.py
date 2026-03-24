#!/usr/bin/env python3
"""Entry point de Gestor Productos."""

import logging
import sys
from pathlib import Path

app_dir = Path(__file__).resolve().parent
if str(app_dir.parent) not in sys.path:
    sys.path.insert(0, str(app_dir.parent))

from dotenv import load_dotenv
load_dotenv(app_dir.parent / ".env")

from app.db import init_db
from app.ui.theme import setup_theme
from app.ui.app_window import AppWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Iniciando Gestor Productos")
    init_db()

    root = AppWindow(className="gestorproductos")

    # Ícono de la ventana
    icon_path = app_dir / "assets" / "icon.png"
    if icon_path.exists():
        try:
            from PIL import Image, ImageTk
            icon_img = Image.open(icon_path)
            icon_sizes = []
            for size in (16, 32, 48, 64, 128, 256):
                resized = icon_img.resize((size, size), Image.LANCZOS)
                icon_sizes.append(ImageTk.PhotoImage(resized))
            root.tk.call('wm', 'iconphoto', root._w, '-default', *icon_sizes)
            root._icon_refs = icon_sizes
        except Exception as e:
            logger.warning("No se pudo cargar ícono: %s", e)

    setup_theme()
    root.mainloop()


if __name__ == "__main__":
    main()
