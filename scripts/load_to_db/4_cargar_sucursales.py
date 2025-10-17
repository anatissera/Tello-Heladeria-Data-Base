import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

def main():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("No se encontró SUPABASE_DB_URL en el .env")

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    with open("sql/sucursales.sql", "r") as f:
        sql_script = f.read()

    cur.execute(sql_script)

    conn.commit()
    cur.close()
    conn.close()
    print("Sucursales insertadas correctamente")

if __name__ == "__main__":
    main()