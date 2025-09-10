import re
import csv
import unicodedata
from pathlib import Path
from typing import Optional, Dict, Set
import pandas as pd
from difflib import get_close_matches
from torch import cat

MAESTRO = "data/catalog/productos.csv"                 
CSV_PEDIDO = "data/raw/monteagudo1.csv"  
OUTCSV  = "data/processed/pedidos_suc_monteagudo_1.csv"

FUZZY_CUTOFF = 0.88

CATS_3 = {"helado", "minitortas", "paletas", "tortas heladas", "tortas", "tartas"}
CATS_2 = {"diet"}

ALIASES = {
    "crema de higo c/nuez": "crema de higo con nuez",
    "arandanos y casis": "arandano y cassis",
    "pistacchio": "pistacho",
    "yogurt griego": "yogur griego",
    "dulce leche bombon": "dulce de leche bombon",
    "dulce leche graniz.": "dulce de leche granizado",
    "dulce leche tentac.": "dulce de leche tentacion",
    "chocolate c/almendra": "chocolate con almendras",
    "chocolate c/cerezas": "chocolate con cerezas",
    "crema biscuit": "biscuit",
    "tiramissu": "tiramisu",
    "cheescake dl/ oreo": "cheescake",
    "diet anana": "diet anana",
    "diet durazno": "diet durazno",
    "diet americana": "diet americana",
    "diet banana": "diet banana",
    "diet dulce de leche": "diet dulce de leche",
    "diet vainilla": "diet vainilla",
    "flan": "crema flan",
    "cafe": "crema de cafe",
    "durazno": "durazno al agua",
    "cheescake": "cheescake tarta",
    "mousse de maracuya": "maracuya",
    "diamont": "cristal",
    "chocolate con alm.": "chocolate con almendras",
    "classic": "clasica",
    "dulce de leche gra.": "dulce de leche granizado",
    "del. de amer.": "del americana",
    "del. de d. de l": "del dulce d leche"
}

def strip_accents(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def norm_txt(s: str) -> str:
    s = (s or "").replace("�", "ñ").replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = strip_accents(s).lower()
    return s

def apply_alias(norm_name: str) -> str:
    return ALIASES.get(norm_name, norm_name)

def fraction_to_float(x: str) -> Optional[float]:
    if x is None:
        return None
    s = norm_txt(str(x)).replace(",", ".")
    if s in {"", "mandar", "hay"}:
        return None
    m = re.match(r"^(-?\d+)\s+(\d+)/(\d+)$", s)  
    if m:
        a, b, c = m.groups()
        try:
            return float(a) + (float(b) / float(c))
        except ZeroDivisionError:
            return None
    m = re.match(r"^(-?\d+)/(\d+)$", s)       
    if m:
        b, c = m.groups()
        try:
            return float(b) / float(c)
        except ZeroDivisionError:
            return None
    try:
        return float(s)
    except ValueError:
        return None

def sniff_sep(path: str, sample_bytes: int = 4096) -> str:
    with open(path, "rb") as f:
        sample = f.read(sample_bytes)
    for enc in ("utf-8", "latin-1"):
        try:
            txt = sample.decode(enc, errors="strict")
            dialect = csv.Sniffer().sniff(txt, delimiters=";,|\t,")
            return dialect.delimiter
        except Exception:
            continue
    return ";"

def read_dirty_csv(path: str) -> pd.DataFrame:
    sep = sniff_sep(path)
    try:
        df = pd.read_csv(path, header=None, dtype=str, sep=sep, engine="python")
        return df.fillna("")
    except UnicodeDecodeError:
        df = pd.read_csv(path, header=None, dtype=str, sep=sep, engine="python", encoding="latin-1")
        return df.fillna("")

def cargar_maestro(path: str):
    m = pd.read_csv(path, dtype=str)
    m.columns = [c.strip() for c in m.columns]
    for c in ["ID", "nombre", "familia", "categoria"]:
        if c not in m.columns:
            raise ValueError(f"Falta columna '{c}' en {path}")
    for col in ["ID", "nombre", "familia", "categoria"]:
        m[col] = m[col].fillna("").astype(str).str.strip()
    m["nombre_norm"] = m["nombre"].map(norm_txt)
    m["nombre_norm"] = m["nombre_norm"].map(apply_alias)  
    m["categoria_norm"] = m["categoria"].map(norm_txt)
    id_by_norm: Dict[str, str]    = dict(zip(m["nombre_norm"], m["ID"]))
    name_by_norm: Dict[str, str]  = dict(zip(m["nombre_norm"], m["nombre"]))
    fam_by_norm: Dict[str, str]   = dict(zip(m["nombre_norm"], m["familia"]))
    cat_by_norm: Dict[str, str]   = dict(zip(m["nombre_norm"], m["categoria_norm"]))
    universe_norm: Set[str] = set(m["nombre_norm"])
    return id_by_norm, name_by_norm, fam_by_norm, cat_by_norm, universe_norm

def best_match(cell: str, universe: Set[str]) -> Optional[str]:
    s = norm_txt(cell)
    if not s:
        return None
    s = apply_alias(s)
    if s in universe:
        return s
    cand = get_close_matches(s, list(universe), n=1, cutoff=FUZZY_CUTOFF)
    return cand[0] if cand else None

def parse_pedido_csv(
    df_raw: pd.DataFrame,
    id_by_norm, name_by_norm, fam_by_norm, cat_by_norm, universe_norm: Set[str]
) -> pd.DataFrame:
    out_rows = []
    df = df_raw.astype(str)
    for _, row in df.iterrows():
        cells = row.tolist()
        i, n = 0, len(cells)
        while i < n:
            nm = best_match(cells[i], universe_norm)
            if not nm:
                i += 1
                continue
            prod_id = id_by_norm[nm]
            prod_nm = name_by_norm[nm]
            fam     = fam_by_norm[nm]
            cat     = cat_by_norm[nm] 
            if cat in CATS_2:
                pozo_raw   = cells[i+1] if i+1 < n else ""
                salon_raw  = ""  
                mandar_raw = cells[i+2] if i+2 < n else ""
                step = 3
            else:
                pozo_raw   = cells[i+1] if i+1 < n else ""
                salon_raw  = cells[i+2] if i+2 < n else ""
                mandar_raw = cells[i+3] if i+3 < n else ""
                step = 4
            def as_qty(x, force_empty=False):
                if force_empty:
                    return ""  
                val = fraction_to_float(x)
                return 0.0 if val is None else val
            pozo   = as_qty(pozo_raw)
            salon  = as_qty(salon_raw, force_empty=(cat in CATS_2))
            mandar = as_qty(mandar_raw)
            out_rows.append({
                "producto_id": prod_id,
                "producto": prod_nm,
                "familia": fam,
                "categoria": cat,
                "pozo": pozo,
                "salon": salon,     
                "mandar": mandar
            })
            i += step
    if not out_rows:
        return pd.DataFrame(columns=["producto_id","producto","familia","categoria","pozo","salon","mandar"])
    df_out = pd.DataFrame(out_rows)
    for c in ["pozo","mandar"]:
        df_out[c] = pd.to_numeric(df_out[c], errors="coerce").fillna(0.0)
    df_out = (
        df_out
        .assign(salon_num=pd.to_numeric(df_out["salon"], errors="coerce").fillna(0.0))
        .groupby(["producto_id","producto","familia","categoria"], as_index=False)
        .agg({"pozo":"sum","salon_num":"sum","mandar":"sum"})
    )
    df_out["salon"] = df_out.apply(lambda r: "" if r["categoria"] in CATS_2 else r["salon_num"], axis=1)
    df_out = df_out.drop(columns=["salon_num"])
    df_out = df_out[["producto_id","producto","familia","categoria","pozo","salon","mandar"]]
    df_out = df_out.sort_values(["categoria","familia","producto"]).reset_index(drop=True)
    return df_out


if __name__ == "__main__":
    if not Path(MAESTRO).exists():
        raise FileNotFoundError(f"No se encontró {MAESTRO}")
    if not Path(CSV_PEDIDO).exists():
        raise FileNotFoundError(f"No se encontró {CSV_PEDIDO}")
    id_by_norm, name_by_norm, fam_by_norm, cat_by_norm, universe_norm = cargar_maestro(MAESTRO)
    raw = read_dirty_csv(CSV_PEDIDO)
    clean = parse_pedido_csv(raw, id_by_norm, name_by_norm, fam_by_norm, cat_by_norm, universe_norm)
    clean.to_csv(OUTCSV, index=False, encoding="utf-8")
    print(f"OK -> {OUTCSV} ({len(clean)} filas)")