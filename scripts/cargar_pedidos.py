#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, csv, glob, shutil, subprocess, tempfile, sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

ROOT   = Path(__file__).resolve().parents[1]
CSV_IN = ROOT / "data" / "processed"

# Ruta a psql: se toma de la variable de entorno PSQL, del PATH, o se fija acá.
PSQL   = os.environ.get("PSQL") or shutil.which("psql") or "psql"

# Heurística nombre archivo -> sucursal
FILENAME_TO_SUC = {
    "catam": "Catamarca",
    "sept": "Microcentro",
    "monteagudo": "Barrio Norte",
    "yerba": None,  # localidad 'Yerba Buena'
}

KNOWN = {
  "id_producto","producto_id","id",
  "producto","nombre_producto","item","nombre",
  "categoria","cat",
  "familia","fam",
  "sucursal",
  "cantidad","cant","qty","unidades",
  "fecha_emision","fecha","timestamp",
  "dni_empleado","empleado_dni","dni_emp","dniemp",
  "dni_admin","admin_dni","dni_adm","dniadm",
}

def sh(cmd, env=None, capture=False):
    """Ejecuta psql u otro comando. Si capture=True, devuelve stdout.strip()."""
    if capture:
        r = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"Cmd fallo: {cmd}\nSTDERR:\n{r.stderr}")
        return r.stdout.strip()
    else:
        r = subprocess.run(cmd, env=env)
        if r.returncode != 0:
            raise RuntimeError(f"Cmd fallo: {cmd}")

def psql_c(sql, env):
    """psql -t -A -c 'sql' -> devuelve string (sin bordes, sin headers)"""
    cmd = [PSQL, env["SUPABASE_DB_URL"], "-t", "-A", "-q", "-c", sql]
    return sh(cmd, env=env, capture=True)

def psql_f(sql_file, env):
    cmd = [PSQL, env["SUPABASE_DB_URL"], "-v", "ON_ERROR_STOP=1", "-f", str(sql_file)]
    sh(cmd, env=env, capture=False)

def is_num(s):
    try:
        float(str(s).strip())
        return True
    except:
        return False

def parse_fecha(txt):
    if not txt: return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(txt.strip(), fmt)
        except:
            pass
    return None

def estado_por_num(n):
    if n is None: return "emitido"
    if 1 <= n <= 3: return "entregado"
    if n == 4:      return "preparado"
    return "emitido"

def get_num_from_fname(name):
    m = re.search(r'(\d+)\.csv$', name.lower())
    return int(m.group(1)) if m else None

def infer_sucursal(env, fname, csv_single_suc):
    # 1) CSV tiene una única sucursal
    if csv_single_suc:
        sql = f"""
        SELECT id_suc||'|'||nombre||'|'||COALESCE(localidad,'')
        FROM app.sucursal
        WHERE lower(nombre)=lower('{csv_single_suc.replace("'", "''")}')
           OR lower(localidad)=lower('{csv_single_suc.replace("'", "''")}')
        ORDER BY id_suc LIMIT 1;
        """
        out = psql_c(sql, env)
        if out:
            parts = out.split("|")
            return {"id_suc": int(parts[0]), "nombre": parts[1], "localidad": parts[2]}

    # 2) por nombre archivo
    for key, target in FILENAME_TO_SUC.items():
        if key in fname.lower():
            if target:
                sql = f"SELECT id_suc||'|'||nombre||'|'||COALESCE(localidad,'') FROM app.sucursal WHERE lower(nombre)=lower('{target}') LIMIT 1;"
                out = psql_c(sql, env)
                if out:
                    p = out.split("|")
                    return {"id_suc": int(p[0]), "nombre": p[1], "localidad": p[2]}
            else:
                sql = "SELECT id_suc||'|'||nombre||'|'||COALESCE(localidad,'') FROM app.sucursal WHERE lower(localidad)='yerba buena' ORDER BY id_suc LIMIT 1;"
                out = psql_c(sql, env)
                if out:
                    p = out.split("|")
                    return {"id_suc": int(p[0]), "nombre": p[1], "localidad": p[2]}

    # 3) con encargado y admin activos
    sql = """
    SELECT s.id_suc||'|'||s.nombre||'|'||COALESCE(s.localidad,'')
    FROM app.sucursal s
    WHERE EXISTS (
        SELECT 1 FROM app.usuario u JOIN app.empleado e USING (dni)
        WHERE u.id_suc=s.id_suc AND u.activo AND e.es_encargado
    )
    AND EXISTS (
        SELECT 1 FROM app.usuario u JOIN app.administrador a USING (dni)
        WHERE u.id_suc=s.id_suc AND u.activo
    )
    ORDER BY s.id_suc LIMIT 1;
    """
    out = psql_c(sql, env)
    if out:
        p = out.split("|")
        return {"id_suc": int(p[0]), "nombre": p[1], "localidad": p[2]}

    # 4) cualquiera
    out = psql_c("SELECT id_suc||'|'||nombre||'|'||COALESCE(localidad,'') FROM app.sucursal ORDER BY id_suc LIMIT 1;", env)
    if out:
        p = out.split("|")
        return {"id_suc": int(p[0]), "nombre": p[1], "localidad": p[2]}

    return None

def pick_emp_admin(env, id_suc):
    # encargado activo
    sql = f"""
    SELECT u.dni FROM app.usuario u JOIN app.empleado e ON e.dni=u.dni
    WHERE u.id_suc={id_suc} AND u.activo AND e.es_encargado LIMIT 1;
    """
    dni_emp = psql_c(sql, env) or None
    if not dni_emp:
        sql = f"""
        SELECT u.dni FROM app.usuario u JOIN app.empleado e ON e.dni=u.dni
        WHERE u.id_suc={id_suc} AND u.activo LIMIT 1;
        """
        dni_emp = psql_c(sql, env) or None
    if not dni_emp:
        dni_emp = psql_c("SELECT u.dni FROM app.usuario u JOIN app.empleado e ON e.dni=u.dni WHERE u.activo LIMIT 1;", env) or None

    # admin activo
    sql = f"""
    SELECT u.dni FROM app.usuario u JOIN app.administrador a ON a.dni=u.dni
    WHERE u.id_suc={id_suc} AND u.activo LIMIT 1;
    """
    dni_adm = psql_c(sql, env) or None
    if not dni_adm:
        dni_adm = psql_c("SELECT u.dni FROM app.usuario u JOIN app.administrador a ON a.dni=u.dni WHERE u.activo LIMIT 1;", env) or None

    return (dni_emp.strip() if dni_emp else None, dni_adm.strip() if dni_adm else None)

def ensure_proveedor(env):
    dni = psql_c("SELECT dni FROM app.proveedor LIMIT 1;", env)
    if dni: return dni.strip()
    # crear uno rápido
    sql = """
    WITH any_suc AS (SELECT id_suc FROM app.sucursal LIMIT 1)
    INSERT INTO app.usuario(dni,nombre,id_suc,activo)
    SELECT '30-00000000-0','Proveedor Default', id_suc, true FROM any_suc
    ON CONFLICT (dni) DO NOTHING;
    INSERT INTO app.proveedor(dni) VALUES ('30-00000000-0') ON CONFLICT (dni) DO NOTHING;
    """
    psql_c(sql, env)
    return "30-00000000-0"

def normalize_csv(in_path: Path) -> tuple[Path, str|None, datetime|None]:
    """
    Devuelve: (ruta_csv_normalizado, sucursal_unica_si_apl, primera_fecha_valida)
    """
    with in_path.open("r", encoding="utf-8", newline="") as fi:
        r = csv.DictReader(fi)
        headers = [h for h in (r.fieldnames or [])]
        lower = [h.lower().strip() for h in headers]

        # map rápido
        alias = {}
        mapping = {
            "id": {"id","id_producto","producto_id"},
            "producto": {"producto","nombre_producto","item","nombre"},
            "categoria": {"categoria","cat"},
            "familia": {"familia","fam"},
            "sucursal": {"sucursal"},
            "cantidad": {"cantidad","cant","qty","unidades"},
            "fecha": {"fecha_emision","fecha","timestamp"},
            "dni_empleado": {"dni_empleado","empleado_dni","dni_emp","dniemp"},
            "dni_admin": {"dni_admin","admin_dni","dni_adm","dniadm"},
        }
        for i,h in enumerate(lower):
            for k,als in mapping.items():
                if h in als and k not in alias:
                    alias[k] = headers[i]

        # Detectar sucursal única en CSV (si existiese columna)
        suc_vals = set()
        first_valid_fecha = None

        # tmp = tempfile.NamedTemporaryFile(prefix="norm_", suffix=".csv", delete=False)
        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="",
            prefix="norm_", suffix=".csv", delete=False
        )
        tmp_path = Path(tmp.name)
        with tmp:
            w = csv.DictWriter(tmp, fieldnames=["producto","categoria","familia","cantidad","fecha_emision","dni_empleado","dni_admin"])
            w.writeheader()
            fi.seek(0); r = csv.DictReader(fi)
            for row in r:
                # sucursal única?
                if "sucursal" in alias:
                    sval = (row.get(alias["sucursal"]) or "").strip()
                    if sval: suc_vals.add(sval)

                # cantidad
                if "cantidad" in alias:
                    v = (row.get(alias["cantidad"]) or "").strip()
                    qty = int(float(v)) if (v and is_num(v)) else 0
                else:
                    # sumar numéricas desconocidas
                    qty = 0
                    for col, val in row.items():
                        if col and col.lower().strip() not in KNOWN and is_num(val):
                            qty += int(float(val))

                if qty <= 0:
                    continue

                # fecha
                ftxt = (row.get(alias["fecha"]) or "").strip() if "fecha" in alias else ""
                dt = parse_fecha(ftxt)
                if dt and not first_valid_fecha:
                    first_valid_fecha = dt

                w.writerow({
                    "producto": (row.get(alias.get("producto",""), "") or "").strip(),
                    "categoria": (row.get(alias.get("categoria",""), "") or "").strip(),
                    "familia": (row.get(alias.get("familia",""), "") or "").strip(),
                    "cantidad": qty,
                    "fecha_emision": dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "",
                    "dni_empleado": (row.get(alias.get("dni_empleado",""), "") or "").strip(),
                    "dni_admin": (row.get(alias.get("dni_admin",""), "") or "").strip(),
                })

        suc_unique = list(suc_vals)[0] if len(suc_vals)==1 else None
        return tmp_path, suc_unique, first_valid_fecha

def main():
    load_dotenv(override=True)
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("❌ Falta SUPABASE_DB_URL en .env")
        sys.exit(1)
    env = os.environ.copy()
    env["PGCONNECT_TIMEOUT"] = "10"
    env["PGOPTIONS"] = ""  # limpio por si acaso
    env["SUPABASE_DB_URL"] = db_url  # psql admite la URL directa

    files = sorted(glob.glob(str(CSV_IN / "*.csv")))
    if not files:
        print(f"⚠️ No encontré CSV en {CSV_IN}")
        return

    proveedor = ensure_proveedor(env)

    total_ped, total_items, total_ent = 0, 0, 0

    for p in files:
        in_path = Path(p)
        fname = in_path.name
        n = get_num_from_fname(fname)
        estado = estado_por_num(n)

        # 1) Normalizar CSV
        norm_path, suc_csv, first_fecha = normalize_csv(in_path)

        # 2) Resolver sucursal
        suc = infer_sucursal(env, fname, suc_csv)
        if not suc:
            print(f"⚠️ {fname}: no pude resolver sucursal. Salto.")
            continue

        # 3) Empleado/Administrador
        dni_emp, dni_adm = pick_emp_admin(env, suc["id_suc"])
        if not dni_emp or not dni_adm:
            print(f"⚠️ {fname}: no hay empleado/admin elegible. Salto.")
            continue

        # 4) Crear pedido y obtener id
        fecha_sql = first_fecha.strftime("%Y-%m-%d %H:%M:%S") if first_fecha else None
        sql_ins = f"""
        WITH ins AS (
          INSERT INTO app.pedido (id_suc, estado, fecha_emision, dni_empleado, dni_admin)
          VALUES (
            {suc['id_suc']},
            '{estado}',
            {f"'{fecha_sql}'::timestamp" if fecha_sql else "NOW()"},
            '{dni_emp}',
            '{dni_adm}'
          )
          RETURNING id_pedido
        )
        SELECT id_pedido::text FROM ins;
        """
        id_pedido = psql_c(sql_ins, env).strip()
        if not id_pedido:
            print(f"⚠️ {fname}: no pude crear pedido. Salto.")
            continue
        total_ped += 1

        # 5) Cargar items: \copy -> staging tmp -> insert contiene
        tmp_table = f"staging._tmp_items_{id_pedido}"
        sql_batch = f"""
        CREATE SCHEMA IF NOT EXISTS staging;
        DROP TABLE IF EXISTS {tmp_table};
        CREATE TABLE {tmp_table}(
          producto TEXT, categoria TEXT, familia TEXT,
          cantidad INTEGER, fecha_emision TIMESTAMP,
          dni_empleado TEXT, dni_admin TEXT
        );
        """
        # ejecutar batch de creación
        with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as fsql:
            fsql.write(sql_batch)
            tmp_sql_path = fsql.name
        psql_f(tmp_sql_path, env)
        os.unlink(tmp_sql_path)

        # # \copy del CSV normalizado
        # cmd_copy = [
        #     PSQL, env["SUPABASE_DB_URL"], "-v", "ON_ERROR_STOP=1",
        #     "-c", f"\\copy {tmp_table} FROM '{str(norm_path).replace('\\','/')}' CSV HEADER"
        # ]
        # sh(cmd_copy, env)
        # \copy del CSV normalizado
        csv_path = str(norm_path).replace("\\", "/")
        cmd_copy = [
            PSQL, env["SUPABASE_DB_URL"], "-v", "ON_ERROR_STOP=1",
            "-c", f"\\copy {tmp_table} FROM '{csv_path}' CSV HEADER"
        ]
        sh(cmd_copy, env)


        # Insertar solo las filas con cantidad>0 y producto/cat válidos
        sql_cont = f"""
        INSERT INTO app.contiene(id_producto, id_pedido, cantidad)
        SELECT p.id_producto, {id_pedido}::int, t.cantidad
        FROM {tmp_table} t
        JOIN app.categoria c ON c.nombre = TRIM(t.categoria)
        LEFT JOIN app.familia f ON f.nombre = TRIM(t.familia)
        JOIN app.producto p ON lower(p.nombre)=lower(TRIM(t.producto))
                           AND p.id_categoria=c.id_categoria
                           AND (f.id_familia IS NULL OR p.id_familia=f.id_familia)
        WHERE COALESCE(t.cantidad,0) > 0;
        SELECT COUNT(*)::text FROM {tmp_table};
        """
        inserted = psql_c(sql_cont, env).strip()
        try:
            total_items += int(inserted or "0")
        except:
            pass

        # cleanup staging
        psql_c(f"DROP TABLE IF EXISTS {tmp_table};", env)
        try: os.unlink(norm_path)
        except: pass

        # 6) Si estado entregado, crear app.entrega
        if estado == "entregado":
            sql_ent = f"""
            INSERT INTO app.entrega(id_pedido, dni_proveedor, dni_empleado)
            VALUES ({id_pedido}, '{proveedor}', '{dni_emp}')
            ON CONFLICT DO NOTHING;
            """
            psql_c(sql_ent, env)
            total_ent += 1

        print(f"✔ {fname}: pedido {id_pedido}  estado={estado}  suc='{suc['nombre']}'")

    print(f"\nResumen → pedidos: {total_ped}  ítems aprox: {total_items}  entregas: {total_ent}")

if __name__ == "__main__":
    main()
