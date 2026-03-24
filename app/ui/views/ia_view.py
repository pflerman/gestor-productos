"""Vista de Inteligencia Artificial — Claude (texto) + Gemini (imágenes)."""

import logging
import os
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
from pathlib import Path

from app.ui import theme

logger = logging.getLogger(__name__)


def _get_claude_client():
    """Cliente lazy de Anthropic."""
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY no encontrada en .env")
    return anthropic.Anthropic(api_key=api_key)


def _get_gemini_client():
    """Cliente lazy de Google GenAI."""
    from google import genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        env_path = Path("/home/pepe/Proyectos/gemini-test/.env")
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY no encontrada")
    return genai.Client(api_key=api_key)


class IAView(tk.Frame):
    """Vista con dos paneles: Claude (texto) y Gemini (imágenes)."""

    def __init__(self, master: tk.Widget, **kwargs):
        super().__init__(master, bg=theme.BG_PRIMARY, **kwargs)
        self._last_image_bytes: bytes | None = None
        self._photo_ref = None  # mantener referencia para que no se recolecte
        self._build()

    def _build(self) -> None:
        # ── Header ────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=theme.BG_PRIMARY)
        header.pack(fill="x", padx=20, pady=(20, 12))

        tk.Label(header, text="🤖 Asistente IA", font=theme.FONT_TITLE,
                 bg=theme.BG_PRIMARY, fg=theme.TEXT_PRIMARY).pack(side="left")

        # ── Contenedor principal con dos columnas ─────────────────────────
        main = tk.Frame(self, bg=theme.BG_PRIMARY)
        main.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # ── Panel CLAUDE (izquierda) ──────────────────────────────────────
        self._build_claude_panel(main)

        # ── Panel GEMINI (derecha) ────────────────────────────────────────
        self._build_gemini_panel(main)

    # ══════════════════════════════════════════════════════════════════════════
    # CLAUDE — Generación de texto
    # ══════════════════════════════════════════════════════════════════════════

    def _build_claude_panel(self, parent: tk.Widget) -> None:
        card = tk.Frame(parent, bg=theme.BG_CARD, bd=1, relief="solid",
                        highlightbackground=theme.BORDER, highlightthickness=1)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        # Título
        title_frame = tk.Frame(card, bg="#5B48D9")
        title_frame.pack(fill="x")
        tk.Label(title_frame, text="🧠 Claude — Texto",
                 font=theme.FONT_BOLD, bg="#5B48D9", fg="white"
                 ).pack(anchor="w", padx=12, pady=8)

        inner = tk.Frame(card, bg=theme.BG_CARD)
        inner.pack(fill="both", expand=True, padx=12, pady=8)

        # Prompt
        tk.Label(inner, text="Tu prompt:", font=theme.FONT_SMALL,
                 bg=theme.BG_CARD, fg=theme.TEXT_SECONDARY).pack(anchor="w")
        self._claude_prompt = scrolledtext.ScrolledText(
            inner, height=4, font=theme.FONT_NORMAL,
            bg=theme.BG_INPUT, fg=theme.TEXT_PRIMARY,
            relief="flat", bd=1, wrap="word",
            highlightbackground=theme.BORDER, highlightthickness=1)
        self._claude_prompt.pack(fill="x", pady=(2, 8))

        # Botón enviar
        btn_frame = tk.Frame(inner, bg=theme.BG_CARD)
        btn_frame.pack(fill="x", pady=(0, 8))

        self._btn_claude = tk.Button(
            btn_frame, text="✨ Generar con Claude", font=theme.FONT_BOLD,
            bg="#5B48D9", fg="white", relief="flat", bd=0,
            padx=14, pady=6, cursor="hand2", command=self._on_claude_send)
        self._btn_claude.pack(side="left")

        self._claude_status = tk.Label(
            btn_frame, text="", font=theme.FONT_SMALL,
            bg=theme.BG_CARD, fg=theme.TEXT_MUTED)
        self._claude_status.pack(side="left", padx=(10, 0))

        # Respuesta
        tk.Label(inner, text="Respuesta:", font=theme.FONT_SMALL,
                 bg=theme.BG_CARD, fg=theme.TEXT_SECONDARY).pack(anchor="w")
        self._claude_response = scrolledtext.ScrolledText(
            inner, height=12, font=theme.FONT_NORMAL,
            bg=theme.BG_INPUT, fg=theme.TEXT_PRIMARY,
            relief="flat", bd=1, wrap="word",
            highlightbackground=theme.BORDER, highlightthickness=1,
            state="disabled")
        self._claude_response.pack(fill="both", expand=True, pady=(2, 8))

        # Botón copiar
        self._btn_copy = tk.Button(
            inner, text="📋 Copiar respuesta", font=theme.FONT_BOLD,
            bg=theme.BTN_INFO, fg="white", relief="flat", bd=0,
            padx=14, pady=4, cursor="hand2", command=self._on_copy_claude,
            state="disabled")
        self._btn_copy.pack(anchor="w")

    # ══════════════════════════════════════════════════════════════════════════
    # GEMINI — Generación de imágenes
    # ══════════════════════════════════════════════════════════════════════════

    def _build_gemini_panel(self, parent: tk.Widget) -> None:
        card = tk.Frame(parent, bg=theme.BG_CARD, bd=1, relief="solid",
                        highlightbackground=theme.BORDER, highlightthickness=1)
        card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        # Título
        title_frame = tk.Frame(card, bg="#1A73E8")
        title_frame.pack(fill="x")
        tk.Label(title_frame, text="🎨 Gemini — Imágenes",
                 font=theme.FONT_BOLD, bg="#1A73E8", fg="white"
                 ).pack(anchor="w", padx=12, pady=8)

        inner = tk.Frame(card, bg=theme.BG_CARD)
        inner.pack(fill="both", expand=True, padx=12, pady=8)

        # Prompt
        tk.Label(inner, text="Describí la imagen:", font=theme.FONT_SMALL,
                 bg=theme.BG_CARD, fg=theme.TEXT_SECONDARY).pack(anchor="w")
        self._gemini_prompt = scrolledtext.ScrolledText(
            inner, height=4, font=theme.FONT_NORMAL,
            bg=theme.BG_INPUT, fg=theme.TEXT_PRIMARY,
            relief="flat", bd=1, wrap="word",
            highlightbackground=theme.BORDER, highlightthickness=1)
        self._gemini_prompt.pack(fill="x", pady=(2, 8))

        # Botón enviar
        btn_frame = tk.Frame(inner, bg=theme.BG_CARD)
        btn_frame.pack(fill="x", pady=(0, 8))

        self._btn_gemini = tk.Button(
            btn_frame, text="🖼️ Generar con Gemini", font=theme.FONT_BOLD,
            bg="#1A73E8", fg="white", relief="flat", bd=0,
            padx=14, pady=6, cursor="hand2", command=self._on_gemini_send)
        self._btn_gemini.pack(side="left")

        self._gemini_status = tk.Label(
            btn_frame, text="", font=theme.FONT_SMALL,
            bg=theme.BG_CARD, fg=theme.TEXT_MUTED)
        self._gemini_status.pack(side="left", padx=(10, 0))

        # Área de imagen
        self._img_frame = tk.Frame(inner, bg="#e8edf2", bd=1, relief="solid",
                                    highlightbackground=theme.BORDER,
                                    highlightthickness=1)
        self._img_frame.pack(fill="both", expand=True, pady=(0, 8))

        self._img_label = tk.Label(
            self._img_frame, text="🖼️ La imagen aparecerá acá",
            font=theme.FONT_NORMAL, bg="#e8edf2", fg=theme.TEXT_MUTED)
        self._img_label.pack(expand=True)

        # Botón guardar
        self._btn_save = tk.Button(
            inner, text="💾 Guardar imagen", font=theme.FONT_BOLD,
            bg=theme.BTN_SUCCESS, fg="white", relief="flat", bd=0,
            padx=14, pady=4, cursor="hand2", command=self._on_save_image,
            state="disabled")
        self._btn_save.pack(anchor="w")

    # ══════════════════════════════════════════════════════════════════════════
    # ACCIONES
    # ══════════════════════════════════════════════════════════════════════════

    def _on_claude_send(self) -> None:
        prompt = self._claude_prompt.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("Prompt vacío", "Escribí algo para enviar a Claude.")
            return

        self._btn_claude.configure(state="disabled")
        self._claude_status.configure(text="⏳ Generando...", fg=theme.WARNING)
        self._set_claude_response("")
        self._btn_copy.configure(state="disabled")

        threading.Thread(target=self._call_claude, args=(prompt,), daemon=True).start()

    def _call_claude(self, prompt: str) -> None:
        try:
            client = _get_claude_client()
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=16000,
                thinking={"type": "adaptive"},
                messages=[{"role": "user", "content": prompt}],
            )
            text = ""
            for block in response.content:
                if block.type == "text":
                    text += block.text
            self.after(0, self._claude_done, text, None)
        except Exception as e:
            self.after(0, self._claude_done, None, str(e))

    def _claude_done(self, text: str | None, error: str | None) -> None:
        self._btn_claude.configure(state="normal")
        if error:
            self._claude_status.configure(text=f"❌ Error: {error}", fg=theme.ERROR)
            return
        self._set_claude_response(text or "(sin respuesta)")
        self._claude_status.configure(text="✅ Listo!", fg=theme.SUCCESS)
        self._btn_copy.configure(state="normal")

    def _set_claude_response(self, text: str) -> None:
        self._claude_response.configure(state="normal")
        self._claude_response.delete("1.0", "end")
        self._claude_response.insert("1.0", text)
        self._claude_response.configure(state="disabled")

    def _on_copy_claude(self) -> None:
        self._claude_response.configure(state="normal")
        text = self._claude_response.get("1.0", "end").strip()
        self._claude_response.configure(state="disabled")
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._claude_status.configure(text="📋 ¡Copiado al portapapeles!", fg=theme.INFO)

    def _on_gemini_send(self) -> None:
        prompt = self._gemini_prompt.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("Prompt vacío", "Escribí una descripción de imagen.")
            return

        self._btn_gemini.configure(state="disabled")
        self._gemini_status.configure(text="⏳ Generando imagen... (puede tardar)", fg=theme.WARNING)
        self._btn_save.configure(state="disabled")
        self._img_label.configure(image="", text="⏳ Generando...",
                                   bg="#e8edf2", fg=theme.TEXT_MUTED)
        self._photo_ref = None

        threading.Thread(target=self._call_gemini, args=(prompt,), daemon=True).start()

    def _call_gemini(self, prompt: str) -> None:
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

        try:
            client = _get_gemini_client()
            from google.genai import types

            def _do():
                return client.models.generate_content(
                    model="gemini-2.5-flash-preview-05-20",
                    contents=[types.Content(parts=[types.Part.from_text(text=prompt)])],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"]),
                )

            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(_do)
                response = future.result(timeout=120)

            img_bytes = None
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    img_bytes = part.inline_data.data
                    break

            if img_bytes:
                self.after(0, self._gemini_done, img_bytes, None)
            else:
                self.after(0, self._gemini_done, None, "Gemini no devolvió imagen")

        except FuturesTimeout:
            self.after(0, self._gemini_done, None, "Timeout (120s) — intentá de nuevo")
        except Exception as e:
            self.after(0, self._gemini_done, None, str(e))

    def _gemini_done(self, img_bytes: bytes | None, error: str | None) -> None:
        self._btn_gemini.configure(state="normal")
        if error:
            self._gemini_status.configure(text=f"❌ {error}", fg=theme.ERROR)
            self._img_label.configure(image="", text=f"❌ {error}")
            return

        self._last_image_bytes = img_bytes
        self._gemini_status.configure(text="✅ ¡Imagen generada!", fg=theme.SUCCESS)
        self._btn_save.configure(state="normal")

        # Mostrar preview
        try:
            from PIL import Image, ImageTk
            import io

            img = Image.open(io.BytesIO(img_bytes))

            # Escalar para que entre en el panel
            max_w = self._img_frame.winfo_width() - 10
            max_h = self._img_frame.winfo_height() - 10
            if max_w < 100:
                max_w = 500
            if max_h < 100:
                max_h = 350

            img.thumbnail((max_w, max_h), Image.LANCZOS)
            self._photo_ref = ImageTk.PhotoImage(img)
            self._img_label.configure(image=self._photo_ref, text="",
                                       bg=theme.BG_CARD)
        except Exception as e:
            self._img_label.configure(
                image="",
                text=f"✅ Imagen generada ({len(img_bytes)} bytes)\n(preview no disponible: {e})")

    def _on_save_image(self) -> None:
        if not self._last_image_bytes:
            return
        path = filedialog.asksaveasfilename(
            title="Guardar imagen",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("Todos", "*.*")],
            initialfile="gemini_imagen.png")
        if not path:
            return
        Path(path).write_bytes(self._last_image_bytes)
        self._gemini_status.configure(
            text=f"💾 Guardada: {Path(path).name}", fg=theme.SUCCESS)
