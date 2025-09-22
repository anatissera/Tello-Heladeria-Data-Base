import os
import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv(dotenv_path=".env")  # ajustar ruta si está en otra carpeta

def test_connection():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("❌ No se encontró SUPABASE_DB_URL en el .env")

    try:
        # Conectar a Supabase
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # Ejecutar consulta de prueba
        cur.execute("SELECT 1;")
        result = cur.fetchone()

        print("✔ Conexión exitosa a la base de datos. Resultado:", result)

        # Cerrar
        cur.close()
        conn.close()

    except Exception as e:
        print("❌ Error al conectar a la base de datos:", e)

test_connection()