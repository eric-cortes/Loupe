"""Exercises the structured-filter retrieval path against a real Postgres.

Deliberately avoids the semantic_query path so this runs in CI without an
OpenAI key. Requires DATABASE_URL to point at a Postgres with sql/schema.sql
already applied.
"""
from __future__ import annotations

import json
import os

import psycopg
import pytest

from agents.search_tool import search_archive

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://archive:archive@localhost:5433/archive"
)


@pytest.fixture
def seeded_image():
    with psycopg.connect(DATABASE_URL) as pg, pg.cursor() as cur:
        cur.execute(
            """
            INSERT INTO images (lrcat_id, file_path, base_name, extension, camera_model, rating)
            VALUES (999999, '/tmp/test.jpg', 'test', 'jpg', 'X-Pro2', 5)
            ON CONFLICT (lrcat_id) DO UPDATE SET camera_model = EXCLUDED.camera_model
            RETURNING id
            """
        )
        image_id = cur.fetchone()[0]
        pg.commit()
        yield image_id
        cur.execute("DELETE FROM images WHERE id = %s", (image_id,))
        pg.commit()


def test_structured_filter_finds_seeded_image(seeded_image):
    raw = search_archive.invoke({"camera_model": "X-Pro2", "min_rating": 5, "limit": 50})
    results = json.loads(raw)
    assert any(r["id"] == seeded_image for r in results)


def test_structured_filter_excludes_non_matching_camera(seeded_image):
    raw = search_archive.invoke({"camera_model": "Canon EOS 5D", "min_rating": 5, "limit": 50})
    results = json.loads(raw)
    assert all(r["id"] != seeded_image for r in results)
