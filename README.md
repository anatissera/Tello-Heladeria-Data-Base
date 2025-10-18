# TP1 - Bases de Datos (Heladería)

Este proyecto implementa el esquema de base de datos, carga inicial de datos y scripts auxiliares para la gestión de pedidos en la heladería.

---

## Requisitos previos

- **Supabase**: proyecto creado.
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
├── scripts/preprocess/ # scripts de preprocesamiento de datos de pedidos
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
│ ├── processed/ # salida procesados para cargar
│ │ ├── pedidos_suc_catam1.csv, pedidos_suc_catam2.csv, ...
│ │ ├── pedidos_suc_monteagudo1.csv, ...
│ │ ├── pedidos_suc_sept1.csv, ...
│ │ └── pedidos_suc_yerba1.csv, ...
│ │
│ ├── fake/ # para simulación
│ │ ├── administradores.csv
│ │ ├── empleados.csv
│ │ ├── provedores.csv
│ │ └── usuarios.csv
│ │
│ ├── categorias.csv
│ ├── familias.csv
│ └── productos.csv
│
├── scripts/ 
│ ├── generate/ # scripts para generar datos de prueba
│ │ └── generar_usuarios.py 
│ │ 
│ ├── load_to_db/ # scripts para cargar datos a la BD
│ │ ├── 0_cargar_schema.py
│ │ ├── 1_cargar_categorias.py
│ │ ├── 2_cargar_familias.py
│ │ ├── 3_cargar_productos.py
│ │ ├── 4_cargar_sucursales.py
│ │ ├── 5_cargar_usuarios.py
│ │ └── 6_cargar_pedidos.py
│
├── sql/
│ ├── schema.sql # esquema completo de la BD
│ └── sucursales.sql # datos iniciales de sucursales
│
├── .env # contiene SUPABASE_DB_URL con la conexión
├── manage_load.sh # script para ejecutar todo automáticamente
├── README.md # este archivo
├── requirements.txt # dependencias
└── Trabajo Práctico Grupal - Enunciado.pdf
```

---

## Paso 1 - Preprocesar CSVs (en este caso, todos los raw están processed → saltear)

El script `scripts/preprocess/procesar_csvs.py` convierte los archivos **raw** (originales de cada sucursal) en archivos **procesados** listos para cargar en la base.

### Modo de uso

```bash
# Procesar TODOS los archivos en data/raw/
python scripts/preprocess/procesar_csvs.py --mode all
# o simplemente:
python scripts/preprocess/procesar_csvs.py --mode 0
```

Esto genera automáticamente un archivo `pedidos_suc_<nombre>.csv` para cada archivo en `data/raw/`, y los guardará en `data/processed/`.

---

#### Procesar un solo archivo (modo single)

Si querés procesar solo uno (por ejemplo `yerba1.csv`):

```bash
python scripts/preprocess/procesar_csvs.py --mode single --raw-path data/raw/yerba1.csv
```

Esto genera `data/processed/pedidos_suc_yerba1.csv`.

También se puede especificar un nombre de salida personalizado:

```bash
python scripts/preprocess/procesar_csvs.py --mode single     --raw-path data/raw/yerba1.csv     --out-path data/processed/pedidos_suc_test.csv
```

Y si no pasás ningún argumento, el script pregunta interactivamente:

```
Seleccioná modo:
  0 -> procesar TODOS los archivos
  1 -> procesar UN archivo
Ingrese 0 o 1:
```

---

## Paso 2 - Crear esquema y cargar datos automáticamente con `manage_load.sh`

En lugar de ejecutar cada script de carga a mano, el repositorio incluye un script principal llamado `manage_load.sh` (ubicado en la raíz).

### Modo de uso

```bash
# Solo crear el schema
./manage_load.sh schema
# o
./manage_load.sh 0

# Solo cargar los datos (asumiendo que el schema ya existe)
./manage_load.sh data
# o
./manage_load.sh 1

# Crear schema y luego cargar todos los datos (recomendado)
./manage_load.sh all
# o
./manage_load.sh 2
```

### Qué hace cada modo

| Modo | Acción |
|------|--------|
| `0` o `schema` | Ejecuta `psql "$SUPABASE_DB_URL" -f sql/schema.sql`. Esto crea las tablas, restricciones y triggers |
| `1` o `data` | Ejecuta todos los scripts `cargar_*.py` en orden. Para esto, el esquema ya tiene que estar creado |
| `2` o `all` | Ejecuta schema + todos los scripts de carga |

### Scripts que ejecuta en orden
Cada script lee los CSV y hace inserts en las tablas correspondientes:

1. **`1_cargar_categorias.py`** → carga `categorias.csv` en `app.categoria`
2. **`2_cargar_familias.py`** → carga `familias.csv` en `app.familia`
3. **`3_cargar_productos.py`** → carga `productos.csv` en `app.producto`, enlazando con categoría/familia
4. **`4_cargar_sucursales.py`** → crea sucursales desde `sql/sucursales.sql`
5. **`5_cargar_usuarios.py`** → genera usuarios base por sucursal:
   - empleados (marcando encargados activos),
   - administradores activos,
   - proveedores.
6. **`6_cargar_pedidos.py`** → crea los **pedidos** (`app.pedido`) y sus **ítems asociados** (`app.contiene`) a partir de los archivos procesados en `data/processed/`.
   - este permite dos modos de ejecución:
      | Modo | Descripción |
      |------|--------------|
      | **`random`** *(por defecto)* | Simula un flujo realista de pedidos con decisiones automáticas:<br>– Crea algunos pedidos en estado `emitido` (pendientes).<br>– Asigna aleatoriamente administradores activos para aprobar o cancelar pedidos (según la lógica de triggers del schema).<br>– Inserta entregas para algunos pedidos aprobados, lo que actualiza automáticamente su estado a `entregado`.<br>Este modo sirve para **probar el flujo completo**: emisión, aprobación, cancelación y entrega. |
      | **`emit_all`** | Crea **todos los pedidos en estado `emitido`**, sin asignar administradores ni insertar entregas.<br>No dispara ninguna transición de estado: los pedidos quedan listos para ser aprobados o procesados más adelante desde la base de datos o la aplicación. |

      #### Uso

      ```bash
      # Modo por defecto (random / simulación)
      python scripts/load_to_db/cargar_pedidos.py

      # Modo explícito (simulado)
      python scripts/load_to_db/cargar_pedidos.py --mode random

      # Modo simple (solo emitir todos los pedidos)
      python scripts/load_to_db/cargar_pedidos.py --mode emit_all
      ```


### Personalización

Si querés usar un entorno Python específico (por ejemplo de Anaconda):

```bash
PYTHON=/ruta/a/python ./manage_load.sh all
```
---

## Checklist de ejecución

1. Configurar `.env` con `SUPABASE_DB_URL`.  
2. (Opcional) Preprocesar CSVs con `python scripts/preprocess/procesar_csvs.py`.  
3. Ejecutar `./manage_load.sh all` para crear el schema y cargar todos los datos.  

---

Proyecto realizado para **TP1 - I312 Bases de Datos (UdeSA, 2025)**.
