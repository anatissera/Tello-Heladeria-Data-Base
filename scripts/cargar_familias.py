import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv(dotenv_path=".env")  # ajustá la ruta a tu .env

CSV_FILE = "data/catalog/familias.csv"  # ruta al archivo CSV

def main():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("❌ No se encontró SUPABASE_DB_URL en el .env")

    # Leer CSV
    df = pd.read_csv(CSV_FILE)

    # Conectar a Supabase
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    for _, row in df.iterrows():
        cur.execute(
            """
            INSERT INTO app.familia (nombre)
            VALUES (%s)
            ON CONFLICT (nombre) DO NOTHING;
            """,
            (row["nombre"].strip(),)
        )

    conn.commit()
    cur.close()
    conn.close()
    print("✔ Familias cargadas correctamente")

if __name__ == "__main__":
    main()