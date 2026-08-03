CREATE EXTENSION IF NOT EXISTS vector;

-- One row per Lightroom master image. Embedding columns are populated in
-- Phase 2+; Phase 1 only fills metadata.
CREATE TABLE images (
    id              SERIAL PRIMARY KEY,
    lrcat_id        INTEGER NOT NULL UNIQUE,   -- Adobe_images.id_local
    file_path       TEXT NOT NULL,             -- absolute path reconstructed from catalog
    base_name       TEXT NOT NULL,
    extension       TEXT NOT NULL,

    capture_time    TIMESTAMP,                 -- camera-local clock time, no tz (see note below)
    file_width      INTEGER,
    file_height     INTEGER,
    orientation     TEXT,                      -- raw Lightroom orientation code (e.g. 'AB'), undecoded

    camera_model    TEXT,
    lens            TEXT,
    focal_length_mm REAL,
    aperture_fnum   REAL,                      -- decoded from APEX Av
    shutter_speed_s REAL,                      -- decoded from APEX Tv, seconds
    iso             INTEGER,

    gps_lat         DOUBLE PRECISION,
    gps_lon         DOUBLE PRECISION,
    has_gps         BOOLEAN NOT NULL DEFAULT FALSE,

    rating          SMALLINT,                  -- 1-5, null if unrated
    pick            SMALLINT,                  -- Lightroom flag: 1 = picked, -1 = rejected, 0 = unflagged
    color_label     TEXT,
    caption         TEXT,                      -- IPTC caption, sparse but high quality where present

    image_embedding   vector(1152),            -- Phase 2: SigLIP 2 / OpenCLIP (unpopulated until SSD is available)
    caption_embedding vector(1536),             -- OpenAI text-embedding-3-small
    embedded_text     TEXT,                     -- text actually embedded (caption, or keyword/EXIF fallback)
    search_vector     tsvector,                 -- caption + keyword names, refreshed on ingest

    thumbnail_path  TEXT,                       -- Phase 1 stretch / Phase 2

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE keywords (
    id       SERIAL PRIMARY KEY,
    lrcat_id INTEGER NOT NULL UNIQUE,          -- AgLibraryKeyword.id_local
    name     TEXT NOT NULL
);

CREATE TABLE image_keywords (
    image_id   INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    keyword_id INTEGER NOT NULL REFERENCES keywords(id) ON DELETE CASCADE,
    PRIMARY KEY (image_id, keyword_id)
);

CREATE TABLE collections (
    id       SERIAL PRIMARY KEY,
    lrcat_id INTEGER NOT NULL UNIQUE,          -- AgLibraryCollection.id_local
    name     TEXT NOT NULL
);

CREATE TABLE image_collections (
    image_id      INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    pick          SMALLINT,                    -- pick flag within this collection
    PRIMARY KEY (image_id, collection_id)
);

CREATE INDEX images_search_vector_idx ON images USING gin (search_vector);
CREATE INDEX images_capture_time_idx ON images (capture_time);
CREATE INDEX images_rating_idx ON images (rating);
CREATE INDEX images_has_gps_idx ON images (has_gps) WHERE has_gps;

-- HNSW indexes on image_embedding / caption_embedding are created in Phase 2,
-- once vectors are populated (index-then-empty is wasted work).
