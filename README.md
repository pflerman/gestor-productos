# 📦 Gestor de Productos

Sistema simple de gestión de productos (CRUD) con Python, SQLite y Rich para una interfaz de terminal bonita.

## 🚀 Características

- ✅ **CRUD Completo**: Crear, Leer, Actualizar y Eliminar productos
- 📊 **Interfaz Rica**: Menús y tablas formateadas con Rich
- 💾 **Persistencia**: Base de datos SQLite (products.db)
- ✨ **Validación**: Validación de datos numéricos
- 🎨 **Interfaz Amigable**: Menú interactivo con navegación numérica

## 📋 Requisitos

- Python 3.7 o superior
- Rich (para interfaz de terminal)

## 🔧 Instalación

1. Clona o descarga este repositorio:
```bash
git clone <tu-repo-url>
cd gestor-productos
```

2. Instala las dependencias:
```bash
pip install rich
```

## 🎮 Uso

Ejecuta el programa:
```bash
python main.py
```

o con permisos de ejecución:
```bash
chmod +x main.py
./main.py
```

## 📖 Funcionalidades

### 1. Agregar Producto
Permite ingresar un nuevo producto con los siguientes campos:
- **Largo** (metros)
- **Ancho** (metros)
- **Alto** (metros)
- **Precio** ($)

### 2. Listar Productos
Muestra todos los productos en una tabla formateada que incluye:
- ID
- Dimensiones (largo, ancho, alto)
- Precio
- Volumen calculado (largo × ancho × alto)

### 3. Modificar Producto
Actualiza los datos de un producto existente. Muestra los valores actuales y permite mantenerlos presionando Enter.

### 4. Eliminar Producto
Elimina un producto de la base de datos (con confirmación).

### 5. Salir
Cierra la aplicación de forma segura.

## 💾 Base de Datos

El archivo `products.db` se crea automáticamente en la primera ejecución y contiene:

**Tabla: products**
| Campo  | Tipo    | Descripción              |
|--------|---------|--------------------------|
| id     | INTEGER | ID autoincremental (PK)  |
| largo  | REAL    | Largo en metros          |
| ancho  | REAL    | Ancho en metros          |
| alto   | REAL    | Alto en metros           |
| precio | REAL    | Precio en pesos/dólares  |

**Nota**: El archivo `products.db` está incluido en el repositorio para permitir la sincronización de datos entre diferentes PCs.

## 🛠️ Estructura del Proyecto

```
gestor-productos/
├── main.py          # Aplicación principal
├── products.db      # Base de datos SQLite (se crea automáticamente)
├── .gitignore       # Archivos ignorados por Git
└── README.md        # Este archivo
```

## 🎨 Capturas de Ejemplo

### Menú Principal
```
╭─────── GESTOR DE PRODUCTOS ───────╮
│ [1] 📝 Agregar Producto           │
│ [2] 📋 Listar Productos            │
│ [3] ✏️  Modificar Producto         │
│ [4] 🗑️  Eliminar Producto          │
│ [5] 🚪 Salir                       │
╰────────────────────────────────────╯
```

### Tabla de Productos
```
           📦 Lista de Productos
┏━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ ID ┃ Largo (m) ┃ Ancho (m) ┃ Alto (m) ┃ Precio ($)┃ Volumen (m³)┃
┡━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ 1  │      2.00 │      1.50 │     0.80 │    150.00 │       2.400 │
│ 2  │      3.50 │      2.00 │     1.20 │    280.50 │       8.400 │
└────┴───────────┴───────────┴──────────┴───────────┴─────────────┘
```

## 🤝 Contribuciones

Este es un proyecto simple de ejemplo. Siéntete libre de hacer fork y modificarlo según tus necesidades.

## 📝 Licencia

Proyecto de uso libre para aprendizaje y uso personal.

## ✨ Características Técnicas

- **Manejo de errores**: Try-catch en todas las operaciones de BD
- **Validación**: Verifica que valores numéricos sean positivos
- **Confirmación**: Solicita confirmación antes de eliminar
- **ID Autoincremental**: SQLite genera IDs automáticamente
- **Interfaz amigable**: Rich proporciona colores y formato
- **Persistencia**: Datos guardados automáticamente en SQLite

---

Desarrollado con ❤️ usando Python, SQLite y Rich
