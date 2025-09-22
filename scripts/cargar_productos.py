#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cargar_productos.py
Carga productos desde un CSV a app.producto.
- CSV esperado: columnas (nombre, categoria, familia) (headers sin importar mayúsculas/minúsculas)
- Crea categorías/familias que no existan todavía.
- Inserta productos con ON CONFLICT DO NOTHING contra uq_producto.

Uso:
  python scripts/cargar_productos.py --csv data/catalog/productos.csv
"""

import os
import sys
import argparse
import pandas as pd
import psycopg2
import psycopg2.extras as extras
from dotenv import load_dotenv

def norm(s):
    if s is None:
        return None
    s = str(s).strip()
    return s if s != "" else None

def load_csv(path):
    df = pd.read_csv(path)
    # Normalizamos nombres de columnas (case-insensitive) a [nombre, categoria, familia]
    cols = {c.lower().strip(): c for c in df.columns}
    # sinónimos por si cambian headers
    aliases = {
        "nombre": ["nombre", "producto", "producto_nombre", "nombre_prod"],
        "categoria": ["categoria", "cat", "categoria_nombre"],
        "familia": ["familia", "fam", "familia_nombre"],
    }
    def pick(colkey):
        for k in aliases[colkey]:
            if k in cols:
                return cols[k]
        raise KeyError(f"No se encontró columna para '{colkey}' en el CSV. Headers={list(df.columns)}")

    df = df[[pick("nombre"), pick("categoria"), pick("familia")]].copy()
    df.columns = ["nombre", "categoria", "familia"]

    # Trim + drop filas inválidas
    df["nombre"] = df["nombre"].map(norm)
    df["categoria"] = df["categoria"].map(norm)
    df["familia"] = df["familia"].map(norm)
    df = df.dropna(subset=["nombre", "categoria", "familia"]).drop_duplicates()
    return df

def get_conn():
    load_dotenv()
    url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: No encontré SUPABASE_DB_URL ni DATABASE_URL en tu .env", file=sys.stderr)
        sys.exit(1)
    return psycopg2.connect(url)

def fetch_lookup(conn, table, id_col, name_col):
    with conn.cursor() as cur:
        cur.execute(f"SELECT {id_col}, {name_col} FROM app.{table};")
        rows = cur.fetchall()
    # dict por nombre case-insensitive
    return {r[1].strip().lower(): r[0] for r in rows if r[1]}

def get_or_create_ids(conn, names, table, id_col, name_col):
    """
    Devuelve dict name_lower -> id, creando los que falten.
    """
    lk = fetch_lookup(conn, table, id_col, name_col)
    missing = [n for n in names if n.lower() not in lk]

    if missing:
        # Insert masivo con ON CONFLICT DO NOTHING
        with conn.cursor() as cur:
            extras.execute_values(
                cur,
                f"INSERT INTO app.{table}({name_col}) VALUES %s ON CONFLICT ({name_col}) DO NOTHING;",
                [(m,) for m in missing],
                page_size=1000
            )
        conn.commit()
        # Refrescar lookup
        lk = fetch_lookup(conn, table, id_col, name_col)

    return {n.lower(): lk[n.lower()] for n in names}

def insert_products(conn, rows, cat_ids, fam_ids):
    """
    rows: lista de tuplas (nombre, categoria, familia)
    cat_ids/fam_ids: dict name_lower -> id
    """
    to_ins = []
    for nombre, categoria, familia in rows:
        ckey = categoria.strip().lower()
        fkey = familia.strip().lower()
        cid = cat_ids.get(ckey)
        fid = fam_ids.get(fkey)
        if not cid or not fid:
            # Esto no debería pasar porque los creamos antes, pero por si acaso:
            continue
        to_ins.append((nombre.strip(), cid, fid))

    if not to_ins:
        return 0

    sql = """
    INSERT INTO app.producto (nombre, id_categoria, id_familia)
    VALUES %s
    ON CONFLICT ON CONSTRAINT uq_producto DO NOTHING;
    """
    with conn.cursor() as cur:
        extras.execute_values(cur, sql, to_ins, page_size=1000)
    conn.commit()
    return len(to_ins)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/catalog/productos.csv", help="Ruta al CSV de productos")
    args = ap.parse_args()

    df = load_csv(args.csv)
    if df.empty:
        print("Nada para insertar: el CSV no tiene filas válidas (nombre,categoria,familia).")
        return

    conn = get_conn()
    try:
        # Preparamos listas únicas de nombres
        categorias = sorted(set(df["categoria"].dropna().map(str).map(str.strip)))
        familias   = sorted(set(df["familia"].dropna().map(str).map(str.strip)))

        # Creamos/obtenemos IDs
        cat_ids = get_or_create_ids(conn, categorias, "categoria", "id_categoria", "nombre")
        fam_ids = get_or_create_ids(conn, familias,   "familia",   "id_familia",   "nombre")

        # Insert de productos
        inserted = insert_products(conn, df[["nombre","categoria","familia"]].itertuples(index=False, name=None),
                                   cat_ids, fam_ids)
        print(f"Intenté insertar {inserted} productos (los existentes se ignoraron por ON CONFLICT).")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
