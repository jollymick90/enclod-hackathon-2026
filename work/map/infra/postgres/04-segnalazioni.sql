-- Segnalazioni dei cittadini (sezione /cittadino della dashboard).
-- Scritta dall'API POST /api/segnalazioni; pubblicata da Martin come gli altri layer.

CREATE TABLE IF NOT EXISTS data.segnalazioni (
  id          bigserial PRIMARY KEY,
  tipo        text NOT NULL CHECK (tipo IN ('incidente_lieve', 'strada_danneggiata', 'pericolo')),
  descrizione text NOT NULL DEFAULT '',
  geom        geometry(Point, 4326) NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS segnalazioni_geom_gist ON data.segnalazioni USING gist (geom);

INSERT INTO public.layers
  (slug, title, description, kind, geom_type, source_table, default_center, default_zoom, style, tags)
VALUES (
  'segnalazioni',
  'Segnalazioni dei cittadini',
  'Segnalazioni inviate dalla dashboard cittadino: incidenti lievi, strade danneggiate, situazioni di pericolo.',
  'vector', 'point', 'segnalazioni',
  ST_SetSRID(ST_MakePoint(11.35, 45.65), 4326), 10,
  '{"paint": {"circle-color": "#9c36b5", "circle-radius": 6, "circle-stroke-width": 2, "circle-stroke-color": "#ffffff"}}'::jsonb,
  ARRAY['soluzione', 'cittadino']
)
ON CONFLICT (slug) DO NOTHING;
