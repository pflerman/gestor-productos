# gestor-productos — contexto para Claude

App de escritorio Python/Tkinter para gestión de productos (CRUD + búsqueda + PDFs con QR) con una pestaña de IA (Claude + Gemini). Corre en Fedora (casa) y Windows/WSL (laburo) contra la misma base remota.

## Dependencias externas críticas

- **`.env` en la raíz** con 4 variables, sin esto la app no arranca:
  - `ANTHROPIC_API_KEY` — Claude API (pestaña IA)
  - `GEMINI_API_KEY` — Gemini API (generación de imágenes)
  - `TURSO_DB_URL` — `https://gestor-productos-pflerman.aws-us-east-1.turso.io`
  - `TURSO_AUTH_TOKEN` — token de Turso
- **Turso (SQLite cloud)** — la base de datos vive remota, no local. La app la consume vía HTTP API v2 Pipeline con `requests` (síncrono, compatible con Tkinter).
- **Multi-PC** — la app corre en dos máquinas (Fedora casa + Windows/WSL laburo) contra la **misma** base Turso. No hay sincronización de archivos, no hay SSHFS, no hay symlinks. Cada PC tiene su clon del repo y su propio venv.

## Arquitectura mental rápida

- `app/main.py` — entry point. Hace `load_dotenv` → `init_db` → `setup_theme` → `AppWindow` → `mainloop`.
- `app/ui/views/main_view.py` — vista CRUD principal, ~800 líneas, monolito. Acá vive el Treeview, el formulario, el menú contextual, los filtros, la generación de PDF.
- `app/ui/views/ia_view.py` — pestaña IA con dos paneles (Claude izquierda, Gemini derecha), cada uno corre en thread separado.
- `app/db.py` — capa de BD: `_execute(sql, args)` → tipifica args → POST a `/v2/pipeline` → `_rows_to_dicts` → `_cast_producto`. Sin ORM.
- `app/ui/theme.py` — Material Design claro, paleta + fuentes.
- Patrón general: MVC liviano, lazy loading de clientes IA, threading para llamadas externas, trace variables para filtros en tiempo real.

## ⚠️ Trampas y cosas no obvias

### No usar `libsql-experimental` ni `libsql-client`
La conexión a Turso es **HTTP API v2 Pipeline con `requests`**, deliberadamente. Los clientes oficiales de libsql fallan en compilación o son async (incompatibles con el mainloop de Tkinter). Si querés "modernizar" esto, no lo hagas — ya se evaluó.

### `minsize` de la ventana tiene que ser bajo (400x300)
Si subís el `minsize`, el snap de ventanas de GNOME se rompe (no podés tirar la ventana a media pantalla). Está documentado en commit `e624516`. No lo toques.

### El orden de `values` del Treeview es load-bearing
El orden es exactamente:
```
(check, id, sku, nombre, largo, ancho, alto, color, precio_fob, notas, etiquetas)
```
El menú contextual (`_on_right_click` en `main_view.py`) y otros lugares indexan por posición (`values[2]`, `values[8]`, etc.). Si agregás/reordenás columnas, hay que actualizar TODOS los índices a mano. No hay protección.

### `productos.db` en el repo está obsoleto
El archivo `productos.db` quedó versionado como legado de cuando la app era SQLite local. **La base real es Turso**, ese archivo no se lee ni se escribe en runtime. No lo edites, no asumas que tiene datos vivos, y no te asustes si aparece "modified" en `git status` — es ruido.

### Íconos con PIL/ImageDraw, NO emoji Unicode
En Tkinter sobre Linux, los emoji Unicode renderizan inconsistente (a veces como cuadraditos, a veces sin color). La regla del proyecto: **dibujar íconos con `PIL.ImageDraw`** y cargarlos como `PhotoImage`. Si ves un helper que dibuja un círculo o una lupa con PIL para un botón, no lo "simplifiques" a un emoji.

### Filtro de búsqueda: AND de palabras sueltas + normalización de acentos
El filtro del Treeview no es un `LIKE %x%` ingenuo: normaliza acentos y hace AND de palabras sueltas sin importar el orden. Eso permite buscar "armario pepe mediano" y matchear "Armario modular mediano Pepe". No lo "simplifiques".

## Helpers / decisiones que parecen raras pero tienen razón

- **Cache en memoria con write-through a Turso** — el filtrado del Treeview lee de un cache local en RAM, las escrituras van a Turso y actualizan el cache. Si lo "simplificás" a leer Turso en cada keypress, el filtrado se vuelve lento e inusable.
- **Threading en la pestaña IA** — las llamadas a Claude/Gemini corren en threads separados para no congelar el mainloop. Si las metés inline, la UI se cuelga durante 10-30s por request.
- **Generación de SKU en cliente** (`GP-XXXXXXXX`) — no en la BD. Hay un índice UNIQUE en Turso pero el SKU se genera en Python antes del INSERT.

## Cómo correrlo

```bash
cd ~/Proyectos/gestor-productos
source venv/bin/activate
python3 app/main.py
```

En una PC nueva:
```bash
git clone https://github.com/pflerman/gestor-productos.git
cd gestor-productos
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Crear .env con las 4 variables (ver arriba)
python3 app/main.py
```

Hay un `.desktop` para el launcher de GNOME (Fedora). Ícono en `app/assets/icon.png`.

## Git

- Branch principal: `main`
- Remote: GitHub `pflerman/gestor-productos`
- Estilo de commits: español, en minúscula, cortos, sin prefijos rígidos tipo `feat:` (algunos tienen `fix:` cuando es bug, pero no es obligatorio). Ejemplos del log:
  - `agregar color Gris`
  - `fix: reducir minsize para que GNOME snap funcione correctamente`
  - `agregar sistema de etiquetas a productos`
- Una rama, push directo a `main`. Sin PRs.
