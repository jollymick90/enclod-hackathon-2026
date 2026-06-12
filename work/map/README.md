# Piattaforma mappa (in-repo)

Piattaforma di visualizzazione GIS della soluzione, basata su **SvelteKit + PostGIS +
Martin (vector tiles) + MapLibre** via Docker Compose. Vendorizzata da `geo-sentinel`
e ripulita dei layer di esempio: qui pubblichiamo solo i dati della soluzione.

## Avvio

```bash
cd work/map
docker compose up -d --build
# apri http://localhost:3030
```

Al **primo avvio** il database esegue in ordine gli script in `infra/postgres/`:

1. `01-init.sql` — schema (`data`, tabella catalogo `public.layers`)
2. `02-accidents.sql` — layer **Incidenti** (738 incidenti reali, colore per gravità)
3. `03-training.sql` — layer **Training** (738 incidenti + 2200 negativi sintetici, colore per esito)

Martin auto-pubblica le tabelle dello schema `data` come vector tiles.

| servizio | porta | ruolo |
|---|---|---|
| web | 3030 | SvelteKit (catalogo + pagine layer, MapLibre) |
| martin | 3010 | vector tiles PostGIS → MVT |
| db | 5433 | PostgreSQL 16 + PostGIS |

Pagine: `/` (catalogo), `/layers/incidenti-vicenza`, `/layers/training-incidenti`.

## Rigenerare i seed dai dati

Gli SQL in `infra/postgres/02-*.sql` e `03-*.sql` sono **generati**:

```bash
python3 ../src/build_accidents_sql.py   # -> infra/postgres/02-accidents.sql
python3 ../src/build_training_sql.py    # -> infra/postgres/03-training.sql
```

Per ricaricare in un DB già avviato (senza ricreare il volume):

```bash
docker compose exec -T db psql -U postgres -d geosentinel < infra/postgres/02-accidents.sql
docker compose restart martin   # Martin scopre le tabelle nuove solo all'avvio
```

Per un reset completo (riesegue tutti i seed): `docker compose down -v && docker compose up -d --build`.

## Aggiungere un layer

1. Crea una tabella `data.<nome>` con una colonna `geom geometry(Point|LineString|Polygon, 4326)`.
2. Inserisci una riga in `public.layers` (vedi i seed come esempio). Il campo `style`
   jsonb accetta `paint` MapLibre + due chiavi meta opzionali: `filters` (lista di
   campi → barra filtri) e `legend` (lista `{label,color}`).
3. `docker compose restart martin`.
