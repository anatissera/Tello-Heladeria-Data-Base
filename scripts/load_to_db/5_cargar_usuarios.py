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

    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        raise SystemExit(f"Error: El archivo CSV '{CSV_FILE}' no se encontró.")

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
    except psycopg2.Error as e:
        raise SystemExit(f"Error al conectar con la base de datos: {e}")

    contador_exitos = 0
    contador_errores = 0
    
    for index, row in df.iterrows():
        dni = str(row["dni"])
        nombre = row["nombre"]
        fecha_nac = row["fecha_nacimiento"]
        mail = row["mail"]
        
        try:
            id_suc = int(row["id_suc"])
        except ValueError:
            print(f"ERROR (Línea {index + 2}, DNI {dni}): ID_suc no es un número. Omitiendo fila.")
            print(f"ERROR (Línea {index + 2}, DNI {dni}): ID_suc no es un número. Omitiendo fila.")
            contador_errores += 1
            continue

        activo = bool(row["activo"])
        tipo = row["tipo"]
        es_encargado = bool(row["es_encargado"])

        try:
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
                # la restricción del trigger falla si ID_suc != 7
                cur.execute("""
                    INSERT INTO app.administrador (dni)
                    VALUES (%s); 
                """, (dni,))
            
            conn.commit() 
            
            contador_exitos += 1

        except psycopg2.Error as e:
            # deshace cualquier cambio pendiente de ESTA fila.
            conn.rollback()
            
            error_msg = getattr(e, 'pgerror', str(e)).strip()
            print(f"ERROR (Línea {index + 2}, DNI {dni}, Tipo: {tipo}): {error_msg}")
            contador_errores += 1

    cur.close()
    conn.close()
    
    print("\n--- RESUMEN DE LA CARGA ---")
    print(f"Registros procesados con éxito: {contador_exitos}")
    print(f"Registros con error (Fila omitida y revertida): {contador_errores}")
    print("La base de datos solo contiene los registros exitosos.")

if __name__ == "__main__":
    main()