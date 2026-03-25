# Gestor de Productos

Aplicación de escritorio para gestión de productos (CRUD) con Python, Tkinter y SQLite.

## Características

- **CRUD Completo**: Crear, leer, actualizar y eliminar productos
- **Interfaz Tkinter**: Tema Material Design oscuro/claro
- **Persistencia**: Base de datos SQLite (productos.db)
- **SKU Automático**: Código único `GP-XXXXXXXX` por producto
- **Códigos QR**: Generación de QR con datos del producto
- **Selección Múltiple**: Checkboxes para operar sobre varios productos
- **Exportar PDF**: PDF con títulos, SKU, medidas y códigos QR
- **Copiar al Portapapeles**: Menú contextual con click derecho
- **Filtros en tiempo real**: Búsqueda y exclusión con normalización de acentos
- **Asistente IA**: Generación de texto con Claude e imágenes con Gemini

## Requisitos

- Python 3.7+
- Dependencias: ver `requirements.txt`

## Instalación

```bash
git clone <tu-repo-url>
cd gestor-productos
pip install -r requirements.txt
```

## Uso

```bash
python app/main.py
```

## Configuración IA

Agregá tus API keys en `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-tu-key
GEMINI_API_KEY=AIzaSy-tu-key
```

## Estructura

```
gestor-productos/
├── app/
│   ├── main.py          # Entry point
│   ├── db.py            # Base de datos SQLite
│   ├── config.py        # Configuración
│   ├── assets/
│   │   └── icon.png
│   └── ui/
│       ├── app_window.py
│       ├── theme.py
│       ├── views/
│       │   ├── main_view.py
│       │   └── ia_view.py
│       └── components/
│           └── log_panel.py
├── productos.db         # BD (se crea automáticamente)
├── requirements.txt
└── README.md
```

## Licencia

Proyecto de uso libre para aprendizaje y uso personal.
