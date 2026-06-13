# Deploy su VM (solo IP, niente DNS)

Obiettivo: portare SaferRoads Vicenza su una VM, raggiungibile da
`http://IP_VM/`, con una sola porta pubblica (80) e **niente CORS** (un reverse
proxy nginx mette web + tile sotto la stessa origine).

File usati: `docker-compose.deploy.yml`, `infra/nginx/default.conf`.

> Sostituisci ovunque `IP_VM` con l'IP reale della VM e `utente` con il tuo
> utente SSH.

---

## 0. Prerequisiti sulla VM (una volta sola)

- Docker + plugin compose. Su Ubuntu:
  ```bash
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker $USER      # poi ri-logga la sessione SSH
  ```
- **Porta 80 aperta** nel firewall / security group del cloud (inbound TCP 80).

---

## 1. (Locale) Pulisci ed esporta il database

Lo stack di sviluppo deve essere su (`docker compose up -d` in `work/map`).
Il DB locale contiene GIÀ tutto (incidenti, training, OSM, road_segments,
segment_risk, segnalazioni): lo congeliamo in un dump.

```bash
cd work/map

# opzionale: togli le segnalazioni di prova prima del dump
docker compose exec -T db psql -U postgres -d geosentinel \
  -c "DELETE FROM data.segnalazioni;"

# dump completo (formato custom, compresso)
docker compose exec -T db pg_dump -U postgres -Fc geosentinel > geosentinel.dump
```

## 2. (Locale) Crea un archivio del codice (senza node_modules)

```bash
# dalla ROOT del repo
tar czf saferroads.tgz \
  --exclude='work/map/web/node_modules' \
  --exclude='work/map/web/.svelte-kit' \
  --exclude='work/map/web/build' \
  work/map work/output
```

## 3. (Locale) Copia tutto sulla VM con scp

```bash
scp saferroads.tgz work/map/geosentinel.dump utente@IP_VM:~/
```

## 4. (VM) Scompatta

```bash
ssh utente@IP_VM
mkdir -p ~/saferroads && tar xzf ~/saferroads.tgz -C ~/saferroads
cd ~/saferroads/work/map
```
La struttura risultante ha `work/map` e `work/output` affiancati: il mount
`../output` del compose si risolve correttamente.

## 5. (VM) Configura l'URL pubblico

```bash
echo "PUBLIC_BASE_URL=http://IP_VM" > .env
```
(compose legge `.env` in automatico; da qui derivano `PUBLIC_MARTIN_URL` e `ORIGIN`.)

## 6. (VM) Avvia il DB e ripristina il dump

```bash
# 1) solo il database, vuoto
docker compose -f docker-compose.deploy.yml up -d db

# 2) attendi che sia "healthy"
docker compose -f docker-compose.deploy.yml ps

# 3) copia il dump nel container e ripristina
docker compose -f docker-compose.deploy.yml cp ~/geosentinel.dump db:/tmp/geosentinel.dump
docker compose -f docker-compose.deploy.yml exec db \
  pg_restore --clean --if-exists --no-owner -U postgres -d geosentinel /tmp/geosentinel.dump
```

## 7. (VM) Avvia il resto (build inclusa)

```bash
docker compose -f docker-compose.deploy.yml up -d --build
```
Martin parte DOPO il restore, quindi scopre le tabelle dello schema `data`.
La build di `web` richiede internet sulla VM (pnpm install). Se la VM non ha
internet, vedi "Alternativa senza build" in fondo.

## 8. Verifica

```bash
# sulla VM
curl -s -o /dev/null -w "home: %{http_code}\n" http://localhost/
curl -s -o /dev/null -w "tile: %{http_code}\n" http://localhost/tiles/road_segments/12/2200/1500
```
Poi dal tuo PC apri **http://IP_VM/** — home, /analisi, /previsione, /priorita,
/cittadino devono caricare con le mappe colorate.

---

## Aggiornare il codice dopo una modifica

Ricopia il sorgente e ribuilda solo `web` (il DB resta col suo volume):

```bash
# locale
tar czf saferroads.tgz --exclude='work/map/web/node_modules' \
  --exclude='work/map/web/.svelte-kit' --exclude='work/map/web/build' work/map work/output
scp saferroads.tgz utente@IP_VM:~/
# VM
tar xzf ~/saferroads.tgz -C ~/saferroads
cd ~/saferroads/work/map
docker compose -f docker-compose.deploy.yml up -d --build web
```

## Note

- **HTTPS/GPS**: su `http://IP` (senza dominio) il pulsante "usa il GPS" della
  sezione Cittadino non funziona (richiede secure context). Resta il tap sulla
  mappa per posizionare la segnalazione. Tutto il resto funziona in http.
- **Basemap**: le tile di sfondo (OpenStreetMap) le scarica il browser da
  internet; serve quindi connettività sul PC che apre la dashboard.
- **Logs**: `docker compose -f docker-compose.deploy.yml logs -f web` (o `martin`,
  `proxy`).
- **Reset totale del DB** (riparti dal dump): `docker compose -f docker-compose.deploy.yml down -v` e ripeti dal passo 6.

## Alternativa senza build sulla VM (VM senza internet)

Builda l'immagine in locale e trasferiscila:
```bash
# locale
docker compose -f work/map/docker-compose.deploy.yml build web
docker save $(docker compose -f work/map/docker-compose.deploy.yml config --images | grep -v postgis | grep -v martin | grep -v nginx) -o web-image.tar
scp web-image.tar utente@IP_VM:~/
# VM
docker load -i ~/web-image.tar
```
(Le immagini postgis, martin e nginx vanno comunque scaricate: se la VM è
totalmente offline, fai `docker save`/`load` anche per quelle.)
