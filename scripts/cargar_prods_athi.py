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
        id_producto = int(row["ID"])   # en tu CSV la columna es "ID"
        nombre_producto = str(row["nombre"]).strip()

        # Familia (puede ser NULL)
        id_familia = None
        if pd.notna(row["familia"]):
            cur.execute("SELECT id_familia FROM app.familia WHERE nombre = %s;", (row["familia"].strip(),))
            fam = cur.fetchone()
            if fam:
                id_familia = fam[0]
            else:
                print(f"⚠️ Familia no encontrada: {row['familia']} (producto {nombre_producto})")

        # Categoría (puede ser NULL)
        id_categoria = None
        if pd.notna(row["categoria"]):
            cur.execute("SELECT id_categoria FROM app.categoria WHERE nombre = %s;", (row["categoria"].strip(),))
            cat = cur.fetchone()
            if cat:
                id_categoria = cat[0]
            else:
                print(f"⚠️ Categoría no encontrada: {row['categoria']} (producto {nombre_producto})")

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