"""The archive search tool the agent calls. One tool, two retrieval modes:
semantic (caption/keyword embedding, pgvector cosine distance) and
structured (EXIF/keyword/collection/rating filters), combinable in one call.
"""
from __future__ import annotations

import json
import os

import psycopg
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://archive:archive@localhost:5433/archive"
)
EMBEDDING_MODEL = "text-embedding-3-small"

_embeddings: OpenAIEmbeddings | None = None


def _get_embeddings() -> OpenAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    return _embeddings


def _connect():
    return psycopg.connect(DATABASE_URL)


@tool
def search_archive(
    semantic_query: str | None = None,
    camera_model: str | None = None,
    collection: str | None = None,
    keyword: str | None = None,
    min_rating: int | None = None,
    capture_year: int | None = None,
    limit: int = 12,
) -> str:
    """Search the photo archive (metadata ingested from Lightroom).

    Args:
        semantic_query: free-text description of visual content / subject /
            mood to match against image captions and keyword text via
            embedding similarity (e.g. "wet street at dusk, reflections").
            Leave null for a pure metadata filter with no semantic ranking.
        camera_model: exact or partial camera model, e.g. "X-Pro2".
        collection: exact or partial Lightroom collection name.
        keyword: exact or partial Lightroom keyword.
        min_rating: minimum star rating (1-5).
        capture_year: four-digit year the photo was taken.
        limit: max results to return, default 12.

    Returns a JSON string: a list of matches with id, file_path, caption,
    camera_model, capture_time, rating, keywords, collections, and
    (if semantic_query was given) a similarity score.
    """
    where = []
    params: dict = {}

    if camera_model:
        where.append("i.camera_model ILIKE %(camera_model)s")
        params["camera_model"] = f"%{camera_model}%"
    if min_rating is not None:
        where.append("i.rating >= %(min_rating)s")
        params["min_rating"] = min_rating
    if capture_year is not None:
        where.append("extract(year from i.capture_time) = %(capture_year)s")
        params["capture_year"] = capture_year
    if collection:
        where.append(
            "EXISTS (SELECT 1 FROM image_collections ic JOIN collections c ON c.id = ic.collection_id "
            "WHERE ic.image_id = i.id AND c.name ILIKE %(collection)s)"
        )
        params["collection"] = f"%{collection}%"
    if keyword:
        where.append(
            "EXISTS (SELECT 1 FROM image_keywords ik JOIN keywords k ON k.id = ik.keyword_id "
            "WHERE ik.image_id = i.id AND k.name ILIKE %(keyword)s)"
        )
        params["keyword"] = f"%{keyword}%"

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with _connect() as pg, pg.cursor() as cur:
        if semantic_query:
            query_vector = _get_embeddings().embed_query(semantic_query)
            vector_literal = "[" + ",".join(str(x) for x in query_vector) + "]"
            params["query_vector"] = vector_literal
            params["limit"] = limit
            sql = f"""
                SELECT i.id, i.file_path, i.caption, i.camera_model, i.capture_time,
                       i.rating, 1 - (i.caption_embedding <=> %(query_vector)s) AS similarity
                FROM images i
                {where_sql}{' AND' if where else ' WHERE'} i.caption_embedding IS NOT NULL
                ORDER BY i.caption_embedding <=> %(query_vector)s
                LIMIT %(limit)s
            """
        else:
            params["limit"] = limit
            sql = f"""
                SELECT i.id, i.file_path, i.caption, i.camera_model, i.capture_time,
                       i.rating, NULL AS similarity
                FROM images i
                {where_sql}
                ORDER BY i.capture_time DESC NULLS LAST
                LIMIT %(limit)s
            """

        cur.execute(sql, params)
        rows = cur.fetchall()

        results = []
        for image_id, file_path, caption, cam, capture_time, rating, similarity in rows:
            cur.execute(
                """
                SELECT k.name FROM image_keywords ik JOIN keywords k ON k.id = ik.keyword_id
                WHERE ik.image_id = %s
                """,
                (image_id,),
            )
            keywords = [r[0] for r in cur.fetchall()]
            cur.execute(
                """
                SELECT c.name FROM image_collections ic JOIN collections c ON c.id = ic.collection_id
                WHERE ic.image_id = %s
                """,
                (image_id,),
            )
            collections = [r[0] for r in cur.fetchall()]

            results.append(
                {
                    "id": image_id,
                    "file_path": file_path,
                    "caption": caption,
                    "camera_model": cam,
                    "capture_time": capture_time.isoformat() if capture_time else None,
                    "rating": rating,
                    "similarity": round(similarity, 4) if similarity is not None else None,
                    "keywords": keywords,
                    "collections": collections,
                }
            )

    return json.dumps(results)
