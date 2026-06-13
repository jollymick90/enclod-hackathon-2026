#!/usr/bin/env bash
# Caso B — aggiorna i DATI del database (+ il codice) sulla VM.
# Rigenera il dump dal DB locale, lo ripristina sulla VM, riavvia Martin e
# ribuilda 'web'. Di DEFAULT preserva le segnalazioni dei cittadini presenti
# sulla VM (le esporta prima del restore e le reimporta dopo).
#
# Uso:   ./deploy-update-data.sh utente@IP_VM            # preserva segnalazioni
#        ./deploy-update-data.sh utente@IP_VM --wipe     # riparte pulito (le cancella)
# Opz.:  REMOTE_DIR=saferroads (default), VM=utente@IP_VM
#
# Richiede: lo stack di sviluppo locale ACCESO (per pg_dump).
set -euo pipefail

VM="${1:-${VM:-}}"
WIPE="no"; [ "${2:-}" = "--wipe" ] && WIPE="yes"
REMOTE_DIR="${REMOTE_DIR:-saferroads}"
COMPOSE="docker-compose.deploy.yml"
[ -n "$VM" ] || { echo "Uso: $0 utente@IP_VM [--wipe]"; exit 1; }

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "==> [1/4] Dump del DB locale (stack di sviluppo dev'essere su)…"
( cd work/map && docker compose exec -T db pg_dump -U postgres -Fc geosentinel ) > /tmp/geosentinel.dump

echo "==> [2/4] Archivio del codice…"
COPYFILE_DISABLE=1 tar czf /tmp/saferroads.tgz \
  --exclude='work/map/web/node_modules' --exclude='work/map/web/.svelte-kit' \
  --exclude='work/map/web/build' --exclude='work/map/geosentinel.dump' \
  work/map work/output

echo "==> [3/4] Copio dump + codice su ${VM}…"
scp /tmp/saferroads.tgz /tmp/geosentinel.dump "$VM:~/"

echo "==> [4/4] Ripristino dati e ribuildo sulla VM (wipe=$WIPE)…"
ssh "$VM" "REMOTE_DIR='$REMOTE_DIR' COMPOSE='$COMPOSE' WIPE='$WIPE' bash -s" <<'EOF'
set -euo pipefail
cd "$HOME/$REMOTE_DIR/work/map" 2>/dev/null || { echo "  Manca il deploy iniziale: segui DEPLOY.md"; exit 1; }
DC="docker compose -f $COMPOSE"

if [ "$WIPE" != "yes" ]; then
  echo "  - salvo le segnalazioni dei cittadini…"
  $DC exec -T db pg_dump -U postgres -t data.segnalazioni --data-only geosentinel > "$HOME/segnalazioni.sql" || true
fi

echo "  - aggiorno il codice…"
tar xzf "$HOME/saferroads.tgz" -C "$HOME/$REMOTE_DIR"

echo "  - ripristino il dump (sostituisce il DB)…"
$DC cp "$HOME/geosentinel.dump" db:/tmp/geosentinel.dump
$DC exec -T db pg_restore --clean --if-exists --no-owner -U postgres -d geosentinel /tmp/geosentinel.dump

if [ "$WIPE" != "yes" ] && [ -s "$HOME/segnalazioni.sql" ]; then
  echo "  - reimporto le segnalazioni e riallineo la sequenza id…"
  $DC exec -T db psql -U postgres -d geosentinel < "$HOME/segnalazioni.sql" || true
  $DC exec -T db psql -U postgres -d geosentinel -c \
    "SELECT setval(pg_get_serial_sequence('data.segnalazioni','id'), COALESCE((SELECT max(id) FROM data.segnalazioni), 1));" || true
fi

echo "  - riavvio Martin e ribuildo web…"
$DC restart martin
$DC up -d --build web
echo "  OK: dati + web aggiornati."
EOF

echo "==> Fatto. Ricarica http://<IP_VM>/"
