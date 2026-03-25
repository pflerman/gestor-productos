"""Base de datos en Turso (SQLite en la nube) para productos."""

import os
import string
import random
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TURSO_URL = os.getenv("TURSO_DB_URL", "")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

COLORES_VALIDOS = ("Blanco", "Negro", "Rosa", "Verde", "Violeta")

_SKU_CHARS = string.ascii_uppercase + string.digits
_SKU_LEN = 8


def _execute(sql: str, args: list | None = None) -> dict:
    """Ejecuta una query SQL en Turso via HTTP API."""
    stmt = {"sql": sql}
    if args:
        typed_args = []
        for a in args:
            if a is None:
                typed_args.append({"type": "null"})
            elif isinstance(a, int):
                typed_args.append({"type": "integer", "value": str(a)})
            elif isinstance(a, float):
                typed_args.append({"type": "float", "value": a})
            else:
                typed_args.append({"type": "text", "value": str(a)})
        stmt["args"] = typed_args

    resp = requests.post(
        f"{TURSO_URL}/v2/pipeline",
        headers={"Authorization": f"Bearer {TURSO_TOKEN}"},
        json={"requests": [{"type": "execute", "stmt": stmt}, {"type": "close"}]},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    result = data["results"][0]
    if result["type"] == "error":
        raise Exception(f"Turso error: {result['error']['message']}")
    return result["response"]["result"]


def _rows_to_dicts(response: dict) -> list[dict]:
    """Convierte la respuesta de Turso a lista de dicts."""
    cols = [c["name"] for c in response["cols"]]
    rows = []
    for row in response["rows"]:
        d = {}
        for i, col in enumerate(cols):
            val = row[i]
            d[col] = val["value"] if val["type"] != "null" else None
        rows.append(d)
    return rows


def _cast_producto(d: dict) -> dict:
    """Castea los campos numéricos de un producto."""
    for campo in ("id",):
        if d.get(campo) is not None:
            d[campo] = int(d[campo])
    for campo in ("largo", "ancho", "alto", "precio_fob"):
        if d.get(campo) is not None:
            d[campo] = float(d[campo])
    return d


def _generar_sku_unico() -> str:
    """Genera un SKU único con formato GP-XXXXXXXX."""
    while True:
        code = "".join(random.choices(_SKU_CHARS, k=_SKU_LEN))
        sku = f"GP-{code}"
        resp = _execute("SELECT 1 FROM productos WHERE sku = ?", [sku])
        if not resp["rows"]:
            return sku


def init_db() -> None:
    _execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            largo REAL NOT NULL DEFAULT 0,
            ancho REAL NOT NULL DEFAULT 0,
            alto REAL NOT NULL DEFAULT 0,
            color TEXT NOT NULL DEFAULT 'Blanco',
            precio_fob REAL NOT NULL DEFAULT 0,
            sku TEXT UNIQUE,
            notas TEXT NOT NULL DEFAULT ''
        )
    """)


def listar(filtro: str = "") -> list[dict]:
    sql = "SELECT * FROM productos"
    params: list = []
    if filtro:
        sql += " WHERE nombre LIKE ? OR color LIKE ? OR sku LIKE ? OR notas LIKE ?"
        like = f"%{filtro}%"
        params = [like, like, like, like]
    sql += " ORDER BY id DESC"
    resp = _execute(sql, params if params else None)
    return [_cast_producto(d) for d in _rows_to_dicts(resp)]


def agregar(nombre: str, largo: float, ancho: float, alto: float,
            color: str, precio_fob: float, notas: str = "") -> int:
    sku = _generar_sku_unico()
    resp = _execute(
        "INSERT INTO productos (nombre, largo, ancho, alto, color, precio_fob, sku, notas) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [nombre, largo, ancho, alto, color, precio_fob, sku, notas])
    return resp.get("last_insert_rowid", 0)


def actualizar(id_: int, nombre: str, largo: float, ancho: float, alto: float,
               color: str, precio_fob: float, notas: str = "") -> None:
    _execute(
        "UPDATE productos SET nombre=?, largo=?, ancho=?, alto=?, color=?, precio_fob=?, notas=? "
        "WHERE id=?",
        [nombre, largo, ancho, alto, color, precio_fob, notas, id_])


def eliminar(id_: int) -> None:
    _execute("DELETE FROM productos WHERE id=?", [id_])
