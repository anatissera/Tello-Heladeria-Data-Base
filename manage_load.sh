#!/usr/bin/env bash
# manage_load.sh
# Uso:
#   ./manage_load.sh 0        # solo schema
#   ./manage_load.sh 1        # solo datos (asume schema ya creado)
#   ./manage_load.sh 2        # schema y luego datos
#   ./manage_load.sh schema
#   ./manage_load.sh data
#   ./manage_load.sh all

set -euo pipefail

# ----- Config -----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}"
ENV_FILE="${REPO_ROOT}/.env"
SCHEMA_SQL="${REPO_ROOT}/sql/schema.sql"

# Modo de carga de pedidos: 'random' simula el flujo completo (emisión,
# aprobación, cancelación y entrega), 'emit_all' deja todo en estado 'emitido'.
PEDIDOS_MODE="${PEDIDOS_MODE:-emit_all}"

DATA_SCRIPTS=(
  "scripts/load_to_db/1_cargar_categorias.py"
  "scripts/load_to_db/2_cargar_familias.py"
  "scripts/load_to_db/3_cargar_productos.py"
  "scripts/load_to_db/4_cargar_sucursales.py"
  "scripts/load_to_db/5_cargar_usuarios.py"
  "scripts/load_to_db/6_cargar_pedidos.py"
)

PYTHON="${PYTHON:-python3}"

# ----- Helpers -----
usage() {
  cat <<EOF
Usage: $0 <mode>
Modes:
  0 | schema    -> solo correr schema (psql -f sql/schema.sql)
  1 | data      -> solo correr scripts de carga (python scripts/load_to_db/...)
  2 | all       -> schema + data (en ese orden)

Variables de entorno:
  PYTHON        -> intérprete a usar (default: python3)
  PEDIDOS_MODE  -> 'emit_all' (default) o 'random'
EOF
  exit 1
}

err() { echo "ERROR: $*" >&2; }

check_cmd() {
  local cmd="$1"; command -v "$cmd" >/dev/null 2>&1 || { err "No se encontró '$cmd' en PATH."; exit 2; }
}

load_env() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    set +a
    echo "Cargado .env"
  else
    echo "No existe .env en repo"
  fi
}

run_schema() {
  if [[ ! -f "$SCHEMA_SQL" ]]; then
    err "No encontré $SCHEMA_SQL"
    exit 3
  fi
  check_cmd psql
  if [[ -z "${SUPABASE_DB_URL:-}" ]]; then
    err "SUPABASE_DB_URL no está definido (en .env o en el entorno)."
    exit 4
  fi
  echo "Ejecutando schema: psql \"\$SUPABASE_DB_URL\" -f $SCHEMA_SQL"
  psql "$SUPABASE_DB_URL" -f "$SCHEMA_SQL"
  echo "Schema cargado correctamente."
}

run_data() {
  check_cmd "$PYTHON"
  if [[ -z "${SUPABASE_DB_URL:-}" ]]; then
    err "SUPABASE_DB_URL no está definido (en .env o en el entorno)."
    exit 4
  fi

  for script in "${DATA_SCRIPTS[@]}"; do
    full="${REPO_ROOT}/${script}"
    if [[ ! -f "$full" ]]; then
      err "No encontré el script de datos: $full"
      exit 5
    fi
  done

  echo "Iniciando carga de datos con '$PYTHON'..."
  for script in "${DATA_SCRIPTS[@]}"; do
    # cargar_pedidos acepta --mode; el resto no lleva argumentos
    args=()
    [[ "$script" == *"6_cargar_pedidos.py" ]] && args=(--mode "$PEDIDOS_MODE")

    echo "-> Ejecutando: $PYTHON ${script} ${args[*]-}"
    # se ejecuta desde REPO_ROOT para que las rutas relativas dentro de los scripts funcionen
    (cd "$REPO_ROOT" && "$PYTHON" "$script" ${args[@]+"${args[@]}"})
    echo "   OK: $script"
  done
  echo "Carga de datos finalizada."
}

# ----- Main -----
if [[ $# -ne 1 ]]; then
  usage
fi

case "$1" in
  0|schema) MODE="schema" ;;
  1|data)   MODE="data" ;;
  2|all)    MODE="all" ;;
  *) usage ;;
esac

echo "Modo: $MODE"
load_env

case "$MODE" in
  schema) run_schema ;;
  data)   run_data ;;
  all)    run_schema; run_data ;;
esac

echo "Hecho."
