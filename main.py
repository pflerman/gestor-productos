#!/usr/bin/env python3
"""
Gestor de Productos - Sistema CRUD simple con SQLite y Rich
"""

import sqlite3
import random
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, FloatPrompt, IntPrompt, Confirm

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

console = Console()


class ProductManager:
    """Gestor de productos con base de datos SQLite"""

    def __init__(self, db_name: str = "products.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.init_database()

    def init_database(self):
        """Inicializa la base de datos y crea la tabla si no existe"""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    largo REAL NOT NULL,
                    ancho REAL NOT NULL,
                    alto REAL NOT NULL,
                    precio REAL NOT NULL
                )
            """)

            # Crear tabla de notas aleatorias para descripciones de venta
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nota TEXT NOT NULL UNIQUE
                )
            """)
            self.conn.commit()

            # Migración: agregar columna nombre si no existe
            self.cursor.execute("PRAGMA table_info(products)")
            columns = [column[1] for column in self.cursor.fetchall()]
            if 'nombre' not in columns:
                self.cursor.execute("ALTER TABLE products ADD COLUMN nombre TEXT DEFAULT 'Sin nombre'")
                self.conn.commit()
                console.print(f"[yellow]⚠[/yellow] Columna 'nombre' agregada a la base de datos existente")

            # Poblar tabla de notas si está vacía
            self.cursor.execute("SELECT COUNT(*) FROM sales_notes")
            if self.cursor.fetchone()[0] == 0:
                self._populate_sales_notes()

            console.print(f"[green]✓[/green] Base de datos '{self.db_name}' inicializada correctamente")
        except sqlite3.Error as e:
            console.print(f"[red]✗[/red] Error al inicializar la base de datos: {e}")

    def _populate_sales_notes(self):
        """Puebla la tabla de notas con mensajes creativos para ventas"""
        notas = [
            "✨ ¡Este producto es una joya! Lo uso personalmente y lo recomiendo 100%",
            "🌟 Calidad premium garantizada, no te vas a arrepentir de esta compra",
            "💯 Mis clientes lo aman, es de los más vendidos de la tienda",
            "🔥 ¡Oferta imperdible! A este precio no lo vas a encontrar en otro lado",
            "⭐ Excelente relación precio-calidad, te va a durar años",
            "🎯 Producto de alta calidad, ideal para lo que necesitás",
            "💎 Es un clásico que nunca falla, super recomendado",
            "🚀 Llegó para quedarse, es uno de mis favoritos personales",
            "👌 Perfecto para regalo, siempre queda bien",
            "🏆 Ganador en su categoría, la mejor inversión que podés hacer",
            "💪 Resistente y duradero, probado por miles de clientes satisfechos",
            "🎁 Un must-have, todos deberían tener uno de estos",
            "✅ Aprobado por expertos, calidad superior comprobada",
            "🌈 Versátil y práctico, te va a sorprender lo útil que es",
            "🔝 Top ventas del mes, se está yendo rapidísimo",
            "💝 Amor a primera vista, mis clientes vuelven a comprarlo",
            "⚡ Entrega rápida disponible, lo tenés en tus manos en días",
            "🎪 ¡No te lo pierdas! Stock limitado por alta demanda",
            "🌺 Diseño impecable y funcionalidad de primera, una combinación perfecta",
            "🔐 Compra segura y confiable, miles de ventas exitosas nos respaldan"
        ]

        for nota in notas:
            try:
                self.cursor.execute("INSERT INTO sales_notes (nota) VALUES (?)", (nota,))
            except sqlite3.IntegrityError:
                # Si ya existe, continuar
                pass
        self.conn.commit()
        console.print(f"[green]✓[/green] {len(notas)} notas de venta cargadas en la base de datos")

    def get_random_sales_note(self) -> str:
        """Obtiene una nota aleatoria de la base de datos"""
        try:
            self.cursor.execute("SELECT nota FROM sales_notes ORDER BY RANDOM() LIMIT 1")
            result = self.cursor.fetchone()
            return result[0] if result else ""
        except sqlite3.Error:
            return ""

    def create_product(self, nombre: str, largo: float, ancho: float, alto: float, precio: float) -> bool:
        """Crea un nuevo producto en la base de datos"""
        try:
            self.cursor.execute(
                "INSERT INTO products (nombre, largo, ancho, alto, precio) VALUES (?, ?, ?, ?, ?)",
                (nombre, largo, ancho, alto, precio)
            )
            self.conn.commit()
            console.print(f"[green]✓[/green] Producto '{nombre}' agregado exitosamente (ID: {self.cursor.lastrowid})")
            return True
        except sqlite3.Error as e:
            console.print(f"[red]✗[/red] Error al crear producto: {e}")
            return False

    def read_products(self) -> list:
        """Lee todos los productos de la base de datos"""
        try:
            self.cursor.execute("SELECT * FROM products ORDER BY id")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            console.print(f"[red]✗[/red] Error al leer productos: {e}")
            return []

    def update_product(self, product_id: int, nombre: str, largo: float, ancho: float, alto: float, precio: float) -> bool:
        """Actualiza un producto existente"""
        try:
            self.cursor.execute(
                "UPDATE products SET nombre=?, largo=?, ancho=?, alto=?, precio=? WHERE id=?",
                (nombre, largo, ancho, alto, precio, product_id)
            )
            self.conn.commit()

            if self.cursor.rowcount > 0:
                console.print(f"[green]✓[/green] Producto '{nombre}' (ID {product_id}) actualizado exitosamente")
                return True
            else:
                console.print(f"[yellow]⚠[/yellow] No se encontró el producto con ID {product_id}")
                return False
        except sqlite3.Error as e:
            console.print(f"[red]✗[/red] Error al actualizar producto: {e}")
            return False

    def delete_product(self, product_id: int) -> bool:
        """Elimina un producto de la base de datos"""
        try:
            self.cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
            self.conn.commit()

            if self.cursor.rowcount > 0:
                console.print(f"[green]✓[/green] Producto ID {product_id} eliminado exitosamente")
                return True
            else:
                console.print(f"[yellow]⚠[/yellow] No se encontró el producto con ID {product_id}")
                return False
        except sqlite3.Error as e:
            console.print(f"[red]✗[/red] Error al eliminar producto: {e}")
            return False

    def close(self):
        """Cierra la conexión a la base de datos"""
        if self.conn:
            self.conn.close()


def display_products(products: list):
    """Muestra los productos en una tabla formateada con Rich"""
    if not products:
        console.print("[yellow]No hay productos registrados[/yellow]")
        return

    table = Table(title="📦 Lista de Productos", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", justify="center")
    table.add_column("Nombre", style="white", justify="left")
    table.add_column("Largo (m)", style="green", justify="right")
    table.add_column("Ancho (m)", style="green", justify="right")
    table.add_column("Alto (m)", style="green", justify="right")
    table.add_column("Precio ($)", style="yellow", justify="right")
    table.add_column("Volumen (m³)", style="blue", justify="right")

    for product in products:
        product_id, nombre, largo, ancho, alto, precio = product
        volumen = largo * ancho * alto
        table.add_row(
            str(product_id),
            nombre,
            f"{largo:.2f}",
            f"{ancho:.2f}",
            f"{alto:.2f}",
            f"{precio:.2f}",
            f"{volumen:.3f}"
        )

    console.print(table)


def show_menu():
    """Muestra el menú principal"""
    console.print()
    menu = Panel(
        "[1] 📝 Agregar Producto\n"
        "[2] 📋 Listar Productos\n"
        "[3] ✏️  Modificar Producto\n"
        "[4] 🗑️  Eliminar Producto\n"
        "[5] 💬 Generar Descripción de Venta\n"
        "[6] 🚪 Salir",
        title="[bold cyan]GESTOR DE PRODUCTOS[/bold cyan]",
        border_style="cyan"
    )
    console.print(menu)


def add_product(manager: ProductManager):
    """Interfaz para agregar un nuevo producto"""
    console.print("\n[bold cyan]➕ Agregar Nuevo Producto[/bold cyan]")

    try:
        nombre = Prompt.ask("Nombre del producto")
        if not nombre.strip():
            console.print("[red]✗[/red] El nombre no puede estar vacío")
            return

        largo = FloatPrompt.ask("Largo (metros)", default=0.0)
        ancho = FloatPrompt.ask("Ancho (metros)", default=0.0)
        alto = FloatPrompt.ask("Alto (metros)", default=0.0)
        precio = FloatPrompt.ask("Precio ($)", default=0.0)

        if largo <= 0 or ancho <= 0 or alto <= 0 or precio <= 0:
            console.print("[red]✗[/red] Todos los valores deben ser mayores a cero")
            return

        manager.create_product(nombre.strip(), largo, ancho, alto, precio)
    except (ValueError, KeyboardInterrupt):
        console.print("[yellow]Operación cancelada[/yellow]")


def list_products(manager: ProductManager):
    """Interfaz para listar todos los productos"""
    console.print("\n[bold cyan]📋 Lista de Productos[/bold cyan]")
    products = manager.read_products()
    display_products(products)


def update_product(manager: ProductManager):
    """Interfaz para actualizar un producto existente"""
    console.print("\n[bold cyan]✏️  Modificar Producto[/bold cyan]")

    # Primero mostrar productos disponibles
    products = manager.read_products()
    display_products(products)

    if not products:
        return

    try:
        product_id = IntPrompt.ask("\nID del producto a modificar")

        # Verificar si existe
        product_exists = any(p[0] == product_id for p in products)
        if not product_exists:
            console.print(f"[red]✗[/red] No existe un producto con ID {product_id}")
            return

        # Obtener datos actuales
        current_product = next(p for p in products if p[0] == product_id)
        _, curr_nombre, curr_largo, curr_ancho, curr_alto, curr_precio = current_product

        console.print(f"\n[dim]Valores actuales: Nombre={curr_nombre}, Largo={curr_largo}, Ancho={curr_ancho}, Alto={curr_alto}, Precio={curr_precio}[/dim]")
        console.print("[dim]Presiona Enter para mantener el valor actual[/dim]\n")

        nombre = Prompt.ask("Nuevo nombre", default=curr_nombre)
        if not nombre.strip():
            console.print("[red]✗[/red] El nombre no puede estar vacío")
            return

        largo = FloatPrompt.ask("Nuevo largo (metros)", default=curr_largo)
        ancho = FloatPrompt.ask("Nuevo ancho (metros)", default=curr_ancho)
        alto = FloatPrompt.ask("Nuevo alto (metros)", default=curr_alto)
        precio = FloatPrompt.ask("Nuevo precio ($)", default=curr_precio)

        if largo <= 0 or ancho <= 0 or alto <= 0 or precio <= 0:
            console.print("[red]✗[/red] Todos los valores deben ser mayores a cero")
            return

        manager.update_product(product_id, nombre.strip(), largo, ancho, alto, precio)
    except (ValueError, KeyboardInterrupt):
        console.print("[yellow]Operación cancelada[/yellow]")


def delete_product(manager: ProductManager):
    """Interfaz para eliminar un producto"""
    console.print("\n[bold cyan]🗑️  Eliminar Producto[/bold cyan]")

    # Primero mostrar productos disponibles
    products = manager.read_products()
    display_products(products)

    if not products:
        return

    try:
        product_id = IntPrompt.ask("\nID del producto a eliminar")

        # Confirmar eliminación
        if Confirm.ask(f"¿Estás seguro de eliminar el producto ID {product_id}?", default=False):
            manager.delete_product(product_id)
        else:
            console.print("[yellow]Operación cancelada[/yellow]")
    except (ValueError, KeyboardInterrupt):
        console.print("[yellow]Operación cancelada[/yellow]")


def generate_sales_description(manager: ProductManager):
    """Interfaz para generar descripción de venta de un producto"""
    console.print("\n[bold cyan]📝 Generar Descripción de Venta[/bold cyan]")

    # Mostrar productos disponibles
    products = manager.read_products()
    display_products(products)

    if not products:
        return

    try:
        product_id = IntPrompt.ask("\nID del producto para generar descripción")

        # Verificar si existe
        product = next((p for p in products if p[0] == product_id), None)
        if not product:
            console.print(f"[red]✗[/red] No existe un producto con ID {product_id}")
            return

        # Desempaquetar datos del producto
        _, nombre, largo_m, ancho_m, alto_m, precio = product

        # Convertir medidas de metros a centímetros
        largo_cm = largo_m * 100
        ancho_cm = ancho_m * 100
        alto_cm = alto_m * 100

        # Obtener nota aleatoria
        nota_random = manager.get_random_sales_note()

        # Generar descripción de venta
        descripcion = f"""¡Hola! Te presento este excelente {nombre} 😊

📏 Medidas:
   • Largo: {largo_cm:.1f} cm
   • Ancho: {ancho_cm:.1f} cm
   • Alto: {alto_cm:.1f} cm

💰 Precio: ${precio:.2f}

{nota_random}

¡Cualquier consulta no dudes en preguntar! Estoy para ayudarte 🙌"""

        # Mostrar descripción
        console.print()
        panel = Panel(
            descripcion,
            title="[bold green]📋 Descripción Generada[/bold green]",
            border_style="green",
            padding=(1, 2)
        )
        console.print(panel)

        # Intentar copiar al portapapeles
        if CLIPBOARD_AVAILABLE:
            try:
                pyperclip.copy(descripcion)
                console.print("\n[green]✓ ¡Descripción copiada al portapapeles![/green] Ya podés pegarla en Mercado Libre 📋")
            except Exception as e:
                console.print(f"\n[yellow]⚠[/yellow] No se pudo copiar al portapapeles: {e}")
                console.print("[dim]Seleccioná y copiá manualmente el texto de arriba[/dim]")
        else:
            console.print("\n[yellow]💡 Tip:[/yellow] Instalá pyperclip para copiar automáticamente al portapapeles:")
            console.print("[dim]   pip install pyperclip[/dim]")
            console.print("[dim]Mientras tanto, seleccioná y copiá manualmente el texto de arriba[/dim]")

    except (ValueError, KeyboardInterrupt):
        console.print("[yellow]Operación cancelada[/yellow]")


def main():
    """Función principal del programa"""
    console.clear()
    console.print("[bold green]🚀 Iniciando Gestor de Productos...[/bold green]\n")

    manager = ProductManager()

    try:
        while True:
            show_menu()

            try:
                choice = Prompt.ask("Selecciona una opción", choices=["1", "2", "3", "4", "5", "6"])

                if choice == "1":
                    add_product(manager)
                elif choice == "2":
                    list_products(manager)
                elif choice == "3":
                    update_product(manager)
                elif choice == "4":
                    delete_product(manager)
                elif choice == "5":
                    generate_sales_description(manager)
                elif choice == "6":
                    console.print("\n[bold green]👋 ¡Hasta pronto![/bold green]")
                    break
            except KeyboardInterrupt:
                console.print("\n[yellow]Operación cancelada[/yellow]")
                continue

    finally:
        manager.close()


if __name__ == "__main__":
    main()
