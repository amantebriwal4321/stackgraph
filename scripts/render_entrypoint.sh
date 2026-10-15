#!/bin/sh
# Start FalkorDB, then the API. Render sets PORT. The API loads the seed on startup.
set -eu

DATA_DIR="${FALKORDB_DATA_PATH:-/var/lib/falkordb/data}"
BIN_DIR="${FALKORDB_BIN_PATH:-/var/lib/falkordb/bin}"
LISTEN_PORT="${PORT:-8091}"

mkdir -p "$DATA_DIR"

redis-server \
  --bind 127.0.0.1 \
  --protected-mode no \
  --appendonly yes \
  --dir "$DATA_DIR" \
  --loadmodule "$BIN_DIR/falkordb.so" \
  ${FALKORDB_ARGS:-} \
  &
REDIS_PID=$!

cleanup() {
  if [ -n "${REDIS_PID:-}" ]; then
    kill "$REDIS_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

ready=0
i=0
while [ "$i" -lt 60 ]; do
  if redis-cli -h 127.0.0.1 ping 2>/dev/null | grep -q PONG; then
    ready=1
    break
  fi
  i=$((i + 1))
  sleep 1
done

if [ "$ready" -ne 1 ]; then
  echo "FalkorDB did not answer on localhost" >&2
  exit 1
fi

export FALKORDB_HOST=127.0.0.1
export FALKORDB_PORT=6379
cd /app
echo "FalkorDB is up. Starting API on port ${LISTEN_PORT}"
exec uvicorn app.main:app --host 0.0.0.0 --port "$LISTEN_PORT"
