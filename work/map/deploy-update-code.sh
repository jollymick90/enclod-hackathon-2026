#!/usr/bin/env bash
# Caso A — aggiorna SOLO il codice della web app sulla VM (il DB resta intatto:
# le segnalazioni dei cittadini fatte sulla VM si conservano).
#
# Uso:   ./deploy-update-code.sh utente@IP_VM
#  o:    VM=utente@IP_VM ./deploy-update-code.sh
# Opz.:  REMOTE_DIR=saferroads (cartella sulla VM, default 'saferroads')
set -euo pipefail

VM="${1:-${VM:-}}"
REMOTE_DIR="${REMOTE_DIR:-saferroads}"
COMPOSE="docker-compose.deploy.yml"
[ -n "$VM" ] || { echo "Uso: $0 utente@IP_VM   (oppure VM=utente@IP_VM $0)"; exit 1; }

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "==> [1/3] Creo l'archivio del codice…"
COPYFILE_DISABLE=1 tar czf /tmp/saferroads.tgz \
  --exclude='work/map/web/node_modules' \
  --exclude='work/map/web/.svelte-kit' \
  --exclude='work/map/web/build' \
  --exclude='work/map/geosentinel.dump' \
  work/map work/output

echo "==> [2/3] Copio su ${VM}…"
scp /tmp/saferroads.tgz "$VM:~/saferroads.tgz"

echo "==> [3/3] Estraggo e ribuildo 'web' sulla VM…"
ssh "$VM" "REMOTE_DIR='$REMOTE_DIR' COMPOSE='$COMPOSE' bash -s" <<'EOF'
set -euo pipefail
mkdir -p "$HOME/$REMOTE_DIR"
tar xzf "$HOME/saferroads.tgz" -C "$HOME/$REMOTE_DIR"
cd "$HOME/$REMOTE_DIR/work/map"
docker compose -f "$COMPOSE" up -d --build web
echo "  OK: 'web' aggiornato."
EOF

echo "==> Fatto. Ricarica http://<IP_VM>/"
