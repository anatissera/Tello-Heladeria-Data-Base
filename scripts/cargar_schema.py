import os
import psycopg2
from dotenv import load_dotenv

SQL_FILE = "sql/schema.sql"
load_dotenv()
db_url = os.getenv("SUPABASE_DB_URL")

with open(SQL_FILE, "r", encoding="utf-8") as f:
    schema_sql = f.read()

conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute(schema_sql)
conn.commit()

cur.close()
conn.close()
print("Esquema creado en Supabase")