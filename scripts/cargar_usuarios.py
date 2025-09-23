import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

CSV_FILE = "data/fake/usuarios.csv"

def main():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("No se encontró SUPABASE_DB_URL en el .env")

    df = pd.read_csv(CSV_FILE)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    for _, row in df.iterrows():
        dni = str(row["dni"])
        nombre = row["nombre"]
        fecha_nac = row["fecha_nacimiento"]
        mail = row["mail"]
        id_suc = int(row["id_suc"])
        activo = bool(row["activo"])
        tipo = row["tipo"]
        es_encargado = bool(row["es_encargado"])

        cur.execute("""
            INSERT INTO app.usuario (dni, nombre, fecha_nacimiento, mail, id_suc, activo)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (dni) DO NOTHING;
        """, (dni, nombre, fecha_nac, mail, id_suc, activo))

        if tipo == "empleado":
            cur.execute("""
                INSERT INTO app.empleado (dni, es_encargado)
                VALUES (%s, %s)
                ON CONFLICT (dni) DO NOTHING;
            """, (dni, es_encargado))
        elif tipo == "proveedor":
            cur.execute("""
                INSERT INTO app.proveedor (dni)
                VALUES (%s)
                ON CONFLICT (dni) DO NOTHING;
            """, (dni,))
        elif tipo == "administrador":
            cur.execute("""
                INSERT INTO app.administrador (dni)
                VALUES (%s)
                ON CONFLICT (dni) DO NOTHING;
            """, (dni,))

    conn.commit()
    cur.close()
    conn.close()
    print("Usuarios cargados correctamente en la base")

if __name__ == "__main__":
    main()