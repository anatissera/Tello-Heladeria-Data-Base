# pasa de csv a tabla de sql para guardar en seed.sql

#!/usr/bin/env python3
# Genera sql/seed.sql desde data/catalog/productos.csv y data/processed/pedidos_suc_*.csv
# - Crea staging (tablas crudas)
# - Genera \copy para cargar CSV a staging
# - Hace UPSERTs a app.* según schema.sql (PostgreSQL)

import csv, re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "data"
PROCESSED = CSV_DIR / "processed"
SQL_DIR = ROOT / "sql"
SQL_DIR.mkdir(exist_ok=True)

SEED = SQL_DIR / "seed.sql"
PRODUCTOS_CSV = CSV_DIR / "productos.csv"

# -------- utilidades
def slug(x: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", x.strip().lower())

def infer_sucursal_from_filename(path: Path) -> str:
    # pedidos_suc_<sucursal>*.csv  -> devuelve <sucursal>
    m = re.search(r"pedidos_suc_([a-zA-Z0-9]+)", path.stem)
    return (m.group(1) if m else "desconocida").lower()

def pick_first(d: dict, keys):
    for k in keys:
        if k in d and d[k] not in ("", None):
            return d[k]
    return None

# -------- recolectar csv de pedidos
pedido_files = sorted(PROCESSED.glob("pedidos_suc_*.csv"))
if not pedido_files:
    raise SystemExit("No se encontraron CSV de pedidos en data/processed/*.csv")

# -------- preparar seed.sql
lines = []

# 1) staging
lines += [
    "-- === STAGING (carga cruda desde CSV) ===",
    "CREATE SCHEMA IF NOT EXISTS staging;",
    "",
    "-- productos crudos (nombre, categoria, familia)",
    "DROP TABLE IF EXISTS staging.productos_raw;",
    "CREATE TABLE staging.productos_raw(",
    "  nombre TEXT,",
    "  categoria TEXT,",
    "  familia TEXT",
    ");",
    "",
    "-- pedidos crudos (una fila por item)",
    "DROP TABLE IF EXISTS staging.pedidos_raw;",
    "CREATE TABLE staging.pedidos_raw(",
    "  sucursal TEXT,",
    "  fecha_emision TIMESTAMP,",
    "  dni_empleado TEXT,",
    "  dni_admin TEXT,",
    "  producto TEXT,",
    "  categoria TEXT,",
    "  familia TEXT,",
    "  cantidad INTEGER",
    ");",
    "",
]

# 2) \copy productos
if PRODUCTOS_CSV.exists():
    lines += [
        f"\\copy staging.productos_raw(nombre,categoria,familia) FROM '{PRODUCTOS_CSV.as_posix()}' CSV HEADER;",
        ""
    ]
else:
    lines += ["-- Aviso: productos.csv no encontrado; se omite carga de productos base.", ""]

# 3) Normalizar y unificar pedidos en UN SOLO CSV temporal que coincida con staging
tmp_unificado = PROCESSED / "_pedidos_unificado_tmp.csv"
with tmp_unificado.open("w", newline="", encoding="utf-8") as fout:
    w = csv.writer(fout)
    w.writerow(["sucursal","fecha_emision","dni_empleado","dni_admin","producto","categoria","familia","cantidad"])

    for fp in pedido_files:
        suc = infer_sucursal_from_filename(fp)
        with fp.open("r", newline="", encoding="utf-8") as fin:
            reader = csv.DictReader(fin)
            # Mapas de sinónimos (por si los headers varían)
            syn = {
                "fecha_emision": ["fecha_emision","fecha","fecha_pedido"],
                "dni_empleado":  ["dni_empleado","empleado_dni","dniemp","dni_emp"],
                "dni_admin":     ["dni_admin","admin_dni","dniadm","dni_adm","dni_aprobador"],
                "producto":      ["producto","producto_nombre","nombre_prod","prod","item","nombre_producto"],
                "categoria":     ["categoria","cat","nombre_cat","id_cat","categoria_nombre"],
                "familia":       ["familia","fam","nombre_fam","id_fam","familia_nombre"],
                "cantidad":      ["cantidad","qty","cant","unidades"],
            }
            for row in reader:
                # normalizar claves a lower-snake
                nr = {slug(k): v for k,v in row.items()}
                fecha = pick_first(nr, syn["fecha_emision"])
                # parseo básico de fecha si viene sin hora
                if fecha and re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
                    fecha = fecha + " 00:00:00"
                w.writerow([
                    suc,
                    fecha or "",
                    pick_first(nr, syn["dni_empleado"]) or "",
                    pick_first(nr, syn["dni_admin"]) or "",
                    pick_first(nr, syn["producto"]) or "",
                    pick_first(nr, syn["categoria"]) or "",
                    pick_first(nr, syn["familia"]) or "",
                    pick_first(nr, syn["cantidad"]) or "0"
                ])

# \copy unificado a staging
lines += [
    f"\\copy staging.pedidos_raw FROM '{tmp_unificado.as_posix()}' CSV HEADER;",
    ""
]

# 4) UPSERTs a app.* (requiere schema.sql ya ejecutado)
lines += [
    "-- === DIMENSIONES ===",
    "-- Categorías y Familias",
    "INSERT INTO app.categoria(nombre)",
    "SELECT DISTINCT TRIM(categoria) FROM staging.productos_raw WHERE NULLIF(TRIM(categoria),'') IS NOT NULL",
    "ON CONFLICT (nombre) DO NOTHING;",
    "",
    "INSERT INTO app.familia(nombre)",
    "SELECT DISTINCT TRIM(familia) FROM staging.productos_raw WHERE NULLIF(TRIM(familia),'') IS NOT NULL",
    "ON CONFLICT (nombre) DO NOTHING;",
    "",
    "-- Productos",
    "INSERT INTO app.producto(nombre, id_categoria, id_familia)",
    "SELECT DISTINCT",
    "  TRIM(p.nombre), c.id_categoria, f.id_familia",
    "FROM staging.productos_raw p",
    "JOIN app.categoria c ON c.nombre = TRIM(p.categoria)",
    "JOIN app.familia   f ON f.nombre = TRIM(p.familia)",
    "WHERE NULLIF(TRIM(p.nombre),'') IS NOT NULL",
    "ON CONFLICT (nombre, id_categoria, id_familia) DO NOTHING;",
    "",
    "-- También considerar categorías/familias que aparezcan en pedidos aunque no figuren en productos.csv",
    "INSERT INTO app.categoria(nombre)",
    "SELECT DISTINCT TRIM(categoria) FROM staging.pedidos_raw WHERE NULLIF(TRIM(categoria),'') IS NOT NULL",
    "ON CONFLICT (nombre) DO NOTHING;",
    "",
    "INSERT INTO app.familia(nombre)",
    "SELECT DISTINCT TRIM(familia) FROM staging.pedidos_raw WHERE NULLIF(TRIM(familia),'') IS NOT NULL",
    "ON CONFLICT (nombre) DO NOTHING;",
    "",
    "INSERT INTO app.producto(nombre, id_categoria, id_familia)",
    "SELECT DISTINCT",
    "  TRIM(r.producto), c.id_categoria, f.id_familia",
    "FROM staging.pedidos_raw r",
    "JOIN app.categoria c ON c.nombre = TRIM(r.categoria)",
    "JOIN app.familia   f ON f.nombre = TRIM(r.familia)",
    "WHERE NULLIF(TRIM(r.producto),'') IS NOT NULL",
    "ON CONFLICT (nombre, id_categoria, id_familia) DO NOTHING;",
    "",
    "-- === SUCURSALES (y direcciones dummy) ===",
    "INSERT INTO app.direccion(calle,numero,piso,depto,localidad,cp)",
    "SELECT DISTINCT",
    "  'Av. '||INITCAP(sucursal), 1, NULL, NULL, INITCAP(sucursal), '0000'",
    "FROM staging.pedidos_raw pr",
    "WHERE NULLIF(TRIM(sucursal),'') IS NOT NULL",
    "ON CONFLICT DO NOTHING;",
    "",
    "INSERT INTO app.sucursal(nombre, id_direccion)",
    "SELECT DISTINCT",
    "  INITCAP(pr.sucursal) AS nombre, d.id_direccion",
    "FROM staging.pedidos_raw pr",
    "JOIN app.direccion d ON d.localidad = INITCAP(pr.sucursal) AND d.cp='0000'",
    "ON CONFLICT DO NOTHING;",
    "",
    "-- === USUARIOS detectados en pedidos (empleados/admins con DNIs) ===",
    "INSERT INTO app.usuario(dni, nombre, id_suc, activo)",
    "SELECT DISTINCT pr.dni_empleado, 'Empleado '||pr.dni_empleado, s.id_suc, TRUE",
    "FROM staging.pedidos_raw pr",
    "JOIN app.sucursal s ON s.nombre = INITCAP(pr.sucursal)",
    "WHERE NULLIF(TRIM(pr.dni_empleado),'') IS NOT NULL",
    "ON CONFLICT (dni) DO NOTHING;",
    "",
    "INSERT INTO app.empleado(dni)",
    "SELECT DISTINCT pr.dni_empleado",
    "FROM staging.pedidos_raw pr",
    "WHERE NULLIF(TRIM(pr.dni_empleado),'') IS NOT NULL",
    "ON CONFLICT (dni) DO NOTHING;",
    "",
    "INSERT INTO app.usuario(dni, nombre, id_suc, activo)",
    "SELECT DISTINCT pr.dni_admin, 'Admin '||pr.dni_admin, s.id_suc, TRUE",
    "FROM staging.pedidos_raw pr",
    "JOIN app.sucursal s ON s.nombre = INITCAP(pr.sucursal)",
    "WHERE NULLIF(TRIM(pr.dni_admin),'') IS NOT NULL",
    "ON CONFLICT (dni) DO NOTHING;",
    "",
    "INSERT INTO app.administrador(dni)",
    "SELECT DISTINCT pr.dni_admin",
    "FROM staging.pedidos_raw pr",
    "WHERE NULLIF(TRIM(pr.dni_admin),'') IS NOT NULL",
    "ON CONFLICT (dni) DO NOTHING;",
    "",
    "-- === PEDIDOS (cabeceras) ===",
    "WITH cab AS (",
    "  SELECT DISTINCT",
    "    s.id_suc,",
    "    pr.fecha_emision,",
    "    NULLIF(TRIM(pr.dni_empleado),'') AS dni_empleado,",
    "    NULLIF(TRIM(pr.dni_admin),'')    AS dni_admin",
    "  FROM staging.pedidos_raw pr",
    "  JOIN app.sucursal s ON s.nombre = INITCAP(pr.sucursal)",
    ")",
    "INSERT INTO app.pedido(id_suc, fecha_emision, dni_empleado, dni_admin)",
    "SELECT id_suc,",
    "       COALESCE(fecha_emision, NOW()),",
    "       dni_empleado,",
    "       dni_admin",
    "FROM cab",
    "ON CONFLICT DO NOTHING;",
    "",
    "-- === Ítems del pedido (contiene) ===",
    "INSERT INTO app.contiene(id_producto, id_pedido, cantidad)",
    "SELECT p.id_producto, ped.id_pedido, CAST(pr.cantidad AS INTEGER)",
    "FROM staging.pedidos_raw pr",
    "JOIN app.categoria c ON c.nombre = TRIM(pr.categoria)",
    "JOIN app.familia   f ON f.nombre = TRIM(pr.familia)",
    "JOIN app.producto  p ON p.nombre = TRIM(pr.producto)",
    "                     AND p.id_categoria = c.id_categoria",
    "                     AND p.id_familia   = f.id_familia",
    "JOIN app.sucursal  s ON s.nombre = INITCAP(pr.sucursal)",
    "JOIN app.pedido   ped ON ped.id_suc = s.id_suc",
    "                      AND ped.fecha_emision = COALESCE(pr.fecha_emision, ped.fecha_emision)",
    "                      AND (ped.dni_empleado IS NOT DISTINCT FROM NULLIF(TRIM(pr.dni_empleado),''))",
    "                      AND (ped.dni_admin    IS NOT DISTINCT FROM NULLIF(TRIM(pr.dni_admin),''));",
    "",
    "-- Fin de seed generado automáticamente.",
]

SEED.write_text("\n".join(lines), encoding="utf-8")
print(f"Semilla generada en {SEED}")
