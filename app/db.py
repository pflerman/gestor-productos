"""Base de datos en Turso (SQLite en la nube) con cache local en memoria.

Al iniciar, descarga todos los productos a una lista en memoria.
Las lecturas (listar, filtrar) trabajan contra la cache → instantáneo.
Las escrituras (agregar, editar, eliminar) van a Turso Y actualizan la cache (write-through).
"""

import os
import string
import random
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TURSO_URL = os.getenv("TURSO_DB_URL", "")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

COLORES_VALIDOS = ("Blanco", "Negro", "Blanco negro", "Rosa", "Verde", "Violeta", "Transparente", "Rojo", "Azul")

_SKU_CHARS = string.ascii_uppercase + string.digits
_SKU_LEN = 8

# Cache en memoria: lista de dicts con todos los productos
_cache: list[dict] = []
_cache_loaded = False


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


def _load_cache() -> None:
    """Descarga todos los productos de Turso a la cache en memoria."""
    global _cache, _cache_loaded
    resp = _execute("SELECT * FROM productos ORDER BY id DESC")
    _cache = [_cast_producto(d) for d in _rows_to_dicts(resp)]
    _cache_loaded = True


def _generar_sku_unico() -> str:
    """Genera un SKU único con formato GP-XXXXXXXX (chequea contra la cache)."""
    skus_existentes = {p["sku"] for p in _cache if p.get("sku")}
    while True:
        code = "".join(random.choices(_SKU_CHARS, k=_SKU_LEN))
        sku = f"GP-{code}"
        if sku not in skus_existentes:
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
            notas TEXT NOT NULL DEFAULT '',
            etiquetas TEXT NOT NULL DEFAULT ''
        )
    """)
    # Migración: agregar columna etiquetas si no existe
    try:
        _execute("ALTER TABLE productos ADD COLUMN etiquetas TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass  # La columna ya existe
    _load_cache()


def listar() -> list[dict]:
    """Retorna todos los productos desde la cache (sin HTTP)."""
    if not _cache_loaded:
        _load_cache()
    return list(_cache)


def agregar(nombre: str, largo: float, ancho: float, alto: float,
            color: str, precio_fob: float, notas: str = "",
            etiquetas: str = "") -> int:
    sku = _generar_sku_unico()
    # Write-through: Turso primero
    resp = _execute(
        "INSERT INTO productos (nombre, largo, ancho, alto, color, precio_fob, sku, notas, etiquetas) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [nombre, largo, ancho, alto, color, precio_fob, sku, notas, etiquetas])
    new_id = resp.get("last_insert_rowid", 0)
    # Actualizar cache
    _cache.insert(0, _cast_producto({
        "id": new_id, "nombre": nombre, "largo": largo, "ancho": ancho,
        "alto": alto, "color": color, "precio_fob": precio_fob,
        "sku": sku, "notas": notas, "etiquetas": etiquetas,
    }))
    return new_id


def actualizar(id_: int, nombre: str, largo: float, ancho: float, alto: float,
               color: str, precio_fob: float, notas: str = "",
               etiquetas: str = "") -> None:
    # Write-through: Turso primero
    _execute(
        "UPDATE productos SET nombre=?, largo=?, ancho=?, alto=?, color=?, precio_fob=?, notas=?, etiquetas=? "
        "WHERE id=?",
        [nombre, largo, ancho, alto, color, precio_fob, notas, etiquetas, id_])
    # Actualizar cache
    for p in _cache:
        if p["id"] == id_:
            p.update(nombre=nombre, largo=largo, ancho=ancho, alto=alto,
                     color=color, precio_fob=precio_fob, notas=notas,
                     etiquetas=etiquetas)
            break


def eliminar(id_: int) -> None:
    # Write-through: Turso primero
    _execute("DELETE FROM productos WHERE id=?", [id_])
    # Actualizar cache
    _cache[:] = [p for p in _cache if p["id"] != id_]
