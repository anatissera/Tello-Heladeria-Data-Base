import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv(dotenv_path=".env")

CSV_FILE = "data/catalog/productos.csv"  # ajustá la ruta al archivo

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
        id_producto = int(row["id_producto"])
        nombre_producto = row["nombre"].strip()
        nombre_familia = row["familia"].strip()
        nombre_categoria = row["categoria"].strip()

        # Buscar id_familia
        cur.execute("SELECT id_familia FROM app.familia WHERE nombre = %s;", (nombre_familia,))
        fam = cur.fetchone()
        if not fam:
            print(f"❌ Familia no encontrada: {nombre_familia} (producto {nombre_producto})")
            continue
        id_familia = fam[0]

        # Buscar id_categoria
        cur.execute("SELECT id_categoria FROM app.categoria WHERE nombre = %s;", (nombre_categoria,))
        cat = cur.fetchone()
        if not cat:
            print(f"❌ Categoría no encontrada: {nombre_categoria} (producto {nombre_producto})")
            continue
        id_categoria = cat[0]

        # Insertar producto con tu propio id_producto
        cur.execute(
            """
            INSERT INTO app.producto (id_producto, nombre, id_categoria, id_familia)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id_producto) DO NOTHING;
            """,
            (id_producto, nombre_producto, id_categoria, id_familia)
        )

    conn.commit()
    cur.close()
    conn.close()
    print("✔ Productos cargados correctamente")

if __name__ == "__main__":
    main()