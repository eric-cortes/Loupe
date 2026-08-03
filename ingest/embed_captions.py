"""Embed per-image text into pgvector via OpenAI embeddings.

Text priority: real IPTC caption > synthesized text from keywords + camera +
collection membership > skip (no text at all to embed).

This is the text-embedding half of the multi-vector design in the spec.
Image-embedding (SigLIP on actual pixels) is a separate, later step that
needs the source images mounted/accessible.
"""
from __future__ import annotations

import os

import psycopg
from openai import OpenAI

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://archive:archive@localhost:5433/archive"
)
EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100


def build_fallback_text(cur, image_id: int, camera_model: str | None, lens: str | None) -> str | None:
    cur.execute(
        """
        SELECT k.name FROM image_keywords ik
        JOIN keywords k ON k.id = ik.keyword_id
        WHERE ik.image_id = %s
        """,
        (image_id,),
    )
    keywords = [row[0] for row in cur.fetchall()]

    cur.execute(
        """
        SELECT c.name FROM image_collections ic
        JOIN collections c ON c.id = ic.collection_id
        WHERE ic.image_id = %s
        """,
        (image_id,),
    )
    collections = [row[0] for row in cur.fetchall()]

    parts = []
    if keywords:
        parts.append(", ".join(keywords))
    if collections:
        parts.append("from collections: " + ", ".join(collections))
    if camera_model:
        parts.append(f"shot on {camera_model}" + (f" with {lens}" if lens else ""))

    return ". ".join(parts) if parts else None


def fetch_images_needing_embedding(cur) -> list[tuple[int, str | None, str | None, str | None]]:
    cur.execute(
        """
        SELECT id, caption, camera_model, lens
        FROM images
        WHERE caption_embedding IS NULL
        """
    )
    return cur.fetchall()


def main() -> None:
    client = OpenAI()  # reads OPENAI_API_KEY from env

    with psycopg.connect(DATABASE_URL) as pg, pg.cursor() as cur:
        rows = fetch_images_needing_embedding(cur)
        print(f"{len(rows)} images without an embedding.")

        to_embed: list[tuple[int, str]] = []
        skipped = 0
        for image_id, caption, camera_model, lens in rows:
            text = caption or build_fallback_text(cur, image_id, camera_model, lens)
            if text:
                to_embed.append((image_id, text))
            else:
                skipped += 1

        print(f"{len(to_embed)} have embeddable text, {skipped} have nothing to embed at all.")

        for i in range(0, len(to_embed), BATCH_SIZE):
            batch = to_embed[i : i + BATCH_SIZE]
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=[text for _, text in batch],
            )
            for (image_id, text), item in zip(batch, response.data):
                vector_literal = "[" + ",".join(str(x) for x in item.embedding) + "]"
                cur.execute(
                    """
                    UPDATE images
                    SET caption_embedding = %s, embedded_text = %s, updated_at = now()
                    WHERE id = %s
                    """,
                    (vector_literal, text, image_id),
                )
            pg.commit()
            print(f"Embedded {min(i + BATCH_SIZE, len(to_embed))}/{len(to_embed)}")

    print("Done.")


if __name__ == "__main__":
    main()
