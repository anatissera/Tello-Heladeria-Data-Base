import re
import csv
import unicodedata
from pathlib import Path
from typing import Optional, Dict, Set, Tuple
import pandas as pd
from difflib import get_close_matches
from datetime import datetime
import traceback
import sys
import argparse

MAESTRO = Path("data/catalog/productos.csv")
RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/processed")

FUZZY_CUTOFF = 0.88

CATS_3 = {"helado", "minitortas", "paletas", "tortas heladas", "tortas", "tartas"}
CATS_2 = {"diet", "salsas", "cuadrados", "chocolates", "postre envasado", "agregados", "bolsas", "insumos", "utiles","para postre"}

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
    "del. de d. de l": "del dulce d leche",
    "ddl": "dulce de leche",
    "salsa ddl": "salsa dulce de leche",
    "salsa d de leche": "salsa dulce de leche",
    "felpon": "felpón",
    "sirope p/ affogato": "sirope para affogato",
    "baño de chocolate": "baño de choco",
    "vasos plastico milkshake": "vaso plast.milk shake"

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

def detect_section_label(cell: str) -> Optional[str]:
    t = norm_txt(cell)
    if not t:
        return None
    if ("tacita" in t and "diet" in t) or t == "diet":
        return "diet"
    if t.startswith("tartas"):
        return "tartas"
    if t.startswith("tortas heladas"):
        return "tortas_heladas"
    if t.startswith("tortas"):
        return "tortas"
    if t.startswith("cajas"):
        return "cajas"
    if t.startswith("salsas"):
        return "salsas"
    if t.startswith("cuadrados"):
        return "cuadrados"
    if t.startswith("postre envasado"):
        return "postre_envasado"

    return None

def to_cajas_candidate(raw_name: str, universe: Set[str]) -> Optional[str]:
    base = norm_txt(raw_name)
    mapping = {
        "tartas": "cajas p/ tartas",
        "tortas medianas": "cajas p/ tortas medianas",
        "tortas grandes": "cajas p/ tortas grandes",
    }
    cand = mapping.get(base)
    return cand if cand in universe else None

def first_existing(cands, universe: Set[str]) -> Optional[str]:
    for c in cands:
        if c in universe:
            return c
    return None


def to_salsas_candidate(raw_name: str, universe: Set[str]) -> Optional[str]:
    base = apply_alias(norm_txt(raw_name))
    if "dulce" in base and "leche" in base:
        return first_existing(
            ["salsa dulce de leche", "salsa de dulce de leche"], universe
        )
    if base in {"chocolate", "choco"}:
        return first_existing(
            ["salsa chocolate", "salsa de chocolate"], universe
        )
    return None

def to_cuadrados_candidate(raw_name: str, universe: Set[str]) -> Optional[str]:
    base = apply_alias(norm_txt(raw_name))
    if base == "brownie":
        return first_existing(
            ["cuadradito brownie", "cuadraditos brownie", "cuadradito de brownie"], universe
        )
    return None

def to_postre_envasado_candidate(raw_name: str, universe: Set[str]) -> Optional[str]:
    base = apply_alias(norm_txt(raw_name))
    if base == "tiramisu":
        return first_existing(
            ["tiramisu postre", "postre tiramisu"], universe
        )
    return None

_DIET_BASE_MAP = {
    "anana": "diet anana",
    "americana": "diet americana",
    "banana": "diet banana",
    "dulce de leche": "diet dulce de leche",
    "durazno": "diet durazno",
    "vainilla": "diet vainilla",
}
def to_diet_candidate(raw_name: str, universe: Set[str]) -> Optional[str]:
    base = apply_alias(norm_txt(raw_name))
    base = re.sub(r"\s+al\s+agua$", "", base)          
    base = {"bananas": "banana"}.get(base, base)
    cand = _DIET_BASE_MAP.get(base, f"diet {base}")
    return cand if cand in universe else None

def to_tarta_candidate(raw_name: str, universe: Set[str]) -> Optional[str]:
    base = apply_alias(norm_txt(raw_name))
    base = re.sub(r"\s+tarta$", "", base)
    cand = f"{base} tarta"
    return cand if cand in universe else None

def parse_pedido_csv(
    df_raw: pd.DataFrame,
    id_by_norm, name_by_norm, fam_by_norm, cat_by_norm, universe_norm: Set[str]
) -> pd.DataFrame:
    out_rows = []
    df = df_raw.astype(str)

    col_ctx: Dict[int, Optional[str]] = {}

    for _, row in df.iterrows():
        cells = row.tolist()
        for j, c in enumerate(cells):
            lab = detect_section_label(c)
            if lab:
                col_ctx[j] = lab

        i, n = 0, len(cells)
        while i < n:
            raw_token = cells[i]
            if not norm_txt(raw_token):
                i += 1
                continue

            ctx = col_ctx.get(i)
            nm_target = None
            if ctx == "diet":
                nm_target = to_diet_candidate(raw_token, universe_norm)
            elif ctx == "tartas":
                nm_target = to_tarta_candidate(raw_token, universe_norm)
            elif ctx == "salsas":
                nm_target = to_salsas_candidate(raw_token, universe_norm)
            elif ctx == "cuadrados":
                nm_target = to_cuadrados_candidate(raw_token, universe_norm)
            elif ctx == "postre_envasado":
                nm_target = to_postre_envasado_candidate(raw_token, universe_norm)
            elif ctx == "cajas":
                nm_target = to_cajas_candidate(raw_token, universe_norm)
    
            if not nm_target:
                nm_target = best_match(raw_token, universe_norm)

            if not nm_target:
                i += 1
                continue

            prod_id = id_by_norm[nm_target]
            prod_nm = name_by_norm[nm_target]
            fam     = fam_by_norm[nm_target]
            cat     = cat_by_norm[nm_target]

            if cat in CATS_2:
                pozo_raw   = ""  
                salon_raw  = cells[i+1] if i+1 < n else ""
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

# detección de fecha
DATE_LINE_SCAN = 30
_date_regex = re.compile(r"\b(\d{1,2}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{2,4})\b")

def _normalize_date_ddmmyyyy(tok: str) -> Optional[str]:
    """Convierte token a formato dd/mm/yyyy si se puede."""
    tok = tok.strip().strip(",;: ")
    formats = [
        "%d/%m/%Y", "%d/%m/%y",
        "%d-%m-%Y", "%d-%m-%y",
        "%d.%m.%Y", "%d.%m.%y"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(tok, fmt)
            return dt.strftime("%d/%m/%Y")
        except Exception:
            continue
    return None

def detect_date_in_file(path: str, lines_to_scan: int = DATE_LINE_SCAN) -> Optional[str]:
    """
    Devuelve una fecha encontrada en el CSV (formato dd/mm/yyyy).
    """
    try:
        with open(path, "rb") as f:
            raw = f.read(20000)
        try:
            txt = raw.decode("utf-8")
        except Exception:
            txt = raw.decode("latin-1", errors="replace")
    except Exception:
        return None

    lines = txt.splitlines()[:lines_to_scan]
    candidates = []

    for i, ln in enumerate(lines):
        has_fecha = bool(re.search(r"\bfecha\b", ln, re.I))
        for m in _date_regex.finditer(ln):
            raw_token = m.group(1).strip()
            norm = _normalize_date_ddmmyyyy(raw_token)
            if norm:
                candidates.append((norm, has_fecha))

    if not candidates:
        return None

    # si hay alguna línea con 'fecha', se prioriza esa
    for norm, has_fecha in candidates:
        if has_fecha:
            return norm

    return candidates[0][0]


def procesar_todos():
    if not MAESTRO.exists():
        raise FileNotFoundError(f"No se encontró {MAESTRO}")
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"No se encontró carpeta raw: {RAW_DIR}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    id_by_norm, name_by_norm, fam_by_norm, cat_by_norm, universe_norm = cargar_maestro(str(MAESTRO))

    raws = sorted([p for p in RAW_DIR.glob("*.csv") if p.is_file()])
    if not raws:
        print(f"No hay archivos RAW en {RAW_DIR}")
        return

    ok_count = 0
    err_count = 0

    for raw_path in raws:
        try:
            stem = raw_path.stem  # yerba4, catam1, etc.
            out_path = OUT_DIR / f"pedidos_suc_{stem}.csv"
            print(f"Procesando {raw_path} -> {out_path} ...", end=" ")

            fecha = detect_date_in_file(str(raw_path))
            raw_df = read_dirty_csv(str(raw_path))
            clean = parse_pedido_csv(raw_df, id_by_norm, name_by_norm, fam_by_norm, cat_by_norm, universe_norm)
            clean["fecha"] = fecha if fecha else ""
            clean.to_csv(str(out_path), index=False, encoding="utf-8")

            print(f"OK ({len(clean)} filas)")
            ok_count += 1
        except Exception as e:
            err_count += 1
            print(f"ERROR: {e}")
            traceback.print_exc()

    print(f"\nResumen: procesados={ok_count}  errores={err_count}")
    
    
def procesar_single(raw_path: Path, out_path: Optional[Path] = None):
    if not MAESTRO.exists():
        raise FileNotFoundError(f"No se encontró {MAESTRO}")
    if not raw_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo raw: {raw_path}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    id_by_norm, name_by_norm, fam_by_norm, cat_by_norm, universe_norm = cargar_maestro(str(MAESTRO))

    stem = raw_path.stem
    default_out = OUT_DIR / f"pedidos_suc_{stem}.csv"
    if out_path is None:
        out_path = default_out
    else:
        out_path = Path(out_path)

    print(f"Procesando single: {raw_path} -> {out_path} ...", end=" ")
    fecha = detect_date_in_file(str(raw_path))
    raw_df = read_dirty_csv(str(raw_path))
    clean = parse_pedido_csv(raw_df, id_by_norm, name_by_norm, fam_by_norm, cat_by_norm, universe_norm)
    clean["fecha"] = fecha if fecha else ""
    clean.to_csv(str(out_path), index=False, encoding="utf-8")
    print(f"OK ({len(clean)} filas)")

def _interactive_mode():
    print("Seleccioná modo:")
    print("  0 -> procesar TODOS los archivos en data/raw/")
    print("  1 -> procesar UN archivo (especificar path)")
    sel = input("Ingrese 0 o 1: ").strip()
    if sel == "0":
        return ("all", None, None)
    if sel == "1":
        raw = input("Path al archivo raw (ej: data/raw/yerba1.csv): ").strip()
        out = input("Path de salida (opcional, dejar vacío para default en data/processed/): ").strip()
        return ("single", raw if raw else None, out if out else None)
    print("Opción inválida.")
    sys.exit(2)

def main(argv=None):
    parser = argparse.ArgumentParser(description="Procesar CSVs RAW a CSVs procesados (pedidos_suc_...)")
    parser.add_argument("--mode", choices=["all","single","0","1"], help="Modo: all|single (o 0|1). Si se omite, se pregunta interactivamente.")
    parser.add_argument("--raw-path", help="(modo single) path al archivo raw a procesar")
    parser.add_argument("--out-path", help="(modo single) path de salida opcional")
    args = parser.parse_args(argv)

    mode = args.mode
    raw_path = args.raw_path
    out_path = args.out_path

    if mode is None:
        mode, raw_path, out_path = _interactive_mode()
    else:
        if mode == "0":
            mode = "all"
        if mode == "1":
            mode = "single"

    if mode == "all":
        procesar_todos()
    elif mode == "single":
        if not raw_path:
            print("Modo 'single' requiere --raw-path o ingresar interactivo.")
            sys.exit(2)
        procesar_single(Path(raw_path), Path(out_path) if out_path else None)
    else:
        print("Modo desconocido.")
        sys.exit(2)

if __name__ == "__main__":
    main()