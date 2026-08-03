"""Read a Lightroom .lrcat catalog (read-only) and load metadata into Postgres.

Phase 1: metadata only, no image pixels touched, no ML. Safe to run repeatedly
(upserts on lrcat_id) as the catalog changes.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import urllib.parse
from dataclasses import dataclass
from datetime import datetime

import psycopg


def open_catalog_readonly(path: str) -> sqlite3.Connection:
    uri = "file:" + urllib.parse.quote(path) + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


@dataclass
class ImageRow:
    lrcat_id: int
    file_path: str
    base_name: str
    extension: str
    capture_time: datetime | None
    file_width: float | None
    file_height: float | None
    orientation: str | None
    camera_model: str | None
    lens: str | None
    focal_length_mm: float | None
    aperture_fnum: float | None
    shutter_speed_s: float | None
    iso: int | None
    gps_lat: float | None
    gps_lon: float | None
    has_gps: bool
    rating: int | None
    pick: int | None
    color_label: str | None
    caption: str | None


def parse_capture_time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    # Lightroom stores e.g. "2014-12-30T15:14:47.00" — camera-local time, no tz.
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def apex_to_fnumber(av: float | None) -> float | None:
    if av is None:
        return None
    return round(2 ** (av / 2), 1)


def apex_to_shutter_seconds(tv: float | None) -> float | None:
    if tv is None:
        return None
    return 2 ** (-tv)


def fetch_images(cat: sqlite3.Connection) -> list[ImageRow]:
    cur = cat.cursor()
    cur.execute(
        """
        SELECT
            i.id_local,
            rf.absolutePath,
            fo.pathFromRoot,
            f.baseName,
            f.extension,
            i.captureTime,
            i.fileWidth,
            i.fileHeight,
            i.orientation,
            i.rating,
            i.pick,
            i.colorLabels,
            cam.value,
            lens.value,
            ex.focalLength,
            ex.aperture,
            ex.shutterSpeed,
            ex.isoSpeedRating,
            ex.gpsLatitude,
            ex.gpsLongitude,
            ex.hasGPS,
            iptc.caption
        FROM Adobe_images i
        JOIN AgLibraryFile f ON f.id_local = i.rootFile
        JOIN AgLibraryFolder fo ON fo.id_local = f.folder
        JOIN AgLibraryRootFolder rf ON rf.id_local = fo.rootFolder
        LEFT JOIN AgHarvestedExifMetadata ex ON ex.image = i.id_local
        LEFT JOIN AgInternedExifCameraModel cam ON cam.id_local = ex.cameraModelRef
        LEFT JOIN AgInternedExifLens lens ON lens.id_local = ex.lensRef
        LEFT JOIN AgLibraryIPTC iptc ON iptc.image = i.id_local
        """
    )
    rows = []
    for r in cur.fetchall():
        (
            lrcat_id, root_path, path_from_root, base_name, extension,
            capture_time_raw, width, height, orientation, rating, pick,
            color_label, camera_model, lens_name, focal_length, aperture,
            shutter_speed, iso, gps_lat, gps_lon, has_gps, caption,
        ) = r

        file_path = os.path.join(root_path, path_from_root, f"{base_name}.{extension}")
        has_gps_bool = bool(has_gps)

        rows.append(
            ImageRow(
                lrcat_id=lrcat_id,
                file_path=file_path,
                base_name=base_name,
                extension=extension,
                capture_time=parse_capture_time(capture_time_raw),
                file_width=width,
                file_height=height,
                orientation=orientation,
                camera_model=camera_model,
                lens=lens_name,
                focal_length_mm=focal_length,
                aperture_fnum=apex_to_fnumber(aperture),
                shutter_speed_s=apex_to_shutter_seconds(shutter_speed),
                iso=int(iso) if iso is not None else None,
                gps_lat=gps_lat if has_gps_bool else None,
                gps_lon=gps_lon if has_gps_bool else None,
                has_gps=has_gps_bool,
                rating=int(rating) if rating else None,
                pick=int(pick) if pick is not None else None,
                color_label=color_label or None,
                caption=caption or None,
            )
        )
    return rows


def fetch_keywords(cat: sqlite3.Connection) -> dict[int, str]:
    cur = cat.cursor()
    cur.execute("SELECT id_local, name FROM AgLibraryKeyword WHERE name IS NOT NULL")
    return {row[0]: row[1] for row in cur.fetchall()}


def fetch_image_keywords(cat: sqlite3.Connection) -> list[tuple[int, int]]:
    cur = cat.cursor()
    cur.execute("SELECT image, tag FROM AgLibraryKeywordImage")
    return cur.fetchall()


def fetch_collections(cat: sqlite3.Connection) -> dict[int, str]:
    cur = cat.cursor()
    cur.execute(
        "SELECT id_local, name FROM AgLibraryCollection WHERE name IS NOT NULL AND systemOnly = 0"
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def fetch_image_collections(cat: sqlite3.Connection) -> list[tuple[int, int, int | None]]:
    cur = cat.cursor()
    cur.execute("SELECT image, collection, pick FROM AgLibraryCollectionImage")
    return cur.fetchall()


def load_into_postgres(
    pg: psycopg.Connection,
    images: list[ImageRow],
    keywords: dict[int, str],
    image_keywords: list[tuple[int, int]],
    collections: dict[int, str],
    image_collections: list[tuple[int, int, int | None]],
) -> None:
    with pg.cursor() as cur:
        for img in images:
            cur.execute(
                """
                INSERT INTO images (
                    lrcat_id, file_path, base_name, extension, capture_time,
                    file_width, file_height, orientation, camera_model, lens,
                    focal_length_mm, aperture_fnum, shutter_speed_s, iso,
                    gps_lat, gps_lon, has_gps, rating, pick, color_label, caption,
                    search_vector, updated_at
                ) VALUES (
                    %(lrcat_id)s, %(file_path)s, %(base_name)s, %(extension)s, %(capture_time)s,
                    %(file_width)s, %(file_height)s, %(orientation)s, %(camera_model)s, %(lens)s,
                    %(focal_length_mm)s, %(aperture_fnum)s, %(shutter_speed_s)s, %(iso)s,
                    %(gps_lat)s, %(gps_lon)s, %(has_gps)s, %(rating)s, %(pick)s, %(color_label)s, %(caption)s,
                    to_tsvector('english', coalesce(%(caption)s, '')), now()
                )
                ON CONFLICT (lrcat_id) DO UPDATE SET
                    file_path = EXCLUDED.file_path,
                    base_name = EXCLUDED.base_name,
                    extension = EXCLUDED.extension,
                    capture_time = EXCLUDED.capture_time,
                    file_width = EXCLUDED.file_width,
                    file_height = EXCLUDED.file_height,
                    orientation = EXCLUDED.orientation,
                    camera_model = EXCLUDED.camera_model,
                    lens = EXCLUDED.lens,
                    focal_length_mm = EXCLUDED.focal_length_mm,
                    aperture_fnum = EXCLUDED.aperture_fnum,
                    shutter_speed_s = EXCLUDED.shutter_speed_s,
                    iso = EXCLUDED.iso,
                    gps_lat = EXCLUDED.gps_lat,
                    gps_lon = EXCLUDED.gps_lon,
                    has_gps = EXCLUDED.has_gps,
                    rating = EXCLUDED.rating,
                    pick = EXCLUDED.pick,
                    color_label = EXCLUDED.color_label,
                    caption = EXCLUDED.caption,
                    search_vector = EXCLUDED.search_vector,
                    updated_at = now()
                """,
                vars(img),
            )

        for lrcat_id, name in keywords.items():
            cur.execute(
                """
                INSERT INTO keywords (lrcat_id, name) VALUES (%s, %s)
                ON CONFLICT (lrcat_id) DO UPDATE SET name = EXCLUDED.name
                """,
                (lrcat_id, name),
            )

        for lrcat_id, name in collections.items():
            cur.execute(
                """
                INSERT INTO collections (lrcat_id, name) VALUES (%s, %s)
                ON CONFLICT (lrcat_id) DO UPDATE SET name = EXCLUDED.name
                """,
                (lrcat_id, name),
            )

        cur.execute("TRUNCATE image_keywords")
        cur.executemany(
            """
            INSERT INTO image_keywords (image_id, keyword_id)
            SELECT i.id, k.id FROM images i, keywords k
            WHERE i.lrcat_id = %s AND k.lrcat_id = %s
            ON CONFLICT DO NOTHING
            """,
            image_keywords,
        )

        cur.execute("TRUNCATE image_collections")
        cur.executemany(
            """
            INSERT INTO image_collections (image_id, collection_id, pick)
            SELECT i.id, c.id, %s FROM images i, collections c
            WHERE i.lrcat_id = %s AND c.lrcat_id = %s
            ON CONFLICT DO NOTHING
            """,
            [(pick, image_id, collection_id) for image_id, collection_id, pick in image_collections],
        )

    pg.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", help="Path to the .lrcat file")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", "postgresql://archive:archive@localhost:5432/archive"),
    )
    args = parser.parse_args()

    cat = open_catalog_readonly(args.catalog)
    print("Reading catalog...")
    images = fetch_images(cat)
    keywords = fetch_keywords(cat)
    image_keywords = fetch_image_keywords(cat)
    collections = fetch_collections(cat)
    image_collections = fetch_image_collections(cat)
    cat.close()

    print(
        f"Read {len(images)} images, {len(keywords)} keywords "
        f"({len(image_keywords)} links), {len(collections)} collections "
        f"({len(image_collections)} links)."
    )

    print("Loading into Postgres...")
    with psycopg.connect(args.database_url) as pg:
        load_into_postgres(pg, images, keywords, image_keywords, collections, image_collections)

    print("Done.")


if __name__ == "__main__":
    main()
