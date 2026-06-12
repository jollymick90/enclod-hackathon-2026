-- 01-init.sql — schema base della piattaforma mappa (eseguito al primo boot del DB).
-- Adattato da geo-sentinel, senza i layer di esempio (regioni/DEM): qui pubblichiamo
-- solo i dati della soluzione (incidenti reali + dataset di training).

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS data;

CREATE TYPE layer_kind     AS ENUM ('vector', 'raster');
CREATE TYPE geom_type_enum AS ENUM ('point', 'line', 'polygon');

CREATE TABLE public.layers (
  id              bigserial PRIMARY KEY,
  slug            text NOT NULL UNIQUE,
  title           text NOT NULL,
  description     text,

  kind            layer_kind NOT NULL,
  geom_type       geom_type_enum,                  -- vector only

  source_table    text,                            -- vector: table name in `data`
  cog_path        text,                            -- raster: filename in titiler mount

  bbox            geometry(Polygon, 4326),
  default_center  geometry(Point,   4326) NOT NULL,
  default_zoom    int  NOT NULL DEFAULT 6,

  style           jsonb,
  tags            text[] NOT NULL DEFAULT '{}',
  source_url      text,
  published_at    timestamptz NOT NULL DEFAULT now(),

  project_id      bigint,

  CONSTRAINT layer_kind_consistent CHECK (
    (kind = 'vector' AND source_table IS NOT NULL AND cog_path IS NULL AND geom_type IS NOT NULL) OR
    (kind = 'raster' AND cog_path     IS NOT NULL AND source_table IS NULL AND geom_type IS NULL)
  )
);

CREATE INDEX layers_kind_idx         ON public.layers (kind);
CREATE INDEX layers_published_at_idx ON public.layers (published_at DESC);
CREATE INDEX layers_bbox_gist        ON public.layers USING GIST (bbox);
CREATE INDEX layers_tags_gin         ON public.layers USING GIN  (tags);
