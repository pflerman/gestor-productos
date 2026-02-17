# 📦 Gestor de Productos

Sistema simple de gestión de productos (CRUD) con Python, SQLite y Rich para una interfaz de terminal bonita.

## 🚀 Características

- ✅ **CRUD Completo**: Crear, Leer, Actualizar y Eliminar productos
- 📊 **Interfaz Rica**: Menús y tablas formateadas con Rich
- 💾 **Persistencia**: Base de datos SQLite (products.db)
- ✨ **Validación**: Validación de datos numéricos
- 🎨 **Interfaz Amigable**: Menú interactivo con navegación numérica
- 💬 **Generador de Descripciones**: Crea textos de venta profesionales para Mercado Libre
- 📋 **Copia al Portapapeles**: Copia automática de descripciones listas para pegar

## 📋 Requisitos

- Python 3.7 o superior
- Rich (para interfaz de terminal)
- Pyperclip (para copiar al portapapeles, opcional)

## 🔧 Instalación

1. Clona o descarga este repositorio:
```bash
git clone <tu-repo-url>
cd gestor-productos
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

O manualmente:
```bash
pip install rich pyperclip
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
- **Nombre** (descripción del producto)
- **Largo** (centímetros)
- **Ancho** (centímetros)
- **Alto** (centímetros)
- **Precio** ($)

### 2. Listar Productos
Muestra todos los productos en una tabla formateada que incluye:
- ID
- Nombre
- Dimensiones (largo, ancho, alto)
- Precio
- Volumen calculado (largo × ancho × alto)

### 3. Modificar Producto
Actualiza los datos de un producto existente. Muestra los valores actuales y permite mantenerlos presionando Enter.

### 4. Eliminar Producto
Elimina un producto de la base de datos (con confirmación).

### 5. Generar Descripción de Venta 🆕
Genera automáticamente descripciones profesionales y amigables para tus publicaciones de Mercado Libre:
- ✨ Formatea las medidas de forma clara y profesional
- 🎲 Agrega una nota aleatoria de venta (20 mensajes creativos disponibles)
- 📋 Copia la descripción al portapapeles automáticamente
- 💬 Formato optimizado para respuestas a clientes

**Ejemplo de descripción generada:**
```
¡Hola! Te presento este excelente Mueble de Roble 😊

📏 Medidas:
   • Largo: 150.0 cm
   • Ancho: 80.0 cm
   • Alto: 45.0 cm

💰 Precio: $25000.00

🌟 Calidad premium garantizada, no te vas a arrepentir de esta compra

¡Cualquier consulta no dudes en preguntar! Estoy para ayudarte 🙌
```

### 6. Salir
Cierra la aplicación de forma segura.

## 💾 Base de Datos

El archivo `products.db` se crea automáticamente en la primera ejecución y contiene:

**Tabla: products**
| Campo  | Tipo    | Descripción              |
|--------|---------|--------------------------|
| id     | INTEGER | ID autoincremental (PK)  |
| nombre | TEXT    | Nombre del producto      |
| largo  | REAL    | Largo en centímetros     |
| ancho  | REAL    | Ancho en centímetros     |
| alto   | REAL    | Alto en centímetros      |
| precio | REAL    | Precio en pesos/dólares  |

**Tabla: sales_notes**
| Campo | Tipo    | Descripción                          |
|-------|---------|--------------------------------------|
| id    | INTEGER | ID autoincremental (PK)              |
| nota  | TEXT    | Mensaje de venta aleatorio (UNIQUE)  |

La tabla `sales_notes` contiene 20 mensajes creativos que se agregan aleatoriamente a las descripciones de venta.

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
│ [5] 💬 Generar Descripción de Venta│
│ [6] 🚪 Salir                       │
╰────────────────────────────────────╯
```

### Tabla de Productos
```
                          📦 Lista de Productos
┏━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ ID ┃ Nombre        ┃ Largo (cm) ┃ Ancho (cm) ┃ Alto (cm) ┃ Precio ($)┃ Volumen (cm³)┃
┡━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ 1  │ Mesa Roble    │     200.00 │     150.00 │     80.00 │    150.00 │   2400000.00 │
│ 2  │ Estantería    │     350.00 │     200.00 │    120.00 │    280.50 │   8400000.00 │
└────┴───────────────┴────────────┴────────────┴───────────┴───────────┴──────────────┘
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
