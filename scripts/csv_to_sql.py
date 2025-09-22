#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
CSV_DIR = ROOT / "data"
PROCESSED_DIR = CSV_DIR / "processed"
SEED_PATH = SQL_DIR / "seed.sql"

ALIASES = {
    "sucursal":      {"sucursal", "suc", "id_sucursal", "store"},
    "producto":      {"producto", "producto_nombre", "item", "nombre_producto", "prod"},
    "categoria":     {"categoria", "cat", "categoria_nombre", "nombre_cat"},
    "familia":       {"familia", "fam", "familia_nombre", "nombre_fam"},
    "cantidad":      {"cantidad", "cant", "qty", "unidades"},
    "fecha_emision": {"fecha_emision", "fecha", "fecha_pedido", "emision", "timestamp"},
    "dni_empleado":  {"dni_empleado", "empleado_dni", "dniemp", "dni_emp"},
    "dni_admin":     {"dni_admin", "admin_dni", "dniadm", "dni_adm", "dni_aprobador"},
    "producto_id":   {"producto_id", "id_producto_ext", "id_prod"},
}

CANON = ["sucursal","producto","categoria","familia","cantidad","fecha_emision","dni_empleado","dni_admin"]

def norm(s: str) -> str:
    return s.strip().lower()

def read_header(csv_path: Path):
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        return next(r)

def map_header_to_canon(header):
    out = {}
    for h in header:
        hn = norm(h)
        for canon, aliases in ALIASES.items():
            if hn in aliases and canon not in out:
                out[canon] = h
                break
    return out  # {canon: real_name}

def posix(p: Path) -> str:
    return str(p.resolve()).replace("\\", "/")

def main():
    productos_csv = CSV_DIR / "productos.csv"
    pedido_files = sorted(PROCESSED_DIR.glob("*.csv"))
    if not productos_csv.exists():
        raise SystemExit(f"No existe {productos_csv}")
    if not pedido_files:
        raise SystemExit(f"No hay CSVs en {PROCESSED_DIR}")

    lines = []
    # STAGING bases
    lines += [
        "-- === STAGING (carga cruda desde CSV) ===",
        "CREATE SCHEMA IF NOT EXISTS staging;",
        "",
        "-- productos crudos",
        "DROP TABLE IF EXISTS staging.productos_raw;",
        "CREATE TABLE staging.productos_raw(",
        "  id_ext    TEXT,",
        "  nombre    TEXT,",
        "  categoria TEXT,",
        "  familia   TEXT",
        ");",
        "",
        "-- pedidos crudos canon (una fila por item) - todo TEXT",
        "DROP TABLE IF EXISTS staging.pedidos_raw;",
        "CREATE TABLE staging.pedidos_raw(",
        "  sucursal      TEXT,",
        "  producto      TEXT,",
        "  categoria     TEXT,",
        "  familia       TEXT,",
        "  cantidad      TEXT,",
        "  fecha_emision TEXT,",
        "  dni_empleado  TEXT,",
        "  dni_admin     TEXT",
        ");",
        "",
        f"\\copy staging.productos_raw(id_ext,nombre,categoria,familia) FROM '{posix(productos_csv)}' CSV HEADER;",
        "",
        "-- === Cargar TODOS los pedidos desde processed/ ===",
    ]

    tmp_idx = 0
    for f in pedido_files:
        header = read_header(f)
        mapping = map_header_to_canon(header)

        # columnas básicas de producto
        col_prod = mapping.get("producto")
        col_cat  = mapping.get("categoria")
        col_fam  = mapping.get("familia")
        if not (col_prod and col_cat and col_fam):
            raise SystemExit(f"{f.name}: faltan columnas de producto/categoria/familia en headers={header}")

        # detectar si trae sucursal+cantidad (formato largo)
        has_sucursal = "sucursal" in mapping
        has_cantidad = "cantidad" in mapping

        tmp_idx += 1
        tname = f"staging.tmp_{tmp_idx}"

        # 1) crear tmp con todas las columnas reales como TEXT
        cols_def = ", ".join([f"\"{h}\" TEXT" for h in header])
        lines += [
            f"-- {f.name} -> tmp + mapeo por nombre",
            f"DROP TABLE IF EXISTS {tname};",
            f"CREATE TABLE {tname} ({cols_def});",
            f"\\copy {tname} FROM '{posix(f)}' CSV HEADER;",
        ]

        if has_sucursal and has_cantidad:
            # 2A) LARGO: insert directo seleccionando columnas por nombre
            sel_suc = f"NULLIF(TRIM(t.\"{mapping['sucursal']}\"),'')"
            sel_prod = f"NULLIF(TRIM(t.\"{col_prod}\"),'')"
            sel_cat  = f"NULLIF(TRIM(t.\"{col_cat}\"),'')"
            sel_fam  = f"NULLIF(TRIM(t.\"{col_fam}\"),'')"
            sel_cant = f"NULLIF(TRIM(t.\"{mapping['cantidad']}\"),'')"
            sel_fecha = f"NULLIF(TRIM(t.\"{mapping['fecha_emision']}\"),'')" if "fecha_emision" in mapping else "NULL"
            sel_emp   = f"NULLIF(TRIM(t.\"{mapping['dni_empleado']}\"),'')"  if "dni_empleado" in mapping else "NULL"
            sel_adm   = f"NULLIF(TRIM(t.\"{mapping['dni_admin']}\"),'')"     if "dni_admin" in mapping else "NULL"

            lines += [
                "INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)",
                "SELECT",
                f"  {sel_suc} AS sucursal,",
                f"  {sel_prod} AS producto,",
                f"  {sel_cat}  AS categoria,",
                f"  {sel_fam}  AS familia,",
                f"  {sel_cant} AS cantidad,",
                f"  {sel_fecha} AS fecha_emision,",
                f"  {sel_emp} AS dni_empleado,",
                f"  {sel_adm} AS dni_admin",
                f"FROM {tname} t",
                "WHERE COALESCE(NULLIF(TRIM(" + (f"t.\"{mapping['cantidad']}\"" ) + "),'')::int, 0) > 0;",
                ""
            ]
        else:
            # 2B) ANCHO: UNPIVOT todas las columnas que NO son conocidas
            known = {mapping.get(k) for k in ["producto","categoria","familia","fecha_emision","dni_empleado","dni_admin","producto_id","cantidad","sucursal"]}
            known = {k for k in known if k}
            suc_cols = [h for h in header if h not in known]
            if not suc_cols:
                raise SystemExit(f"{f.name}: no detecté columnas de sucursal (formato ancho) en headers={header}")

            values_rows = ", ".join([f"('{sc}', NULLIF(TRIM(t.\"{sc}\"),''))" for sc in suc_cols])

            sel_prod = f"NULLIF(TRIM(t.\"{col_prod}\"),'')"
            sel_cat  = f"NULLIF(TRIM(t.\"{col_cat}\"),'')"
            sel_fam  = f"NULLIF(TRIM(t.\"{col_fam}\"),'')"

            lines += [
                "INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)",
                "SELECT v.sucursal,",
                f"       {sel_prod} AS producto,",
                f"       {sel_cat}  AS categoria,",
                f"       {sel_fam}  AS familia,",
                "       v.cantidad,",
                "       NULL AS fecha_emision,",
                "       NULL AS dni_empleado,",
                "       NULL AS dni_admin",
                f"FROM {tname} t",
                "CROSS JOIN LATERAL (",
                f"  VALUES {values_rows}",
                ") AS v(sucursal, cantidad)",
                "WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';",
                ""
            ]

    # === resto del seed igual que antes (dimensiones, productos, sucursales, usuarios, pedidos, contiene)
    lines += [
        "",
        "-- === DIMENSIONES ===",
        "INSERT INTO app.categoria(nombre)",
        "SELECT DISTINCT TRIM(categoria) FROM staging.productos_raw WHERE NULLIF(TRIM(categoria),'') IS NOT NULL",
        "ON CONFLICT (nombre) DO NOTHING;",
        "",
        "INSERT INTO app.categoria(nombre)",
        "SELECT DISTINCT TRIM(categoria) FROM staging.pedidos_raw WHERE NULLIF(TRIM(categoria),'') IS NOT NULL",
        "ON CONFLICT (nombre) DO NOTHING;",
        "",
        "INSERT INTO app.familia(nombre)",
        "SELECT DISTINCT TRIM(familia) FROM staging.productos_raw WHERE NULLIF(TRIM(familia),'') IS NOT NULL",
        "ON CONFLICT (nombre) DO NOTHING;",
        "",
        "INSERT INTO app.familia(nombre)",
        "SELECT DISTINCT TRIM(familia) FROM staging.pedidos_raw WHERE NULLIF(TRIM(familia),'') IS NOT NULL",
        "ON CONFLICT (nombre) DO NOTHING;",
        "",
        "-- Productos desde productos.csv",
        "INSERT INTO app.producto(nombre, id_categoria, id_familia)",
        "SELECT DISTINCT TRIM(p.nombre), c.id_categoria, f.id_familia",
        "FROM staging.productos_raw p",
        "JOIN app.categoria c ON c.nombre = TRIM(p.categoria)",
        "JOIN app.familia   f ON f.nombre = TRIM(p.familia)",
        "WHERE NULLIF(TRIM(p.nombre),'') IS NOT NULL",
        "ON CONFLICT (nombre, id_categoria, id_familia) DO NOTHING;",
        "",
        "-- Productos que aparezcan solo en pedidos",
        "INSERT INTO app.producto(nombre, id_categoria, id_familia)",
        "SELECT DISTINCT TRIM(r.producto), c.id_categoria, f.id_familia",
        "FROM staging.pedidos_raw r",
        "JOIN app.categoria c ON c.nombre = TRIM(r.categoria)",
        "JOIN app.familia   f ON f.nombre = TRIM(r.familia)",
        "WHERE NULLIF(TRIM(r.producto),'') IS NOT NULL",
        "ON CONFLICT (nombre, id_categoria, id_familia) DO NOTHING;",
        "",
        "-- SUCURSALES (dirección inline)",
        "INSERT INTO app.sucursal (nombre, calle, numero, piso, depto, localidad, cp)",
        "SELECT DISTINCT",
        "  INITCAP(pr.sucursal),",
        "  'Av. ' || INITCAP(pr.sucursal),",
        "  1, NULL, NULL, INITCAP(pr.sucursal), '0000'",
        "FROM staging.pedidos_raw pr",
        "WHERE NULLIF(TRIM(sucursal),'') IS NOT NULL",
        "ON CONFLICT DO NOTHING;",
        "",
        "-- USUARIOS (si vienen en largo)",
        "INSERT INTO app.usuario(dni, nombre, id_suc, activo)",
        "SELECT DISTINCT pr.dni_empleado, 'Empleado '||pr.dni_empleado, s.id_suc, TRUE",
        "FROM staging.pedidos_raw pr JOIN app.sucursal s ON s.nombre = INITCAP(pr.sucursal)",
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
        "FROM staging.pedidos_raw pr JOIN app.sucursal s ON s.nombre = INITCAP(pr.sucursal)",
        "WHERE NULLIF(TRIM(pr.dni_admin),'') IS NOT NULL",
        "ON CONFLICT (dni) DO NOTHING;",
        "",
        "INSERT INTO app.administrador(dni)",
        "SELECT DISTINCT pr.dni_admin",
        "FROM staging.pedidos_raw pr",
        "WHERE NULLIF(TRIM(pr.dni_admin),'') IS NOT NULL",
        "ON CONFLICT (dni) DO NOTHING;",
        "",
        "-- Índice único para no duplicar cabeceras",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_pedido_natural",
        "ON app.pedido (id_suc, fecha_emision, dni_empleado, dni_admin);",
        "",
        "-- CABECERAS",
        "WITH cab AS (",
        "  SELECT DISTINCT s.id_suc,",
        "    NULLIF(TRIM(pr.fecha_emision),'') AS fecha_txt,",
        "    NULLIF(TRIM(pr.dni_empleado),'')  AS dni_empleado,",
        "    NULLIF(TRIM(pr.dni_admin),'')     AS dni_admin",
        "  FROM staging.pedidos_raw pr",
        "  JOIN app.sucursal s ON s.nombre = INITCAP(pr.sucursal)",
        ")",
        "INSERT INTO app.pedido(id_suc, fecha_emision, dni_empleado, dni_admin)",
        "SELECT id_suc,",
        "  CASE WHEN fecha_txt ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}( [0-9]{2}(:[0-9]{2})?)?$' THEN fecha_txt::timestamp",
        "       ELSE timestamp '2000-01-01 00:00:00' END,",
        "  dni_empleado, dni_admin",
        "FROM cab",
        "ON CONFLICT DO NOTHING;",
        "",
        "-- ÍTEMS (contiene)  (cantidad > 0)",
        "INSERT INTO app.contiene(id_producto, id_pedido, cantidad)",
        "SELECT p.id_producto, ped.id_pedido, NULLIF(TRIM(pr.cantidad),'')::int",
        "FROM staging.pedidos_raw pr",
        "JOIN app.categoria c ON c.nombre = TRIM(pr.categoria)",
        "JOIN app.familia   f ON f.nombre = TRIM(pr.familia)",
        "JOIN app.producto  p ON p.nombre = TRIM(pr.producto)",
        "                     AND p.id_categoria = c.id_categoria",
        "                     AND p.id_familia   = f.id_familia",
        "JOIN app.sucursal  s ON s.nombre = INITCAP(pr.sucursal)",
        "JOIN app.pedido   ped ON ped.id_suc = s.id_suc",
        "  AND ped.fecha_emision = CASE",
        "      WHEN NULLIF(TRIM(pr.fecha_emision),'') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}( [0-9]{2}(:[0-9]{2})?)?$' THEN pr.fecha_emision::timestamp",
        "      ELSE timestamp '2000-01-01 00:00:00'",
        "  END",
        "  AND (ped.dni_empleado IS NOT DISTINCT FROM NULLIF(TRIM(pr.dni_empleado),''))",
        "  AND (ped.dni_admin    IS NOT DISTINCT FROM NULLIF(TRIM(pr.dni_admin),''))",
        "WHERE COALESCE(NULLIF(TRIM(pr.cantidad),'')::int, 0) > 0;",
        "",
    ]

    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEED_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generado: {SEED_PATH}")

if __name__ == "__main__":
    main()
