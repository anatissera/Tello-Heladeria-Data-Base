import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Nombre del CSV que querés cargar
CSV_PATH = "pedidos_suc_catam2.csv"

def main():
    # Cargar la URL de conexión desde .env
    load_dotenv()
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("❌ Falta SUPABASE_DB_URL en el archivo .env")

    # Leer el CSV
    df = pd.read_csv(CSV_PATH)

    # Normalizar columnas (aseguramos que tengan los mismos nombres que la tabla)
    df = df.rename(columns={
        "fecha": "fecha_emision",
        "id_sucursal": "id_suc"
    })

    # Crear un CSV temporal bien formateado
    tmp_csv = "_tmp_pedidos.csv"
    df.to_csv(tmp_csv, index=False, date_format="%Y-%m-%d %H:%M:%S")

    # Conectar a la base
    conn = psycopg2.connect(db_url)
    try:
        with conn, conn.cursor() as cur, open(tmp_csv, "r", encoding="utf-8") as f:
            cur.execute("SET search_path TO app, public;")
            cur.copy_expert("""
                COPY app.pedido (estado, fecha_emision, id_suc, dni_empleado, dni_admin)
                FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER ',');
            """, f)
        conn.commit()
        print("✔ Carga finalizada con COPY.")
    finally:
        conn.close()
        os.remove(tmp_csv)

if __name__ == "__main__":
    main()