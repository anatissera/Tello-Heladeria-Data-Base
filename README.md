# Tello Heladerías: base de datos de pedidos

Base de datos para la gestión de pedidos de una cadena de heladerías de Tucumán,
con 8 sucursales. El repositorio contiene el modelo de datos, el esquema
PostgreSQL con sus reglas de negocio en triggers, y el pipeline que toma los
pedidos crudos de cada sucursal y los carga en Supabase.

Trabajo práctico de **I312 Bases de Datos**, Universidad de San Andrés, 2025.

## Modelo de datos

Del modelo entidad-relación al esquema relacional:

| Modelo E-R | Esquema en Supabase |
|:---:|:---:|
| [<img src="docs/modelo-er.png" alt="Modelo entidad-relación" width="400">](docs/modelo-er.png) | [<img src="docs/esquema-relacional.png" alt="Esquema relacional en Supabase" width="400">](docs/esquema-relacional.png) |

Once tablas bajo el esquema `app`:

| Tabla | Qué guarda |
|---|---|
| `sucursal` | Las 8 sucursales, con dirección desagregada en calle, número, piso, depto, localidad y CP. |
| `usuario` | Datos comunes a toda persona del sistema: DNI, nombre, fecha de nacimiento, mail, sucursal y si está activa. |
| `empleado`, `administrador`, `proveedor` | Los tres subtipos de `usuario`, modelados como tablas que heredan la PK. `empleado` agrega `es_encargado`. |
| `categoria`, `familia` | Clasificación de productos. Un producto tiene categoría obligatoria y familia opcional. |
| `producto` | El catálogo, 102 productos. |
| `pedido` | Cabecera del pedido: estado, fecha de emisión, sucursal, empleado que lo emite y administrador que lo aprueba o cancela. |
| `contiene` | Los ítems de cada pedido, con su cantidad. |
| `entrega` | La recepción del pedido: proveedor, empleado que recibe y fecha. |

El estado de un pedido es un enum: `emitido`, `aprobado`, `preparado`,
`entregado`, `cancelado`.

## Reglas de negocio

Lo que no se puede expresar con claves foráneas está resuelto con triggers, no
con validaciones en la aplicación. Las principales:

- Un pedido solo puede pasar de un estado al siguiente según el flujo permitido
  (`chk_pedido_flujo_estado`).
- Solo un administrador activo puede aprobar o cancelar un pedido, y tiene que
  pertenecer a la Casa Central (`chk_admin_central`, `pedido_validate_roles`).
- Los proveedores también pertenecen a la Casa Central (`chk_proveedor_central`).
- Una entrega solo se admite sobre un pedido que esté en un estado que lo
  permita, y el empleado que la recibe tiene que ser de la misma sucursal del
  pedido (`chk_entrega_permitida`, `chk_empleado_sucursal_entrega`).
- Insertar la entrega marca el pedido como `entregado` automáticamente
  (`auto_marcar_pedido_entregado`).
- Un usuario no puede tener dos roles incompatibles a la vez
  (`chk_roles_casa_central_usuario`).

## Estructura del repositorio

```
.
├── sql/
│   ├── schema.sql          esquema completo: tablas, constraints y triggers
│   └── sucursales.sql      las 8 sucursales
│
├── scripts/
│   ├── preprocess/         normalización de los CSV crudos
│   │   ├── procesar_csvs.py
│   │   └── chequeo_paso_csv.py
│   ├── generate/
│   │   └── generar_usuarios.py    datos sintéticos con Faker
│   └── load_to_db/         carga a Supabase, en orden
│       ├── 0_cargar_schema.py
│       ├── 1_cargar_categorias.py
│       ├── 2_cargar_familias.py
│       ├── 3_cargar_productos.py
│       ├── 4_cargar_sucursales.py
│       ├── 5_cargar_usuarios.py
│       └── 6_cargar_pedidos.py
│
├── data/
│   ├── raw/                16 archivos crudos, tal como los entregó cada sucursal
│   ├── processed/          los mismos, ya normalizados y listos para cargar
│   ├── catalog/            categorias.csv, familias.csv, productos.csv
│   └── fake/               usuarios, empleados, administradores y proveedores sintéticos
│
├── docs/
│   ├── modelo-er.png
│   ├── esquema-relacional.png
│   ├── informe.pdf         informe del trabajo práctico
│   └── enunciado.pdf       consigna original
│
├── manage_load.sh          corre el schema y todos los loaders
└── requirements.txt
```

## Los datos

Cada sucursal entregó sus pedidos en un formato distinto: nombres de columna que
no coinciden entre archivos, productos escritos de formas diferentes, fechas en
varios formatos. `scripts/preprocess/procesar_csvs.py` es el que absorbe ese
desorden: mapea los encabezados contra un conjunto de alias conocidos, resuelve
cada producto contra el catálogo maestro y emite un CSV uniforme.

Los 16 archivos de `data/raw/` corresponden a cuatro sucursales:

| Prefijo | Sucursal |
|---|---|
| `catam*` | Catamarca |
| `sept*` | Microcentro |
| `monteagudo*` | Barrio Norte |
| `yerba*` | Lobo de la Vega |

## Cómo correrlo

### Requisitos

- Un proyecto de **Supabase** creado.
- **Python 3.11+** con las dependencias de `requirements.txt`.
- **psql** accesible en el PATH.
- Un archivo `.env` en la raíz con la conexión:

```bash
SUPABASE_DB_URL=postgresql://usuario:password@host:puerto/base?sslmode=require
```

> El `.env` está en `.gitignore` y no debe versionarse nunca.

```bash
pip install -r requirements.txt
```

### Paso 1: preprocesar los CSV (opcional)

Los archivos de `data/processed/` ya están generados, así que este paso solo hace
falta si se agregan datos crudos nuevos.

```bash
# Todos los archivos de data/raw/
python scripts/preprocess/procesar_csvs.py --mode all

# Uno solo
python scripts/preprocess/procesar_csvs.py --mode single --raw-path data/raw/yerba1.csv

# Con nombre de salida propio
python scripts/preprocess/procesar_csvs.py --mode single \
    --raw-path data/raw/yerba1.csv \
    --out-path data/processed/pedidos_suc_test.csv
```

Sin argumentos, el script pregunta el modo de forma interactiva.

### Paso 2: crear el esquema y cargar todo

```bash
./manage_load.sh all      # schema + datos  (recomendado)
./manage_load.sh schema   # solo el schema
./manage_load.sh data     # solo los datos, asumiendo que el schema ya existe
```

También acepta `0`, `1` y `2` en lugar de `schema`, `data` y `all`.

Los loaders corren en orden: categorías, familias, productos, sucursales,
usuarios y por último pedidos con sus ítems.

### Modos de carga de pedidos

`6_cargar_pedidos.py` puede poblar los pedidos de dos maneras:

| Modo | Qué hace |
|---|---|
| `emit_all` *(default de `manage_load.sh`)* | Crea todos los pedidos en estado `emitido`. No dispara ninguna transición: quedan listos para procesarse después. |
| `random` | Simula el flujo realista completo: deja algunos pedidos pendientes, asigna administradores que aprueban o cancelan, e inserta entregas para algunos aprobados, lo que los marca como `entregado` vía trigger. Sirve para probar toda la máquina de estados. |

```bash
# Cambiar el modo que usa manage_load.sh
PEDIDOS_MODE=random ./manage_load.sh data

# O correr el script directamente
python scripts/load_to_db/6_cargar_pedidos.py --mode random
```

### Personalización

```bash
# Usar un intérprete específico (por ejemplo de Anaconda)
PYTHON=/ruta/a/python ./manage_load.sh all

# Indicar dónde está psql si no está en el PATH
PSQL=/opt/homebrew/bin/psql python scripts/load_to_db/6_cargar_pedidos.py
```

## Autoras

[Ana Paula Tissera](https://github.com/anatissera),
[Athina Salim](https://github.com/athinasalimm),
[Naomi Couriel](https://github.com/naomicouriel) y
[Ana Holcman](https://github.com/Anaholcman).
