"""Vista principal CRUD de Gestor Productos."""

import io
import logging
import subprocess
import tempfile
import unicodedata
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

import qrcode
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageTk

from app.ui import theme

from app import db

logger = logging.getLogger(__name__)

COLORES = ("Blanco", "Negro", "Blanco negro", "Gris", "Rosa", "Verde", "Violeta", "Transparente", "Rojo", "Azul")
COLUMNS = ("check", "id", "sku", "nombre", "largo", "ancho", "alto", "color", "precio_fob", "notas", "etiquetas")
COL_HEADERS = ("✓", "ID", "SKU", "Nombre", "Largo", "Ancho", "Alto", "Color", "Precio FOB", "Notas", "Etiquetas")
COL_WIDTHS = (35, 50, 110, 200, 80, 80, 80, 100, 100, 0, 150)


def _fmt_num(val) -> str:
    """Formatea número: max 2 decimales, sin ceros innecesarios."""
    n = float(val)
    if n == int(n):
        return str(int(n))
    return f"{n:.2f}".rstrip("0")


def _normalize(text: str) -> str:
    """Minúsculas + sin acentos/tildes."""
    text = text.lower()
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def _texto_qr(prod: dict) -> str:
    """Arma el texto completo para el QR de un producto."""
    lines = [
        f"Producto: {prod['nombre']}",
        f"SKU: {prod.get('sku', '-')}",
        f"Medidas: {_fmt_num(prod['largo'])} x {_fmt_num(prod['ancho'])} x {_fmt_num(prod['alto'])} cm",
        f"Color: {prod['color']}",
        f"Precio FOB: US$ {_fmt_num(prod['precio_fob'])}",
    ]
    notas = prod.get("notas", "")
    if notas:
        lines.append(f"Notas: {notas}")
    etiquetas = prod.get("etiquetas", "")
    if etiquetas:
        lines.append(f"Etiquetas: {etiquetas}")
    return "\n".join(lines)


def _generar_qr_bytes(texto: str) -> bytes:
    """Genera una imagen QR en PNG como bytes."""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(texto)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class MainView(tk.Frame):
    """Vista CRUD de productos."""

    def __init__(self, master: tk.Widget, **kwargs):
        super().__init__(master, bg=theme.BG_PRIMARY, **kwargs)
        self._editing_id: int | None = None
        self._checked: set[int] = set()  # IDs de productos seleccionados con check
        self._build()
        self._refresh_tree()

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build(self) -> None:
        # ── Header ─────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=theme.BG_PRIMARY)
        header.pack(fill="x", padx=20, pady=(20, 8))

        tk.Label(header, text="Gestor Productos", font=theme.FONT_TITLE,
                 bg=theme.BG_PRIMARY, fg=theme.TEXT_PRIMARY).pack(side="left")

        self._count_label = tk.Label(
            header, text="0 productos", font=theme.FONT_SMALL,
            bg=theme.BG_PRIMARY, fg=theme.COUNT_LABEL_COLOR)
        self._count_label.pack(side="right")

        # ── Filtros de búsqueda ───────────────────────────────────────────
        filter_card = tk.Frame(self, bg=theme.BG_CARD, bd=1, relief="solid",
                               highlightbackground=theme.ACCENT, highlightthickness=2)
        filter_card.pack(fill="x", padx=20, pady=(0, 8))

        # Campo Buscar (ícono lupa dibujado con PIL)
        self._search_icon = self._make_icon(16, theme.ACCENT, self._draw_search)
        tk.Label(filter_card, image=self._search_icon,
                 bg=theme.BG_CARD).pack(side="left", padx=(10, 2), pady=6)
        tk.Label(filter_card, text="Buscar:", font=theme.FONT_BOLD,
                 bg=theme.BG_CARD, fg=theme.ACCENT
                 ).pack(side="left", padx=(0, 4), pady=6)

        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._refresh_tree())
        self._buscar_entry = tk.Entry(
            filter_card, textvariable=self._filter_var,
            font=theme.FONT_NORMAL, bg=theme.BG_INPUT,
            fg=theme.TEXT_PRIMARY, relief="flat", bd=1,
            highlightbackground=theme.BORDER, highlightthickness=1, width=25)
        self._buscar_entry.pack(side="left", padx=(0, 12), pady=6)

        # Campo Excluir (ícono X dibujado con PIL)
        self._exclude_icon = self._make_icon(14, theme.BTN_DANGER, self._draw_exclude)
        tk.Label(filter_card, image=self._exclude_icon,
                 bg=theme.BG_CARD).pack(side="left", padx=(0, 2), pady=6)
        tk.Label(filter_card, text="Excluir:", font=theme.FONT_BOLD,
                 bg=theme.BG_CARD, fg=theme.BTN_DANGER
                 ).pack(side="left", padx=(0, 4), pady=6)

        self._excluir_var = tk.StringVar()
        self._excluir_var.trace_add("write", lambda *_: self._refresh_tree())
        self._excluir_entry = tk.Entry(
            filter_card, textvariable=self._excluir_var,
            font=theme.FONT_NORMAL, bg=theme.BG_INPUT,
            fg=theme.TEXT_PRIMARY, relief="flat", bd=1,
            highlightbackground=theme.BORDER, highlightthickness=1, width=25)
        self._excluir_entry.pack(side="left", padx=(0, 10), pady=6)

        # Placeholders
        self._setup_placeholder(self._buscar_entry, self._filter_var, "Filtrar por texto...")
        self._setup_placeholder(self._excluir_entry, self._excluir_var, "Palabras a excluir...")

        # Botón limpiar
        def _limpiar_filtros():
            self._filter_var.set("")
            self._excluir_var.set("")
            # Restaurar placeholders
            self._buscar_entry.configure(fg=theme.TEXT_MUTED)
            self._buscar_entry.delete(0, "end")
            self._buscar_entry.insert(0, "Filtrar por texto...")
            self._excluir_entry.configure(fg=theme.TEXT_MUTED)
            self._excluir_entry.delete(0, "end")
            self._excluir_entry.insert(0, "Palabras a excluir...")

        tk.Button(filter_card, text="Limpiar", font=theme.FONT_SMALL,
                  bg=theme.BG_SECONDARY, fg=theme.TEXT_SECONDARY, relief="flat",
                  bd=0, padx=8, pady=2, cursor="hand2",
                  command=_limpiar_filtros
                  ).pack(side="left", padx=(0, 8), pady=6)

        # ── Formulario ────────────────────────────────────────────────────
        form_card = tk.Frame(self, bg=theme.BG_CARD, bd=1, relief="solid",
                             highlightbackground=theme.BORDER, highlightthickness=1)
        form_card.pack(fill="x", padx=20, pady=(0, 8))

        self._form_title = tk.Label(form_card, text="Nuevo Producto",
                                    font=theme.FONT_BOLD, bg=theme.BG_CARD,
                                    fg=theme.ACCENT)
        self._form_title.pack(anchor="w", padx=12, pady=(8, 4))

        fields_frame = tk.Frame(form_card, bg=theme.BG_CARD)
        fields_frame.pack(fill="x", padx=12, pady=(0, 4))

        # Crear íconos del formulario
        ic = theme.TEXT_SECONDARY
        self._icon_tag = self._make_icon(14, ic, self._draw_tag)
        self._icon_ruler = self._make_icon(14, ic, self._draw_ruler)
        self._icon_palette = self._make_icon(14, ic, self._draw_palette)
        self._icon_dollar = self._make_icon(14, ic, self._draw_dollar)
        self._icon_pencil = self._make_icon(14, ic, self._draw_pencil)

        # Row 1: Nombre
        row1 = tk.Frame(fields_frame, bg=theme.BG_CARD)
        row1.pack(fill="x", pady=2)

        tk.Label(row1, image=self._icon_tag,
                 bg=theme.BG_CARD).pack(side="left", padx=(0, 2))
        tk.Label(row1, text="Nombre:", font=theme.FONT_NORMAL,
                 bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, anchor="e"
                 ).pack(side="left", padx=(0, 4))
        self._nombre_var = tk.StringVar()
        tk.Entry(row1, textvariable=self._nombre_var, font=theme.FONT_NORMAL,
                 bg=theme.BG_INPUT, fg=theme.TEXT_PRIMARY, relief="flat", bd=1,
                 highlightbackground=theme.BORDER, highlightthickness=1
                 ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        # Row 2: Medidas
        row2 = tk.Frame(fields_frame, bg=theme.BG_CARD)
        row2.pack(fill="x", pady=2)

        tk.Label(row2, image=self._icon_ruler,
                 bg=theme.BG_CARD).pack(side="left", padx=(0, 2))
        tk.Label(row2, text="Largo:", font=theme.FONT_NORMAL,
                 bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, anchor="e"
                 ).pack(side="left", padx=(0, 4))
        self._largo_var = tk.StringVar(value="0")
        tk.Entry(row2, textvariable=self._largo_var, font=theme.FONT_NORMAL,
                 bg=theme.BG_INPUT, fg=theme.TEXT_PRIMARY, relief="flat", bd=1,
                 highlightbackground=theme.BORDER, highlightthickness=1, width=8
                 ).pack(side="left", padx=(0, 8))

        tk.Label(row2, text="Ancho:", font=theme.FONT_NORMAL,
                 bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY
                 ).pack(side="left", padx=(0, 4))
        self._ancho_var = tk.StringVar(value="0")
        tk.Entry(row2, textvariable=self._ancho_var, font=theme.FONT_NORMAL,
                 bg=theme.BG_INPUT, fg=theme.TEXT_PRIMARY, relief="flat", bd=1,
                 highlightbackground=theme.BORDER, highlightthickness=1, width=8
                 ).pack(side="left", padx=(0, 8))

        tk.Label(row2, text="Alto:", font=theme.FONT_NORMAL,
                 bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY
                 ).pack(side="left", padx=(0, 4))
        self._alto_var = tk.StringVar(value="0")
        tk.Entry(row2, textvariable=self._alto_var, font=theme.FONT_NORMAL,
                 bg=theme.BG_INPUT, fg=theme.TEXT_PRIMARY, relief="flat", bd=1,
                 highlightbackground=theme.BORDER, highlightthickness=1, width=8
                 ).pack(side="left", padx=(0, 8))

        # Row 3: Color + Precio FOB
        row3 = tk.Frame(fields_frame, bg=theme.BG_CARD)
        row3.pack(fill="x", pady=2)

        tk.Label(row3, image=self._icon_palette,
                 bg=theme.BG_CARD).pack(side="left", padx=(0, 2))
        tk.Label(row3, text="Color:", font=theme.FONT_NORMAL,
                 bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, anchor="e"
                 ).pack(side="left", padx=(0, 4))
        self._color_var = tk.StringVar(value=COLORES[0])
        color_combo = ttk.Combobox(row3, textvariable=self._color_var,
                                   values=COLORES, state="readonly",
                                   font=theme.FONT_NORMAL, width=12)
        color_combo.pack(side="left", padx=(0, 8))

        tk.Label(row3, image=self._icon_dollar,
                 bg=theme.BG_CARD).pack(side="left", padx=(4, 2))
        tk.Label(row3, text="Precio FOB:", font=theme.FONT_NORMAL,
                 bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY
                 ).pack(side="left", padx=(0, 4))
        self._precio_var = tk.StringVar(value="0")
        tk.Entry(row3, textvariable=self._precio_var, font=theme.FONT_NORMAL,
                 bg=theme.BG_INPUT, fg=theme.TEXT_PRIMARY, relief="flat", bd=1,
                 highlightbackground=theme.BORDER, highlightthickness=1, width=10
                 ).pack(side="left", padx=(0, 8))

        # Row 4: Notas
        row4 = tk.Frame(fields_frame, bg=theme.BG_CARD)
        row4.pack(fill="x", pady=2)

        tk.Label(row4, image=self._icon_pencil,
                 bg=theme.BG_CARD).pack(side="left", padx=(0, 2))
        tk.Label(row4, text="Notas:", font=theme.FONT_NORMAL,
                 bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, anchor="e"
                 ).pack(side="left", padx=(0, 4), anchor="n")
        self._notas_var = tk.StringVar()
        tk.Entry(row4, textvariable=self._notas_var, font=theme.FONT_NORMAL,
                 bg=theme.BG_INPUT, fg=theme.TEXT_PRIMARY, relief="flat", bd=1,
                 highlightbackground=theme.BORDER, highlightthickness=1
                 ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        # Row 5: Etiquetas
        row5 = tk.Frame(fields_frame, bg=theme.BG_CARD)
        row5.pack(fill="x", pady=2)

        tk.Label(row5, image=self._icon_tag,
                 bg=theme.BG_CARD).pack(side="left", padx=(0, 2))
        tk.Label(row5, text="Etiquetas:", font=theme.FONT_NORMAL,
                 bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, anchor="e"
                 ).pack(side="left", padx=(0, 4))
        self._etiquetas_var = tk.StringVar()
        tk.Entry(row5, textvariable=self._etiquetas_var, font=theme.FONT_NORMAL,
                 bg=theme.BG_INPUT, fg=theme.TEXT_PRIMARY, relief="flat", bd=1,
                 highlightbackground=theme.BORDER, highlightthickness=1
                 ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        # Botones del formulario
        btn_frame = tk.Frame(form_card, bg=theme.BG_CARD)
        btn_frame.pack(fill="x", padx=12, pady=(4, 8))

        self._btn_save = tk.Button(
            btn_frame, text="Agregar", font=theme.FONT_BOLD,
            bg=theme.BTN_SUCCESS, fg="white", relief="flat", bd=0,
            padx=14, pady=4, cursor="hand2", command=self._on_save)
        self._btn_save.pack(side="left", padx=(0, 6))

        self._btn_cancel = tk.Button(
            btn_frame, text="Cancelar", font=theme.FONT_BOLD,
            bg=theme.BG_SECONDARY, fg=theme.TEXT_SECONDARY, relief="flat", bd=0,
            padx=14, pady=4, cursor="hand2", command=self._clear_form)
        self._btn_cancel.pack(side="left")

        # Enter en cualquier campo del formulario → agregar/guardar
        for w in (row1, row2, row3, row4, row5):
            for child in w.winfo_children():
                if isinstance(child, tk.Entry):
                    child.bind("<Return>", lambda e: self._on_save())
                    child.bind("<KP_Enter>", lambda e: self._on_save())

        # ── Treeview ───────────────────────────────────────────────────────
        tree_frame = tk.Frame(self, bg=theme.BG_PRIMARY)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        self._tree = ttk.Treeview(tree_frame, columns=COLUMNS, show="headings",
                                  selectmode="browse")
        for col, hdr, width in zip(COLUMNS, COL_HEADERS, COL_WIDTHS):
            if col == "check":
                self._tree.heading(col, text=hdr, command=self._on_toggle_all_checks)
            else:
                self._tree.heading(col, text=hdr)
            if col == "check":
                self._tree.column(col, width=width, minwidth=35, anchor="center",
                                  stretch=False)
            elif col == "notas":
                self._tree.column(col, width=0, minwidth=0, stretch=False)
            elif col == "etiquetas":
                self._tree.column(col, width=width, minwidth=50, anchor="w")
            else:
                anchor = "e" if col in ("largo", "ancho", "alto", "precio_fob", "id") else "w"
                self._tree.column(col, width=width, minwidth=40, anchor=anchor)

        self._tree.tag_configure("even", background=theme.TAG_EVEN)
        self._tree.tag_configure("odd", background=theme.TAG_ODD)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._tree.bind("<Double-1>", lambda e: self._on_show_detail())
        self._tree.bind("<Return>", lambda e: self._on_edit_selected())
        self._tree.bind("<Delete>", lambda e: self._on_delete())
        self._tree.bind("<Button-1>", self._on_tree_click)
        self._tree.bind("<Button-3>", self._on_right_click)

        # ── Botones de acción ──────────────────────────────────────────────
        action_bar = tk.Frame(self, bg=theme.BG_PRIMARY)
        action_bar.pack(fill="x", padx=20, pady=(0, 4))

        tk.Button(action_bar, text="✅ Seleccionar todo", font=theme.FONT_BOLD,
                  bg="#607D8B", fg="white", relief="flat", bd=0,
                  padx=14, pady=4, cursor="hand2",
                  command=self._on_select_all).pack(side="left", padx=(0, 6))

        tk.Button(action_bar, text="❌ Deseleccionar", font=theme.FONT_BOLD,
                  bg="#607D8B", fg="white", relief="flat", bd=0,
                  padx=14, pady=4, cursor="hand2",
                  command=self._on_deselect_all).pack(side="left", padx=(0, 6))

        tk.Button(action_bar, text="📄 Generar PDF con QR", font=theme.FONT_BOLD,
                  bg="#9C27B0", fg="white", relief="flat", bd=0,
                  padx=14, pady=4, cursor="hand2",
                  command=self._on_generar_pdf).pack(side="left", padx=(0, 6))

        tk.Button(action_bar, text="Editar", font=theme.FONT_BOLD,
                  bg=theme.BTN_INFO, fg="white", relief="flat", bd=0,
                  padx=14, pady=4, cursor="hand2",
                  command=self._on_edit_selected).pack(side="right", padx=(6, 0))

        tk.Button(action_bar, text="Eliminar", font=theme.FONT_BOLD,
                  bg=theme.BTN_DANGER, fg="white", relief="flat", bd=0,
                  padx=14, pady=4, cursor="hand2",
                  command=self._on_delete).pack(side="right", padx=(0, 6))


    # ══════════════════════════════════════════════════════════════════════════
    # PLACEHOLDERS Y FILTROS
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _make_icon(size: int, color: str, draw_func) -> ImageTk.PhotoImage:
        """Crea un ícono dibujado con PIL."""
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw_func(draw, size, color)
        return ImageTk.PhotoImage(img)

    @staticmethod
    def _draw_search(draw, s, color):
        """Lupa: círculo + mango."""
        r = s * 0.35
        cx, cy = s * 0.38, s * 0.38
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=2)
        draw.line([cx + r * 0.7, cy + r * 0.7, s - 1, s - 1], fill=color, width=2)

    @staticmethod
    def _draw_exclude(draw, s, color):
        """X de excluir."""
        m = s * 0.2
        draw.line([m, m, s - m, s - m], fill=color, width=2)
        draw.line([s - m, m, m, s - m], fill=color, width=2)

    @staticmethod
    def _draw_tag(draw, s, color):
        """Etiqueta/tag para Nombre."""
        m = s * 0.15
        # Rectángulo redondeado (simplificado)
        draw.rounded_rectangle([m, m + s * 0.15, s - m, s - m - s * 0.15],
                               radius=3, outline=color, width=2)
        # Líneas internas (texto simulado)
        draw.line([m + s * 0.2, s * 0.42, s - m - s * 0.2, s * 0.42], fill=color, width=1)
        draw.line([m + s * 0.2, s * 0.58, s * 0.6, s * 0.58], fill=color, width=1)

    @staticmethod
    def _draw_ruler(draw, s, color):
        """Regla para medidas."""
        m = s * 0.1
        # Regla horizontal
        y_top = s * 0.35
        y_bot = s * 0.65
        draw.rectangle([m, y_top, s - m, y_bot], outline=color, width=2)
        # Marcas de la regla
        for i in range(1, 5):
            x = m + (s - 2 * m) * i / 5
            tick_h = s * 0.12 if i % 2 == 0 else s * 0.08
            draw.line([x, y_top, x, y_top + tick_h], fill=color, width=1)

    @staticmethod
    def _draw_palette(draw, s, color):
        """Paleta/gota de color."""
        cx = s * 0.5
        # Gota
        draw.ellipse([s * 0.2, s * 0.35, s * 0.8, s * 0.85], outline=color, width=2)
        draw.polygon([(cx, s * 0.1), (s * 0.3, s * 0.5), (s * 0.7, s * 0.5)],
                     outline=color)

    @staticmethod
    def _draw_dollar(draw, s, color):
        """Billete: rectángulo con círculo adentro."""
        m = s * 0.05
        # Rectángulo del billete
        draw.rounded_rectangle([m, s * 0.2, s - m, s * 0.8], radius=2,
                               outline=color, width=2)
        # Círculo central (medallón)
        cx, cy = s * 0.5, s * 0.5
        r = s * 0.15
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=1)
        # Línea horizontal decorativa izquierda y derecha
        draw.line([m + s * 0.08, cy, cx - r - s * 0.05, cy], fill=color, width=1)
        draw.line([cx + r + s * 0.05, cy, s - m - s * 0.08, cy], fill=color, width=1)

    @staticmethod
    def _draw_pencil(draw, s, color):
        """Lápiz para notas."""
        m = s * 0.15
        # Cuerpo del lápiz (línea diagonal)
        draw.line([s - m, m, m, s - m], fill=color, width=2)
        # Punta
        draw.line([m, s - m, m + s * 0.12, s - m - s * 0.05], fill=color, width=2)
        draw.line([m, s - m, m + s * 0.05, s - m - s * 0.12], fill=color, width=2)
        # Borrador (rayita arriba)
        draw.line([s - m - s * 0.12, m + s * 0.12,
                   s - m + s * 0.02, m - s * 0.02], fill=color, width=2)

    def _setup_placeholder(self, entry: tk.Entry, var: tk.StringVar,
                           placeholder: str) -> None:
        """Placeholder text gris que desaparece al hacer focus."""
        def _on_focus_in(e):
            if entry.get() == placeholder:
                entry.delete(0, "end")
                entry.configure(fg=theme.TEXT_PRIMARY)

        def _on_focus_out(e):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.configure(fg=theme.TEXT_MUTED)

        entry.insert(0, placeholder)
        entry.configure(fg=theme.TEXT_MUTED)
        entry.bind("<FocusIn>", _on_focus_in)
        entry.bind("<FocusOut>", _on_focus_out)

    def _get_filter_text(self, var: tk.StringVar, placeholder: str) -> str:
        """Obtiene el texto del filtro ignorando el placeholder."""
        val = var.get()
        return "" if val == placeholder else val

    # ══════════════════════════════════════════════════════════════════════════
    # MENÚ CONTEXTUAL (CLICK DERECHO)
    # ══════════════════════════════════════════════════════════════════════════

    def _on_right_click(self, event) -> None:
        """Muestra menú contextual con opciones de copiar."""
        item = self._tree.identify_row(event.y)
        if not item:
            return
        self._tree.selection_set(item)
        # values: (check, id, sku, nombre, largo, ancho, alto, color, precio_fob, notas, etiquetas)
        values = self._tree.item(item, "values")
        nombre = values[3]
        sku = values[2]
        largo = values[4]
        ancho = values[5]
        alto = values[6]
        precio_fob = values[8] if len(values) > 8 else ""
        notas = values[9] if len(values) > 9 else ""
        etiquetas = values[10] if len(values) > 10 else ""

        if hasattr(self, "_ctx_menu"):
            self._ctx_menu.destroy()
        menu = tk.Menu(self, tearoff=0)
        self._ctx_menu = menu
        menu.add_command(label=f"📋 Copiar SKU: {sku}",
                         command=lambda: self._copiar(sku))
        menu.add_command(label=f"📋 Copiar Título: {nombre}",
                         command=lambda: self._copiar(nombre))
        if notas:
            nota_preview = notas if len(notas) <= 40 else notas[:40] + "..."
            menu.add_command(label=f"📋 Copiar Nota: {nota_preview}",
                             command=lambda: self._copiar(notas))
        menu.add_command(label=f"📋 Copiar Largo: {largo}",
                         command=lambda: self._copiar(largo))
        menu.add_command(label=f"📋 Copiar Ancho: {ancho}",
                         command=lambda: self._copiar(ancho))
        menu.add_command(label=f"📋 Copiar Alto: {alto}",
                         command=lambda: self._copiar(alto))
        menu.add_command(
            label=f"📋 Copiar Medidas completas",
            command=lambda: self._copiar(
                f"Las medidas de {nombre} son: {largo} cm de largo, "
                f"{ancho} cm de ancho y {alto} cm de alto"))
        menu.add_command(
            label=f"📋 Copiar FOB amigo: {precio_fob}",
            command=lambda: self._copiar(precio_fob))
        menu.add_separator()
        if etiquetas:
            etiq_preview = etiquetas if len(etiquetas) <= 40 else etiquetas[:40] + "..."
            menu.add_command(label=f"📋 Copiar Etiquetas: {etiq_preview}",
                             command=lambda: self._copiar(etiquetas))
        menu.add_command(label="📋 Copiar todo",
                         command=lambda: self._copiar(
                             f"{nombre}\nSKU: {sku}\n"
                             f"Medidas: {largo} x {ancho} x {alto} cm"
                             + (f"\nNotas: {notas}" if notas else "")
                             + (f"\nEtiquetas: {etiquetas}" if etiquetas else "")))
        menu.add_separator()
        id_ = int(values[1])
        menu.add_command(label=f"🗑 Eliminar '{nombre}'",
                         command=lambda: self._on_delete_by_id(id_, nombre))

        menu.tk_popup(event.x_root, event.y_root)

    def _copiar(self, texto: str) -> None:
        """Copia texto al portapapeles."""
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.update()
        try:
            subprocess.run(
                ["clip.exe"], input=texto.encode("utf-16-le"),
                check=False, timeout=2,
            )
        except FileNotFoundError:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # CHECKBOX / SELECCIÓN
    # ══════════════════════════════════════════════════════════════════════════

    def _on_tree_click(self, event) -> None:
        """Toggle check cuando se clickea la columna ✓."""
        region = self._tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self._tree.identify_column(event.x)
        if col != "#1":  # Columna "check" es la primera
            return
        item = self._tree.identify_row(event.y)
        if not item:
            return
        values = list(self._tree.item(item, "values"))
        prod_id = int(values[1])  # ID está en posición 1
        if prod_id in self._checked:
            self._checked.discard(prod_id)
            values[0] = "☐"
        else:
            self._checked.add(prod_id)
            values[0] = "☑"
        self._tree.item(item, values=values)

    def _on_toggle_all_checks(self) -> None:
        """Click en heading ✓: si hay alguno sin check → seleccionar todos, sino deseleccionar todos."""
        all_checked = all(
            int(self._tree.item(item, "values")[1]) in self._checked
            for item in self._tree.get_children()
        ) if self._tree.get_children() else False

        if all_checked:
            self._on_deselect_all()
        else:
            self._on_select_all()

    def _on_select_all(self) -> None:
        for item in self._tree.get_children():
            values = list(self._tree.item(item, "values"))
            prod_id = int(values[1])
            self._checked.add(prod_id)
            values[0] = "☑"
            self._tree.item(item, values=values)

    def _on_deselect_all(self) -> None:
        self._checked.clear()
        for item in self._tree.get_children():
            values = list(self._tree.item(item, "values"))
            values[0] = "☐"
            self._tree.item(item, values=values)

    # ══════════════════════════════════════════════════════════════════════════
    # PDF CON QR
    # ══════════════════════════════════════════════════════════════════════════

    def _on_generar_pdf(self) -> None:
        if not self._checked:
            messagebox.showinfo("Sin selección",
                                "Seleccioná al menos un producto con el check ✓")
            return

        productos = db.listar()
        seleccionados = [p for p in productos if p["id"] in self._checked]

        if not seleccionados:
            messagebox.showwarning("Error", "No se encontraron los productos seleccionados.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Guardar PDF con QR",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="productos_qr.pdf")
        if not filepath:
            return

        try:
            self._generar_pdf(seleccionados, filepath)
            messagebox.showinfo("PDF generado", f"Se guardó en:\n{filepath}")
        except Exception as e:
            logger.exception("Error generando PDF")
            messagebox.showerror("Error", f"No se pudo generar el PDF:\n{e}")

    def _generar_pdf(self, productos: list[dict], filepath: str) -> None:
        """Genera PDF con título, SKU y QR de cada producto."""
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)

        # Fuente por defecto (Helvetica soporta caracteres latinos)
        for prod in productos:
            pdf.add_page()

            # Título del producto (multi_cell para que no se corte)
            pdf.set_font("Helvetica", "B", 22)
            pdf.multi_cell(0, 12, prod["nombre"], new_x="LMARGIN", new_y="NEXT", align="C")

            pdf.ln(5)

            # SKU
            pdf.set_font("Helvetica", "", 14)
            sku_text = f"SKU: {prod['sku']}" if prod.get("sku") else "SKU: -"
            pdf.cell(0, 10, sku_text, new_x="LMARGIN", new_y="NEXT", align="C")

            # Medidas
            pdf.set_font("Helvetica", "", 11)
            medidas = (f"Medidas: {_fmt_num(prod['largo'])} x "
                       f"{_fmt_num(prod['ancho'])} x {_fmt_num(prod['alto'])} cm")
            pdf.cell(0, 8, medidas, new_x="LMARGIN", new_y="NEXT", align="C")

            # Color y precio
            pdf.cell(0, 8, f"Color: {prod['color']}  |  Precio FOB: US$ {_fmt_num(prod['precio_fob'])}",
                     new_x="LMARGIN", new_y="NEXT", align="C")

            # Notas (fuente más grande, bold itálica, multi_cell para wrap)
            notas = prod.get("notas", "")
            if notas:
                pdf.ln(4)
                pdf.set_font("Helvetica", "BI", 13)
                pdf.multi_cell(0, 8, f"Notas: {notas}", new_x="LMARGIN", new_y="NEXT", align="C")

            # Etiquetas
            etiquetas = prod.get("etiquetas", "")
            if etiquetas:
                pdf.ln(2)
                pdf.set_font("Helvetica", "I", 11)
                pdf.multi_cell(0, 7, f"Etiquetas: {etiquetas}", new_x="LMARGIN", new_y="NEXT", align="C")

            pdf.ln(10)

            # QR con info completa del producto
            qr_bytes = _generar_qr_bytes(_texto_qr(prod))

            # Guardar QR temporal y agregarlo al PDF
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(qr_bytes)
                tmp_path = tmp.name

            # Centrar el QR (150x150 px en el PDF)
            qr_size = 80
            x = (pdf.w - qr_size) / 2
            pdf.image(tmp_path, x=x, w=qr_size, h=qr_size)

            # Limpiar archivo temporal
            Path(tmp_path).unlink(missing_ok=True)

            pdf.ln(5)
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 8, "Escaneá el QR para ver el nombre del producto",
                     new_x="LMARGIN", new_y="NEXT", align="C")

        pdf.output(filepath)

    # ══════════════════════════════════════════════════════════════════════════
    # CRUD
    # ══════════════════════════════════════════════════════════════════════════

    def _get_form_values(self) -> dict | None:
        nombre = self._nombre_var.get().strip()
        if not nombre:
            messagebox.showwarning("Campo requerido", "El nombre es obligatorio.")
            return None
        try:
            largo = float(self._largo_var.get() or 0)
            ancho = float(self._ancho_var.get() or 0)
            alto = float(self._alto_var.get() or 0)
            precio_fob = float(self._precio_var.get() or 0)
        except ValueError:
            messagebox.showwarning("Error", "Largo, ancho, alto y precio deben ser números.")
            return None
        color = self._color_var.get()
        notas = self._notas_var.get().strip()
        etiquetas = self._etiquetas_var.get().strip()
        return dict(nombre=nombre, largo=largo, ancho=ancho, alto=alto,
                    color=color, precio_fob=precio_fob, notas=notas,
                    etiquetas=etiquetas)

    def _on_save(self) -> None:
        vals = self._get_form_values()
        if not vals:
            return

        if self._editing_id is not None:
            db.actualizar(self._editing_id, **vals)
            self._editing_id = None
            self._form_title.configure(text="Nuevo Producto")
            self._btn_save.configure(text="Agregar", bg=theme.BTN_SUCCESS)
        else:
            new_id = db.agregar(**vals)

        self._clear_form()
        self._refresh_tree()

    def _on_edit_selected(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Selección", "Seleccioná un producto para editar.")
            return
        values = self._tree.item(sel[0], "values")
        # values: (check, id, sku, nombre, largo, ancho, alto, color, precio_fob, notas, etiquetas)
        self._editing_id = int(values[1])
        self._nombre_var.set(values[3])
        self._largo_var.set(values[4])
        self._ancho_var.set(values[5])
        self._alto_var.set(values[6])
        self._color_var.set(values[7])
        self._precio_var.set(values[8])
        self._notas_var.set(values[9] if len(values) > 9 else "")
        self._etiquetas_var.set(values[10] if len(values) > 10 else "")
        self._form_title.configure(text=f"Editando Producto #{self._editing_id}")
        self._btn_save.configure(text="Guardar", bg=theme.BTN_WARNING)

    def _on_delete(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Selección", "Seleccioná un producto para eliminar.")
            return
        values = self._tree.item(sel[0], "values")
        self._on_delete_by_id(int(values[1]), values[3])

    def _on_delete_by_id(self, id_: int, nombre: str) -> None:
        if not messagebox.askyesno("Confirmar", f"¿Eliminar '{nombre}' (#{id_})?"):
            return
        db.eliminar(id_)
        self._checked.discard(id_)
        if self._editing_id == id_:
            self._clear_form()
        self._refresh_tree()

    def _on_show_detail(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0], "values")
        # Armar dict para el detalle y el QR
        prod = dict(
            id=values[1], sku=values[2], nombre=values[3],
            largo=values[4], ancho=values[5], alto=values[6],
            color=values[7], precio_fob=values[8],
            notas=values[9] if len(values) > 9 else "",
            etiquetas=values[10] if len(values) > 10 else "")
        _DetailWindow(self.winfo_toplevel(), prod, on_edit=self._on_edit_selected)

    def _clear_form(self) -> None:
        self._editing_id = None
        self._nombre_var.set("")
        self._largo_var.set("0")
        self._ancho_var.set("0")
        self._alto_var.set("0")
        self._color_var.set(COLORES[0])
        self._precio_var.set("0")
        self._notas_var.set("")
        self._etiquetas_var.set("")
        self._form_title.configure(text="Nuevo Producto")
        self._btn_save.configure(text="Agregar", bg=theme.BTN_SUCCESS)

    def _refresh_tree(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)

        buscar_raw = self._get_filter_text(self._filter_var, "Filtrar por texto...")
        excluir_raw = self._get_filter_text(self._excluir_var, "Palabras a excluir...")

        buscar_words = [_normalize(w) for w in buscar_raw.split() if w.strip()]
        excluir_words = [_normalize(w) for w in excluir_raw.split() if w.strip()]

        todos = db.listar()
        shown = 0
        for p in todos:
            # Texto completo de la fila para filtrar
            row_text = _normalize(
                f"{p['nombre']} {p.get('sku', '')} {p['color']} "
                f"{p.get('notas', '')} {p.get('etiquetas', '')}")

            # Filtro de inclusión: todas las palabras deben estar presentes
            if buscar_words and not all(w in row_text for w in buscar_words):
                continue
            # Filtro de exclusión: excluye si TODAS las palabras están presentes
            if excluir_words and all(w in row_text for w in excluir_words):
                continue

            tag = "even" if shown % 2 == 0 else "odd"
            check = "☑" if p["id"] in self._checked else "☐"
            self._tree.insert("", "end", values=(
                check, p["id"], p.get("sku", "-"), p["nombre"],
                _fmt_num(p["largo"]), _fmt_num(p["ancho"]),
                _fmt_num(p["alto"]), p["color"], _fmt_num(p["precio_fob"]),
                p.get("notas", ""), p.get("etiquetas", "")),
                tags=(tag,))
            shown += 1

        total = len(todos)
        if shown == total:
            self._count_label.configure(text=f"{total} producto{'s' if total != 1 else ''}")
        else:
            self._count_label.configure(text=f"Mostrando {shown} de {total}")


class _DetailWindow(tk.Toplevel):
    """Ventana de detalle de producto."""

    def __init__(self, master: tk.Widget, prod: dict, on_edit=None):
        super().__init__(master)
        self._on_edit = on_edit
        self.title(f"Producto — {prod['nombre']}")
        self.configure(bg=theme.BG_PRIMARY)
        self.resizable(False, False)
        self.transient(master)

        id_ = prod["id"]
        sku = prod.get("sku", "-")
        nombre = prod["nombre"]
        largo = prod["largo"]
        ancho = prod["ancho"]
        alto = prod["alto"]
        color = prod["color"]
        precio = prod["precio_fob"]
        notas = prod.get("notas", "")
        etiquetas = prod.get("etiquetas", "")

        # ── Contenedor principal ───────────────────────────────────────────
        container = tk.Frame(self, bg=theme.BG_PRIMARY)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # ── Nombre grande ──────────────────────────────────────────────────
        tk.Label(container, text=nombre, font=(theme.FONT_FAMILY, 22, "bold"),
                 bg=theme.BG_PRIMARY, fg=theme.TEXT_PRIMARY,
                 wraplength=420, justify="left").pack(anchor="w", pady=(0, 4))

        info_line = f"ID: {id_}  •  SKU: {sku}"
        tk.Label(container, text=info_line, font=theme.FONT_SMALL,
                 bg=theme.BG_PRIMARY, fg=theme.TEXT_MUTED
                 ).pack(anchor="w")

        # ── Separador ─────────────────────────────────────────────────────
        ttk.Separator(container, orient="horizontal").pack(fill="x", pady=12)

        # ── Card de info ──────────────────────────────────────────────────
        card = tk.Frame(container, bg=theme.BG_CARD, bd=1, relief="solid",
                        highlightbackground=theme.BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 12))

        fields = [
            ("Medidas", f"{largo}  x  {ancho}  x  {alto}"),
            ("Color", color),
            ("Precio FOB", f"US$ {precio}"),
        ]
        if notas:
            fields.append(("Notas", notas))
        if etiquetas:
            fields.append(("Etiquetas", etiquetas))

        for i, (label, value) in enumerate(fields):
            row = tk.Frame(card, bg=theme.BG_CARD)
            row.pack(fill="x", padx=16, pady=(12 if i == 0 else 6, 12 if i == len(fields) - 1 else 0))

            tk.Label(row, text=label, font=theme.FONT_SMALL,
                     bg=theme.BG_CARD, fg=theme.TEXT_MUTED, width=12, anchor="w"
                     ).pack(side="left")

            fnt = (theme.FONT_FAMILY, 16, "bold") if label == "Precio FOB" else (theme.FONT_FAMILY, 14)
            fg = theme.ACCENT if label == "Precio FOB" else theme.TEXT_PRIMARY
            tk.Label(row, text=value, font=fnt,
                     bg=theme.BG_CARD, fg=fg).pack(side="left", padx=(8, 0))

        # ── QR ───────────────────────────────────────────────────────────
        qr_bytes = _generar_qr_bytes(_texto_qr(prod))
        from PIL import Image, ImageTk
        qr_img = Image.open(io.BytesIO(qr_bytes))
        qr_img = qr_img.resize((150, 150), Image.LANCZOS)
        self._qr_photo = ImageTk.PhotoImage(qr_img)
        tk.Label(container, image=self._qr_photo, bg=theme.BG_PRIMARY
                 ).pack(pady=(0, 4))
        tk.Label(container, text="📱 Escaneá el QR para ver el producto",
                 font=theme.FONT_SMALL, bg=theme.BG_PRIMARY, fg=theme.TEXT_MUTED
                 ).pack()

        # ── Botones ──────────────────────────────────────────────────────
        btn_row = tk.Frame(container, bg=theme.BG_PRIMARY)
        btn_row.pack(pady=(8, 0))

        tk.Button(btn_row, text="Editar", font=theme.FONT_BOLD,
                  bg=theme.BTN_WARNING, fg="white", relief="flat", bd=0,
                  padx=20, pady=6, cursor="hand2",
                  command=self._do_edit).pack(side="left", padx=(0, 8))

        tk.Button(btn_row, text="Cerrar", font=theme.FONT_BOLD,
                  bg=theme.BTN_INFO, fg="white", relief="flat", bd=0,
                  padx=20, pady=6, cursor="hand2",
                  command=self.destroy).pack(side="left")

        self.bind("<Escape>", lambda e: self.destroy())

        # Forzar layout antes de mostrar
        self.update_idletasks()
        # Centrar sobre la ventana padre
        pw = master.winfo_width()
        ph = master.winfo_height()
        px = master.winfo_x()
        py = master.winfo_y()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")
        self.grab_set()
        self.focus_set()

    def _do_edit(self) -> None:
        self.destroy()
        if self._on_edit:
            self._on_edit()
