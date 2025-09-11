import pandas as pd
import unicodedata
import re

MAESTRO = "data/catalog/productos.csv"                
OUTCSV  = "data/processed/pedidos_suc_sept2.csv" 

print(OUTCSV)

def norm_txt(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s)
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return s.lower()
m = pd.read_csv(MAESTRO, dtype=str).fillna("")
c = pd.read_csv(OUTCSV, dtype=str).fillna("")
missing_by_id = m[~m["ID"].isin(c.get("producto_id", pd.Series(dtype=str)))][["ID","nombre","familia"," categoria"]]
print("FALTAN (por ID):", len(missing_by_id))
print(missing_by_id.to_string(index=False))
m["nombre_norm"] = m["nombre"].map(norm_txt)
c["producto_norm"] = c["producto"].map(norm_txt)
missing_by_name = m[~m["nombre_norm"].isin(c["producto_norm"])][["ID","nombre","familia"," categoria"]]
print("\nFALTAN (por nombre normalizado):", len(missing_by_name))
print(missing_by_name.to_string(index=False))

