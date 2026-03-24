"""Base de datos SQLite para productos."""

import sqlite3
import string
import random
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "productos.db"

COLORES_VALIDOS = ("Blanco", "Negro", "Rosa", "Verde", "Violeta")

_SKU_CHARS = string.ascii_uppercase + string.digits
_SKU_LEN = 8


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _generar_sku(conn: sqlite3.Connection) -> str:
    """Genera un SKU único con formato GP-XXXXXXXX."""
    while True:
        code = "".join(random.choices(_SKU_CHARS, k=_SKU_LEN))
        sku = f"GP-{code}"
        existe = conn.execute(
            "SELECT 1 FROM productos WHERE sku = ?", (sku,)
        ).fetchone()
        if not existe:
            return sku


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
                precio_fob REAL NOT NULL DEFAULT 0,
                sku TEXT UNIQUE
            )
        """)
        # Migrar: agregar columna sku si no existe (tabla ya creada sin ella)
        cols = [r[1] for r in c.execute("PRAGMA table_info(productos)").fetchall()]
        if "sku" not in cols:
            c.execute("ALTER TABLE productos ADD COLUMN sku TEXT")
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sku ON productos(sku)")
        # Asignar SKU a productos existentes que no tengan
        sin_sku = c.execute("SELECT id FROM productos WHERE sku IS NULL").fetchall()
        for row in sin_sku:
            sku = _generar_sku(c)
            c.execute("UPDATE productos SET sku = ? WHERE id = ?", (sku, row["id"]))


def listar(filtro: str = "") -> list[dict]:
    sql = "SELECT * FROM productos"
    params: list = []
    if filtro:
        sql += " WHERE nombre LIKE ? OR color LIKE ? OR sku LIKE ?"
        like = f"%{filtro}%"
        params = [like, like, like]
    sql += " ORDER BY id DESC"
    with _conn() as c:
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def agregar(nombre: str, largo: float, ancho: float, alto: float,
            color: str, precio_fob: float) -> int:
    with _conn() as c:
        sku = _generar_sku(c)
        cur = c.execute(
            "INSERT INTO productos (nombre, largo, ancho, alto, color, precio_fob, sku) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nombre, largo, ancho, alto, color, precio_fob, sku))
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
