"""Base de datos SQLite para productos."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "productos.db"

COLORES_VALIDOS = ("Blanco", "Negro", "Rosa", "Verde", "Violeta")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                largo REAL NOT NULL DEFAULT 0,
                ancho REAL NOT NULL DEFAULT 0,
                alto REAL NOT NULL DEFAULT 0,
                color TEXT NOT NULL DEFAULT 'Blanco',
                precio_fob REAL NOT NULL DEFAULT 0
            )
        """)


def listar(filtro: str = "") -> list[dict]:
    sql = "SELECT * FROM productos"
    params: list = []
    if filtro:
        sql += " WHERE nombre LIKE ? OR color LIKE ?"
        like = f"%{filtro}%"
        params = [like, like]
    sql += " ORDER BY id DESC"
    with _conn() as c:
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def agregar(nombre: str, largo: float, ancho: float, alto: float,
            color: str, precio_fob: float) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO productos (nombre, largo, ancho, alto, color, precio_fob) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (nombre, largo, ancho, alto, color, precio_fob))
        return cur.lastrowid


def actualizar(id_: int, nombre: str, largo: float, ancho: float, alto: float,
               color: str, precio_fob: float) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE productos SET nombre=?, largo=?, ancho=?, alto=?, color=?, precio_fob=? "
            "WHERE id=?",
            (nombre, largo, ancho, alto, color, precio_fob, id_))


def eliminar(id_: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM productos WHERE id=?", (id_,))
