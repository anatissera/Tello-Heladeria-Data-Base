# TP1 - Bases de Datos (Heladería)

Este proyecto implementa el esquema de base de datos, carga inicial de datos y scripts auxiliares para la gestión de pedidos en la heladería.

---

## Requisitos previos

- **Supabase**: tener un proyecto creado (ej: https://supabase.com/dashboard/).
- **Python 3.11+** con las dependencias instaladas (ver `requirements.txt`).
- **psql** (cliente de PostgreSQL) accesible en el PATH.
- Archivo `.env` con la variable de conexión:

```bash
SUPABASE_DB_URL=postgresql://usuario:password@host:puerto/base?sslmode=require
```

---

## Estructura de carpetas

```
TP1-Bases_de_Datos/
│
├── scripts/preprocess/ # scripts de preprocesamiento de datos de pedidos crudos
│ ├── chequeo_paso_csv.py
│ └── procesar_csvs.py
│
├── data/
│ ├── raw/ # datos crudos de la heladería (archivos originales)
│ │ ├── catam1.csv, catam2.csv, ...
│ │ ├── monteagudo1.csv, ...
│ │ ├── sept1.csv, ...
│ │ ├── yerba1.csv, ...
│ │
│ ├── processed/ # salida normalizada lista para cargar
│ │ ├── pedidos_suc_catam1.csv
│ │ ├── pedidos_suc_catam2.csv
│ │ ├── pedidos_suc_monteagudo1.csv
│ │ ├── pedidos_suc_sept1.csv
│ │ ├── pedidos_suc_yerba1.csv
│ │ └── ...
│ │
│ ├── fake/ # sets para simulación
│ │ ├── administradores.csv
│ │ ├── empleados.csv
│ │ ├── provedores.csv
│ │ └── usuarios.csv
│ │
│ ├── categorias.csv
│ ├── familias.csv
│ └── productos.csv
│
├── scripts/ # scripts de carga incremental
│ ├── cargar_categorias.py
│ ├── cargar_familias.py
│ ├── cargar_productos.py
│ ├── cargar_sucursales.py
│ ├── cargar_usuarios.py
│ ├── cargar_pedidos.py
│ └── generar_usuarios.py
│
├── sql/ # SQL principal y auxiliares
│ ├── schema.sql # esquema completo de la BD
│ ├── sucursales.sql # datos iniciales de sucursales
│ └── entregar_pedidos.sql # script para marcar pedidos como entregados
│
├── .env # contiene SUPABASE_DB_URL con la conexión
├── README.md # este archivo
└── Trabajo Práctico Grupal.pdf
```

---

## Paso 1 - Crear esquema

Primero ejecutar en Supabase el script que crea las tablas, restricciones y triggers:

```bash
psql "$SUPABASE_DB_URL" -f sql/schema.sql
```

Esto genera todas las tablas (`usuario`, `sucursal`, `pedido`, `contiene`, `entrega`, etc.) siguiendo el modelo relacional diseñado.

---

## Paso 2 - Preprocesar CSVs

Los archivos crudos están en `data/raw/`. Para normalizar encabezados, separar categoría/familia y homogeneizar sucursales:

```bash
python scripts/preprocess/procesar_csvs.py
```

El resultado queda en `data/processed/` (un archivo por pedido, con nombre `pedidos_suc_<sucursal><n>.csv`), además de `productos.csv`, `categorias.csv` y `familias.csv`.

---

## Paso 3 - Cargar datos (scripts)

La carga de datos se hace en este **orden**, desde la carpeta `scripts/`. Cada script lee los CSV y hace inserts en las tablas correspondientes:

1. **`cargar_categorias.py`** → carga `categorias.csv` en `app.categoria`  
2. **`cargar_familias.py`** → carga `familias.csv` en `app.familia`  
3. **`cargar_productos.py`** → carga `productos.csv` en `app.producto`, enlazando con categoría/familia  
4. **`cargar_sucursales.py`** → crea sucursales desde `sql/sucursales.sql`  
5. **`cargar_usuarios.py`** → genera usuarios base por sucursal:  
   - empleados (marcando encargados activos),  
   - administradores activos,  
   - proveedores.  
6. **`cargar_pedidos.py`** → recorre `data/processed/` y:  
   - crea un `pedido` por archivo, con estado inicial `emitido`,  
   - inserta sus ítems en `contiene`,  
   - asigna automáticamente empleado encargado y administrador válidos para la sucursal,  
   - valida integridad (empleado debe ser encargado activo de la misma sucursal, admin activo de esa sucursal),  
   - asegura que existan previamente `producto` y `pedido` antes de insertar en `contiene`.  

🔎 Notas importantes:  
- Si un `pedido` cambia a estado `entregado`, debe existir en `entrega`.  
- No puede crearse una `entrega` si el `pedido` está cancelado.  
- Insertar una `entrega` actualiza automáticamente el estado del pedido a `entregado`.  

Ejemplo de ejecución:

```bash
python scripts/cargar_categorias.py
python scripts/cargar_familias.py
python scripts/cargar_productos.py
python scripts/cargar_sucursales.py
python scripts/cargar_usuarios.py
python scripts/cargar_pedidos.py
```

---

## Paso 4 - Marcar pedidos como entregados / preparados

Una vez cargados los pedidos, se puede usar el script SQL `entregar_pedidos.sql` para mover pedidos a otros estados (`entregado`, `preparado`, `emitido`, `cancelado`).  
Ejemplo de configuración dentro del archivo:

```sql
WITH params AS (
  SELECT
    ARRAY[2,3,4]::int[] AS delivered_ids,
    ARRAY[5,10]::int[]  AS prepared_ids,
    ARRAY[6]::int[]     AS emitted_ids,
    ARRAY[]::int[]      AS canceled_ids
)
```

Al correrlo:

```bash
psql "$SUPABASE_DB_URL" -f sql/entregar_pedidos.sql
```

Se insertan las entregas faltantes y se actualiza automáticamente el estado de los pedidos seleccionados.

---

## ✅ Checklist de ejecución

1. Configurar `.env` con `SUPABASE_DB_URL`.  
2. Ejecutar `schema.sql` en Supabase.  
3. Preprocesar CSVs con `procesar_csvs.py`.  
4. Correr los scripts en orden (`cargar_*`).  
5. Usar `entregar_pedidos.sql` para mover pedidos de estado y generar entregas.  

---

👨‍💻 Proyecto realizado para **TP1 - I312 Bases de Datos (UdeSA, 2025)**.
