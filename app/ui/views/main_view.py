"""Vista principal CRUD de Gestor Productos."""

import io
import logging
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

import qrcode
from fpdf import FPDF

from app.ui import theme
from app.ui.components.log_panel import LogPanel
from app import db

logger = logging.getLogger(__name__)

COLORES = ("Blanco", "Negro", "Rosa", "Verde", "Violeta")
COLUMNS = ("check", "id", "sku", "nombre", "largo", "ancho", "alto", "color", "precio_fob", "notas")
COL_HEADERS = ("✓", "ID", "SKU", "Nombre", "Largo", "Ancho", "Alto", "Color", "Precio FOB", "Notas")
COL_WIDTHS = (35, 50, 110, 200, 80, 80, 80, 100, 100, 0)


def _fmt_num(val) -> str:
    """Formatea número: max 2 decimales, sin ceros innecesarios."""
    n = float(val)
    if n == int(n):
        return str(int(n))
    return f"{n:.2f}".rstrip("0")


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

        # ── Filtro de búsqueda ─────────────────────────────────────────────
        filter_card = tk.Frame(self, bg=theme.BG_CARD, bd=1, relief="solid",
                               highlightbackground=theme.BORDER, highlightthickness=1)
        filter_card.pack(fill="x", padx=20, pady=(0, 8))

        tk.Label(filter_card, text="Buscar:", font=theme.FONT_BOLD,
                 bg=theme.BG_CARD, fg=theme.TEXT_SECONDARY
                 ).pack(side="left", padx=(10, 4), pady=8)

        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._refresh_tree())
        filter_entry = tk.Entry(
            filter_card, textvariable=self._filter_var,
            font=theme.FONT_NORMAL, bg=theme.BG_INPUT,
            fg=theme.TEXT_PRIMARY, relief="flat", bd=1,
            highlightbackground=theme.BORDER, highlightthickness=1)
        filter_entry.pack(side="left", fill="x", expand=True, padx=(0, 6), pady=8)

        tk.Button(filter_card, text="Limpiar", font=theme.FONT_SMALL,
                  bg=theme.BG_SECONDARY, fg=theme.TEXT_SECONDARY, relief="flat",
                  bd=0, padx=8, pady=2, cursor="hand2",
                  command=lambda: self._filter_var.set("")
                  ).pack(side="left", padx=(0, 8), pady=8)

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

        # Row 1: Nombre
        row1 = tk.Frame(fields_frame, bg=theme.BG_CARD)
        row1.pack(fill="x", pady=2)

        tk.Label(row1, text="Nombre:", font=theme.FONT_NORMAL,
                 bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, width=10, anchor="e"
                 ).pack(side="left", padx=(0, 4))
        self._nombre_var = tk.StringVar()
        tk.Entry(row1, textvariable=self._nombre_var, font=theme.FONT_NORMAL,
                 bg=theme.BG_INPUT, fg=theme.TEXT_PRIMARY, relief="flat", bd=1,
                 highlightbackground=theme.BORDER, highlightthickness=1
                 ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        # Row 2: Medidas
        row2 = tk.Frame(fields_frame, bg=theme.BG_CARD)
        row2.pack(fill="x", pady=2)

        tk.Label(row2, text="Largo:", font=theme.FONT_NORMAL,
                 bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, width=10, anchor="e"
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

        tk.Label(row3, text="Color:", font=theme.FONT_NORMAL,
                 bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, width=10, anchor="e"
                 ).pack(side="left", padx=(0, 4))
        self._color_var = tk.StringVar(value=COLORES[0])
        color_combo = ttk.Combobox(row3, textvariable=self._color_var,
                                   values=COLORES, state="readonly",
                                   font=theme.FONT_NORMAL, width=12)
        color_combo.pack(side="left", padx=(0, 8))

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

        tk.Label(row4, text="Notas:", font=theme.FONT_NORMAL,
                 bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, width=10, anchor="e"
                 ).pack(side="left", padx=(0, 4), anchor="n")
        self._notas_var = tk.StringVar()
        tk.Entry(row4, textvariable=self._notas_var, font=theme.FONT_NORMAL,
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

        # ── Treeview ───────────────────────────────────────────────────────
        tree_frame = tk.Frame(self, bg=theme.BG_PRIMARY)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        self._tree = ttk.Treeview(tree_frame, columns=COLUMNS, show="headings",
                                  selectmode="browse")
        for col, hdr, width in zip(COLUMNS, COL_HEADERS, COL_WIDTHS):
            self._tree.heading(col, text=hdr)
            if col == "check":
                self._tree.column(col, width=width, minwidth=35, anchor="center",
                                  stretch=False)
            elif col == "notas":
                self._tree.column(col, width=0, minwidth=0, stretch=False)
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

        # ── Botones de acción ──────────────────────────────────────────────
        action_bar = tk.Frame(self, bg=theme.BG_PRIMARY)
        action_bar.pack(fill="x", padx=20, pady=(0, 4))

        tk.Button(action_bar, text="Editar", font=theme.FONT_BOLD,
                  bg=theme.BTN_INFO, fg="white", relief="flat", bd=0,
                  padx=14, pady=4, cursor="hand2",
                  command=self._on_edit_selected).pack(side="left", padx=(0, 6))

        tk.Button(action_bar, text="Eliminar", font=theme.FONT_BOLD,
                  bg=theme.BTN_DANGER, fg="white", relief="flat", bd=0,
                  padx=14, pady=4, cursor="hand2",
                  command=self._on_delete).pack(side="left", padx=(0, 6))

        tk.Button(action_bar, text="📄 Generar PDF con QR", font=theme.FONT_BOLD,
                  bg="#9C27B0", fg="white", relief="flat", bd=0,
                  padx=14, pady=4, cursor="hand2",
                  command=self._on_generar_pdf).pack(side="right", padx=(6, 0))

        tk.Button(action_bar, text="❌ Deseleccionar", font=theme.FONT_BOLD,
                  bg="#607D8B", fg="white", relief="flat", bd=0,
                  padx=14, pady=4, cursor="hand2",
                  command=self._on_deselect_all).pack(side="right", padx=(0, 6))

        tk.Button(action_bar, text="✅ Seleccionar todo", font=theme.FONT_BOLD,
                  bg="#607D8B", fg="white", relief="flat", bd=0,
                  padx=14, pady=4, cursor="hand2",
                  command=self._on_select_all).pack(side="right", padx=(0, 6))

        # ── Log panel ─────────────────────────────────────────────────────
        self._log = LogPanel(self, height=5)
        self._log.pack(fill="x", padx=20, pady=(4, 12))
        self._log.log("App iniciada. Cargá productos con el formulario.")

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

    def _on_select_all(self) -> None:
        for item in self._tree.get_children():
            values = list(self._tree.item(item, "values"))
            prod_id = int(values[1])
            self._checked.add(prod_id)
            values[0] = "☑"
            self._tree.item(item, values=values)
        self._log.log(f"✅ {len(self._checked)} productos seleccionados")

    def _on_deselect_all(self) -> None:
        self._checked.clear()
        for item in self._tree.get_children():
            values = list(self._tree.item(item, "values"))
            values[0] = "☐"
            self._tree.item(item, values=values)
        self._log.log("❌ Selección limpiada")

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
            self._log.log(f"📄 PDF generado: {Path(filepath).name} ({len(seleccionados)} productos)")
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

            # Título del producto
            pdf.set_font("Helvetica", "B", 22)
            pdf.cell(0, 15, prod["nombre"], new_x="LMARGIN", new_y="NEXT", align="C")

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

            # Notas
            notas = prod.get("notas", "")
            if notas:
                pdf.ln(4)
                pdf.set_font("Helvetica", "I", 10)
                pdf.cell(0, 8, f"Notas: {notas}", new_x="LMARGIN", new_y="NEXT", align="C")

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
        return dict(nombre=nombre, largo=largo, ancho=ancho, alto=alto,
                    color=color, precio_fob=precio_fob, notas=notas)

    def _on_save(self) -> None:
        vals = self._get_form_values()
        if not vals:
            return

        if self._editing_id is not None:
            db.actualizar(self._editing_id, **vals)
            self._log.log(f"Producto #{self._editing_id} actualizado: {vals['nombre']}")
            self._editing_id = None
            self._form_title.configure(text="Nuevo Producto")
            self._btn_save.configure(text="Agregar", bg=theme.BTN_SUCCESS)
        else:
            new_id = db.agregar(**vals)
            self._log.log(f"Producto #{new_id} agregado: {vals['nombre']}")

        self._clear_form()
        self._refresh_tree()

    def _on_edit_selected(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Selección", "Seleccioná un producto para editar.")
            return
        values = self._tree.item(sel[0], "values")
        # values: (check, id, sku, nombre, largo, ancho, alto, color, precio_fob, notas)
        self._editing_id = int(values[1])
        self._nombre_var.set(values[3])
        self._largo_var.set(values[4])
        self._ancho_var.set(values[5])
        self._alto_var.set(values[6])
        self._color_var.set(values[7])
        self._precio_var.set(values[8])
        self._notas_var.set(values[9] if len(values) > 9 else "")
        self._form_title.configure(text=f"Editando Producto #{self._editing_id}")
        self._btn_save.configure(text="Guardar", bg=theme.BTN_WARNING)

    def _on_delete(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Selección", "Seleccioná un producto para eliminar.")
            return
        values = self._tree.item(sel[0], "values")
        id_ = int(values[1])
        nombre = values[3]
        if not messagebox.askyesno("Confirmar", f"¿Eliminar '{nombre}' (#{id_})?"):
            return
        db.eliminar(id_)
        self._checked.discard(id_)
        self._log.log(f"Producto #{id_} eliminado: {nombre}")
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
            notas=values[9] if len(values) > 9 else "")
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
        self._form_title.configure(text="Nuevo Producto")
        self._btn_save.configure(text="Agregar", bg=theme.BTN_SUCCESS)

    def _refresh_tree(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        filtro = self._filter_var.get().strip()
        productos = db.listar(filtro)
        for i, p in enumerate(productos):
            tag = "even" if i % 2 == 0 else "odd"
            check = "☑" if p["id"] in self._checked else "☐"
            self._tree.insert("", "end", values=(
                check, p["id"], p.get("sku", "-"), p["nombre"],
                _fmt_num(p["largo"]), _fmt_num(p["ancho"]),
                _fmt_num(p["alto"]), p["color"], _fmt_num(p["precio_fob"]),
                p.get("notas", "")),
                tags=(tag,))
        count = len(productos)
        self._count_label.configure(text=f"{count} producto{'s' if count != 1 else ''}")


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
