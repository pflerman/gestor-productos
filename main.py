#!/usr/bin/env python3
"""
Gestor de Productos - Sistema CRUD simple con SQLite y Rich
"""

import sqlite3
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, FloatPrompt, IntPrompt, Confirm

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
                    largo REAL NOT NULL,
                    ancho REAL NOT NULL,
                    alto REAL NOT NULL,
                    precio REAL NOT NULL
                )
            """)
            self.conn.commit()
            console.print(f"[green]✓[/green] Base de datos '{self.db_name}' inicializada correctamente")
        except sqlite3.Error as e:
            console.print(f"[red]✗[/red] Error al inicializar la base de datos: {e}")

    def create_product(self, largo: float, ancho: float, alto: float, precio: float) -> bool:
        """Crea un nuevo producto en la base de datos"""
        try:
            self.cursor.execute(
                "INSERT INTO products (largo, ancho, alto, precio) VALUES (?, ?, ?, ?)",
                (largo, ancho, alto, precio)
            )
            self.conn.commit()
            console.print(f"[green]✓[/green] Producto agregado exitosamente (ID: {self.cursor.lastrowid})")
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

    def update_product(self, product_id: int, largo: float, ancho: float, alto: float, precio: float) -> bool:
        """Actualiza un producto existente"""
        try:
            self.cursor.execute(
                "UPDATE products SET largo=?, ancho=?, alto=?, precio=? WHERE id=?",
                (largo, ancho, alto, precio, product_id)
            )
            self.conn.commit()

            if self.cursor.rowcount > 0:
                console.print(f"[green]✓[/green] Producto ID {product_id} actualizado exitosamente")
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
    table.add_column("Largo (m)", style="green", justify="right")
    table.add_column("Ancho (m)", style="green", justify="right")
    table.add_column("Alto (m)", style="green", justify="right")
    table.add_column("Precio ($)", style="yellow", justify="right")
    table.add_column("Volumen (m³)", style="blue", justify="right")

    for product in products:
        product_id, largo, ancho, alto, precio = product
        volumen = largo * ancho * alto
        table.add_row(
            str(product_id),
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
        "[5] 🚪 Salir",
        title="[bold cyan]GESTOR DE PRODUCTOS[/bold cyan]",
        border_style="cyan"
    )
    console.print(menu)


def add_product(manager: ProductManager):
    """Interfaz para agregar un nuevo producto"""
    console.print("\n[bold cyan]➕ Agregar Nuevo Producto[/bold cyan]")

    try:
        largo = FloatPrompt.ask("Largo (metros)", default=0.0)
        ancho = FloatPrompt.ask("Ancho (metros)", default=0.0)
        alto = FloatPrompt.ask("Alto (metros)", default=0.0)
        precio = FloatPrompt.ask("Precio ($)", default=0.0)

        if largo <= 0 or ancho <= 0 or alto <= 0 or precio <= 0:
            console.print("[red]✗[/red] Todos los valores deben ser mayores a cero")
            return

        manager.create_product(largo, ancho, alto, precio)
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
        _, curr_largo, curr_ancho, curr_alto, curr_precio = current_product

        console.print(f"\n[dim]Valores actuales: Largo={curr_largo}, Ancho={curr_ancho}, Alto={curr_alto}, Precio={curr_precio}[/dim]")
        console.print("[dim]Presiona Enter para mantener el valor actual[/dim]\n")

        largo = FloatPrompt.ask("Nuevo largo (metros)", default=curr_largo)
        ancho = FloatPrompt.ask("Nuevo ancho (metros)", default=curr_ancho)
        alto = FloatPrompt.ask("Nuevo alto (metros)", default=curr_alto)
        precio = FloatPrompt.ask("Nuevo precio ($)", default=curr_precio)

        if largo <= 0 or ancho <= 0 or alto <= 0 or precio <= 0:
            console.print("[red]✗[/red] Todos los valores deben ser mayores a cero")
            return

        manager.update_product(product_id, largo, ancho, alto, precio)
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


def main():
    """Función principal del programa"""
    console.clear()
    console.print("[bold green]🚀 Iniciando Gestor de Productos...[/bold green]\n")

    manager = ProductManager()

    try:
        while True:
            show_menu()

            try:
                choice = Prompt.ask("Selecciona una opción", choices=["1", "2", "3", "4", "5"])

                if choice == "1":
                    add_product(manager)
                elif choice == "2":
                    list_products(manager)
                elif choice == "3":
                    update_product(manager)
                elif choice == "4":
                    delete_product(manager)
                elif choice == "5":
                    console.print("\n[bold green]👋 ¡Hasta pronto![/bold green]")
                    break
            except KeyboardInterrupt:
                console.print("\n[yellow]Operación cancelada[/yellow]")
                continue

    finally:
        manager.close()


if __name__ == "__main__":
    main()
