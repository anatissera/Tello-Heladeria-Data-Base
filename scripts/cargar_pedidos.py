#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cargar_pedidos.py
Carga pedidos (cabeceras + ítems) desde un CSV con filas a nivel ítem.

- Crea/actualiza: sucursal (con dirección inline dummy), usuario/empleado/administrador,
  categoria, familia, producto.
- Inserta cabeceras de pedidos (evita duplicados buscando la cabecera antes de insertar).
- Inserta ítems (app.contiene) con ON CONFLICT DO NOTHING.

Uso:
  python scripts/cargar_pedidos.py --csv data/pedidos_suc_yerba1.csv
"""

import os, sys, csv, re
from datetime import datetime
from typing import Dict, Tuple, List, Optional
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

# ---- Config de sinónimos de columnas
ALIASES = {
    "sucursal":       ["sucursal", "id_sucursal", "suc"],
    "fecha_emision":  ["fecha_emision", "fecha", "fecha_pedido", "emision"],
    "dni_empleado":   ["dni_empleado", "empleado_dni", "dniemp", "dni_emp"],
    "dni_admin":      ["dni_admin", "admin_dni", "dniadm", "dni_adm", "dni_aprobador"],
    "producto":       ["producto", "producto_nombre", "nombre_prod", "item", "nombre_producto"],
    "categoria":      ["categoria", "cat", "categoria_nombre", "nombre_cat"],
    "familia":        ["familia", "fam", "familia_nombre", "nombre_fam"],
    "cantidad":       ["cantidad", "qty", "cant", "unidades"],
}

def norm(s: Optional[str]) -> Optional[str]:
    if s is None: return None
    s = str(s).strip()
    return s if s else None

def title_or_none(s: Optional[str]) -> Optional[str]:
    s = norm(s)
    return s.title() if s else None

def parse_datetime(s: Optional[str]) -> Optional[str]:
    """
    Devuelve string en formato 'YYYY-MM-DD HH:MM:SS' o None.
    Acepta 'YYYY-MM-DD' y completa '00:00:00'.
    """
    s = norm(s)
    if not s:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}$", s):
            return f"{s} 00:00:00"
        # intentar parseo más general
        try:
            dt = datetime.fromisoformat(s.replace("Z",""))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            # último intento: normalizar separadores
            return s
    except Exception:
        return None

def get_conn():
    load_dotenv()
    url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: faltan SUPABASE_DB_URL / DATABASE_URL en .env", file=sys.stderr)
        sys.exit(1)
    # forzar ssl
    if "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = url + f"{sep}sslmode=require"
    return psycopg2.connect(url)

def pick_header(headers_lower: Dict[str,str], keys: List[str]) -> Optional[str]:
    for k in keys:
        if k in headers_lower:
            return headers_lower[k]
    return None

def read_rows(csv_path: str) -> List[dict]:
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        headers_lower = {h.lower().strip(): h for h in r.fieldnames}

        col_suc   = pick_header(headers_lower, ALIASES["sucursal"])
        col_fecha = pick_header(headers_lower, ALIASES["fecha_emision"])
        col_dem   = pick_header(headers_lower, ALIASES["dni_empleado"])
        col_dad   = pick_header(headers_lower, ALIASES["dni_admin"])
        col_prod  = pick_header(headers_lower, ALIASES["producto"])
        col_cat   = pick_header(headers_lower, ALIASES["categoria"])
        col_fam   = pick_header(headers_lower, ALIASES["familia"])
        col_cant  = pick_header(headers_lower, ALIASES["cantidad"])

        need = [("sucursal", col_suc), ("fecha_emision", col_fecha),
                ("producto", col_prod), ("categoria", col_cat),
                ("familia", col_fam), ("cantidad", col_cant)]
        missing = [n for n,c in need if not c]
        if missing:
            raise SystemExit(f"CSV sin columnas requeridas: {missing}. Headers={list(r.fieldnames)}")

        out = []
        for row in r:
            suc = title_or_none(row.get(col_suc))
            fecha = parse_datetime(row.get(col_fecha))
            dni_emp = norm(row.get(col_dem)) if col_dem else None
            dni_adm = norm(row.get(col_dad)) if col_dad else None
            prod = norm(row.get(col_prod))
            cat  = norm(row.get(col_cat))
            fam  = norm(row.get(col_fam))
            try:
                cant = int(float(row.get(col_cant))) if row.get(col_cant) not in (None,"") else None
            except Exception:
                cant = None

            if not (suc and prod and cat and fam and cant is not None):
                # fila inválida -> salteamos
                continue
            out.append({
                "sucursal": suc,
                "fecha_emision": fecha,  # puede ser None -> se pone NOW() al insertar pedido
                "dni_empleado": dni_emp,
                "dni_admin": dni_adm,
                "producto": prod,
                "categoria": cat,
                "familia": fam,
                "cantidad": cant
            })
        return out

# --- Helpers DB lookups / upserts
def fetch_map(conn, sql, key_idx=0, val_idx=1) -> Dict:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return {rows[i][key_idx]: rows[i][val_idx] for i in range(len(rows))}

def ensure_sucursales(conn, nombres: List[str]) -> Dict[str,int]:
    # Insert sucursales con dirección inline dummy si no existen
    vals = sorted(set([n for n in nombres if n]))
    if not vals: return {}
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO app.sucursal (nombre, calle, numero, piso, depto, localidad, cp)
            VALUES %s
            ON CONFLICT DO NOTHING;
            """,
            [(n, f"Av. {n}", 1, None, None, n, "0000") for n in vals]
        )
    conn.commit()
    # devolver mapa nombre->id_suc
    return fetch_map(conn, "SELECT nombre, id_suc FROM app.sucursal;")

def ensure_users(conn, dni_list: List[str], subtipo: str, suc_map: Dict[str,int], sample_suc: Optional[str]) -> None:
    """
    Crea usuarios y subtipo (empleado/administrador). Asigna id_suc de muestra (si disponible).
    subtipo: 'empleado' | 'administrador'
    """
    dnivals = sorted(set([d for d in dni_list if d]))
    if not dnivals: return
    id_suc = suc_map.get(sample_suc) if sample_suc else None
    with conn.cursor() as cur:
        # usuarios
        execute_values(
            cur,
            """
            INSERT INTO app.usuario(dni, nombre, id_suc, activo)
            VALUES %s
            ON CONFLICT (dni) DO NOTHING;
            """,
            [(d, f"{subtipo.title()} {d}", id_suc, True) for d in dnivals]
        )
        # subtipo
        if subtipo == "empleado":
            execute_values(cur,
                "INSERT INTO app.empleado(dni) VALUES %s ON CONFLICT (dni) DO NOTHING;",
                [(d,) for d in dnivals]
            )
        elif subtipo == "administrador":
            execute_values(cur,
                "INSERT INTO app.administrador(dni) VALUES %s ON CONFLICT (dni) DO NOTHING;",
                [(d,) for d in dnivals]
            )
    conn.commit()

def ensure_dimensiones(conn, cats: List[str], fams: List[str], productos: List[Tuple[str,str,str]]) -> None:
    cats = sorted(set([c for c in cats if c]))
    fams = sorted(set([f for f in fams if f]))
    prods = sorted(set([(n,c,f) for (n,c,f) in productos if n and c and f]))
    with conn.cursor() as cur:
        if cats:
            execute_values(cur,
                "INSERT INTO app.categoria(nombre) VALUES %s ON CONFLICT (nombre) DO NOTHING;",
                [(c,) for c in cats]
            )
        if fams:
            execute_values(cur,
                "INSERT INTO app.familia(nombre) VALUES %s ON CONFLICT (nombre) DO NOTHING;",
                [(f,) for f in fams]
            )
        if prods:
            # mapear ids
            cur.execute("SELECT id_categoria, nombre FROM app.categoria;")
            cat_map = {name:id_ for (id_, name) in cur.fetchall()}
            cur.execute("SELECT id_familia, nombre FROM app.familia;")
            fam_map = {name:id_ for (id_, name) in cur.fetchall()}
            to_ins = []
            for (n,c,f) in prods:
                cid = cat_map.get(c)
                fid = fam_map.get(f)
                if cid and fid:
                    to_ins.append((n, cid, fid))
            if to_ins:
                execute_values(cur,
                    """
                    INSERT INTO app.producto(nombre, id_categoria, id_familia)
                    VALUES %s
                    ON CONFLICT ON CONSTRAINT uq_producto DO NOTHING;
                    """,
                    to_ins
                )
    conn.commit()

def get_ids_maps(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT nombre, id_suc FROM app.sucursal;")
        suc_map = {n: i for (n,i) in cur.fetchall()}
        cur.execute("SELECT nombre, id_categoria FROM app.categoria;")
        cat_map = {n: i for (n,i) in cur.fetchall()}
        cur.execute("SELECT nombre, id_familia FROM app.familia;")
        fam_map = {n: i for (n,i) in cur.fetchall()}
        cur.execute("SELECT nombre, id_categoria, id_familia, id_producto FROM app.vw_producto_resolved;")
        # si no existe vista, hacemos consulta directa más abajo
    return suc_map, cat_map, fam_map

def ensure_pedido_and_get_id(conn, id_suc: int, fecha_emision: Optional[str], dni_empleado: Optional[str], dni_admin: Optional[str]) -> int:
    """
    Busca pedido por (id_suc, fecha_emision, dni_empleado, dni_admin).
    Si no existe, inserta y devuelve id_pedido.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id_pedido
            FROM app.pedido
            WHERE id_suc = %s
              AND (fecha_emision = COALESCE(%s, fecha_emision))
              AND (dni_empleado IS NOT DISTINCT FROM %s)
              AND (dni_admin    IS NOT DISTINCT FROM %s)
            LIMIT 1;
        """, (id_suc, fecha_emision, dni_empleado, dni_admin))
        row = cur.fetchone()
        if row:
            return row[0]
        # Insertar
        if fecha_emision is None:
            cur.execute("""
                INSERT INTO app.pedido(id_suc, dni_empleado, dni_admin)
                VALUES (%s, %s, %s)
                RETURNING id_pedido;
            """, (id_suc, dni_empleado, dni_admin))
        else:
            cur.execute("""
                INSERT INTO app.pedido(id_suc, fecha_emision, dni_empleado, dni_admin)
                VALUES (%s, %s, %s, %s)
                RETURNING id_pedido;
            """, (id_suc, fecha_emision, dni_empleado, dni_admin))
        pid = cur.fetchone()[0]
        conn.commit()
        return pid

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Ruta al CSV de pedidos (filas a nivel ítem)")
    args = ap.parse_args()

    rows = read_rows(args.csv)
    if not rows:
        print("No hay filas válidas en el CSV.")
        return

    conn = get_conn()
    try:
        # 1) Sucursales
        sucursales = [r["sucursal"] for r in rows]
        suc_map = ensure_sucursales(conn, sucursales)

        # 2) Usuarios (si hay DNIs)
        emp_dnIs = [r["dni_empleado"] for r in rows if r.get("dni_empleado")]
        adm_dnIs = [r["dni_admin"]    for r in rows if r.get("dni_admin")]
        sample_suc = rows[0]["sucursal"] if rows else None
        ensure_users(conn, emp_dnIs, "empleado", suc_map, sample_suc)
        ensure_users(conn, adm_dnIs, "administrador", suc_map, sample_suc)

        # 3) Dimensiones y productos
        cats = [r["categoria"] for r in rows]
        fams = [r["familia"]   for r in rows]
        prods = [(r["producto"], r["categoria"], r["familia"]) for r in rows]
        ensure_dimensiones(conn, cats, fams, prods)

        # 4) Mapas finales para resolver IDs
        with conn.cursor() as cur:
            cur.execute("SELECT nombre, id_suc FROM app.sucursal;")
            suc_map = {n: i for (n,i) in cur.fetchall()}
            cur.execute("SELECT nombre, id_categoria FROM app.categoria;")
            cat_map = {n: i for (n,i) in cur.fetchall()}
            cur.execute("SELECT nombre, id_familia FROM app.familia;")
            fam_map = {n: i for (n,i) in cur.fetchall()}
            cur.execute("""
                SELECT p.nombre, c.nombre, f.nombre, p.id_producto
                FROM app.producto p
                JOIN app.categoria c ON c.id_categoria = p.id_categoria
                JOIN app.familia   f ON f.id_familia   = p.id_familia;
            """)
            prod_map = {(pn, cn, fn): pid for (pn,cn,fn,pid) in cur.fetchall()}

        # 5) Insertar cabeceras (y recolectar ids) + preparar contiene
        contiene_rows = []
        for r in rows:
            id_suc = suc_map.get(r["sucursal"])
            if not id_suc:
                continue
            pid = ensure_pedido_and_get_id(conn, id_suc, r["fecha_emision"], r["dni_empleado"], r["dni_admin"])
            pid_prod = prod_map.get((r["producto"], r["categoria"], r["familia"]))
            if pid_prod:
                contiene_rows.append((pid_prod, pid, r["cantidad"]))

        # 6) Insert masivo a contiene (ignora duplicados por PK)
        if contiene_rows:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO app.contiene(id_producto, id_pedido, cantidad)
                    VALUES %s
                    ON CONFLICT DO NOTHING;
                    """,
                    contiene_rows,
                    page_size=1000
                )
            conn.commit()

        print(f"Pedidos insertados/ubicados: {len(set([c[1] for c in contiene_rows]))}")
        print(f"Ítems insertados/ignorados por conflicto: {len(contiene_rows)}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
