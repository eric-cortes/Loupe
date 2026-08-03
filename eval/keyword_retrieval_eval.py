"""Phase 3 baseline: keyword-retrieval eval, no ML.

Ground truth: for each Lightroom keyword, the images tagged with it are
the relevant set. Keywords are NOT part of `images.search_vector` (only the
IPTC caption is), so this measures a pure full-text-search baseline — the
number embeddings need to beat later.

Usage: .venv/bin/python eval/keyword_retrieval_eval.py
"""
from __future__ import annotations

import csv
import os
import re
import statistics
from dataclasses import dataclass, field

import psycopg

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://archive:archive@localhost:5433/archive"
)

# Keywords tagged on more than this many images are blanket/catalog-wide tags
# (e.g. a keyword applied to nearly every image regardless of subject) rather
# than discriminative subject labels.
# They're reported separately so they don't dilute the meaningful numbers.
BLANKET_TAG_THRESHOLD = 200

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


@dataclass
class KeywordResult:
    name: str
    support: int
    ceiling_recall: float  # max achievable recall given only 530 images have captions
    precision_at_5: float
    precision_at_10: float
    recall_at_10: float
    recall_at_20: float
    reciprocal_rank: float
    query_matched_anything: bool
    relevant_ids: frozenset = field(repr=False, compare=False)


def clean_query_text(name: str) -> str:
    # Strip zero-width spaces and trailing punctuation Lightroom keyword names
    # sometimes carry (e.g. "​Portrait", "Landscape.").
    name = name.replace("\u200b", "")
    return re.sub(r"[.\s]+$", "", name).strip()


def fetch_keyword_support(cur) -> dict[str, set[int]]:
    cur.execute(
        """
        SELECT k.name, ik.image_id
        FROM image_keywords ik
        JOIN keywords k ON k.id = ik.keyword_id
        """
    )
    support: dict[str, set[int]] = {}
    for name, image_id in cur.fetchall():
        support.setdefault(name, set()).add(image_id)
    return support


def fetch_images_with_caption(cur) -> set[int]:
    cur.execute("SELECT id FROM images WHERE caption IS NOT NULL")
    return {row[0] for row in cur.fetchall()}


def run_query(cur, query_text: str) -> list[int]:
    cur.execute(
        """
        SELECT id
        FROM images
        WHERE search_vector @@ plainto_tsquery('english', %s)
        ORDER BY ts_rank(search_vector, plainto_tsquery('english', %s)) DESC
        """,
        (query_text, query_text),
    )
    return [row[0] for row in cur.fetchall()]


def precision_at_k(retrieved: list[int], relevant: set[int], k: int) -> float:
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for i in top_k if i in relevant)
    return hits / k


def recall_at_k(retrieved: list[int], relevant: set[int], k: int) -> float:
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for i in top_k if i in relevant)
    return hits / len(relevant)


def reciprocal_rank(retrieved: list[int], relevant: set[int]) -> float:
    for rank, image_id in enumerate(retrieved, start=1):
        if image_id in relevant:
            return 1.0 / rank
    return 0.0


def evaluate_keyword(cur, name: str, relevant: set[int], captioned: set[int]) -> KeywordResult:
    query_text = clean_query_text(name)
    retrieved = run_query(cur, query_text) if query_text else []
    ceiling_recall = len(relevant & captioned) / len(relevant) if relevant else 0.0
    return KeywordResult(
        name=name,
        support=len(relevant),
        ceiling_recall=ceiling_recall,
        precision_at_5=precision_at_k(retrieved, relevant, 5),
        precision_at_10=precision_at_k(retrieved, relevant, 10),
        recall_at_10=recall_at_k(retrieved, relevant, 10),
        recall_at_20=recall_at_k(retrieved, relevant, 20),
        reciprocal_rank=reciprocal_rank(retrieved, relevant),
        query_matched_anything=bool(retrieved),
        relevant_ids=frozenset(relevant),
    )


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def print_and_save_table(rows: list[KeywordResult], label: str, writer: csv.writer | None) -> None:
    print(f"\n=== {label} (n={len(rows)}) ===")
    print(
        f"{'keyword':<28} {'support':>7} {'ceiling_r':>10} "
        f"{'P@5':>6} {'P@10':>6} {'R@10':>6} {'R@20':>6} {'MRR':>6}"
    )
    for r in sorted(rows, key=lambda r: -r.support):
        print(
            f"{r.name[:28]:<28} {r.support:>7} {r.ceiling_recall:>10.2f} "
            f"{r.precision_at_5:>6.2f} {r.precision_at_10:>6.2f} "
            f"{r.recall_at_10:>6.2f} {r.recall_at_20:>6.2f} {r.reciprocal_rank:>6.2f}"
        )
        if writer:
            writer.writerow(
                [
                    label, r.name, r.support, f"{r.ceiling_recall:.4f}",
                    f"{r.precision_at_5:.4f}", f"{r.precision_at_10:.4f}",
                    f"{r.recall_at_10:.4f}", f"{r.recall_at_20:.4f}",
                    f"{r.reciprocal_rank:.4f}",
                ]
            )
    if rows:
        print(
            f"{'MEAN':<28} {'':>7} {mean([r.ceiling_recall for r in rows]):>10.2f} "
            f"{mean([r.precision_at_5 for r in rows]):>6.2f} "
            f"{mean([r.precision_at_10 for r in rows]):>6.2f} "
            f"{mean([r.recall_at_10 for r in rows]):>6.2f} "
            f"{mean([r.recall_at_20 for r in rows]):>6.2f} "
            f"{mean([r.reciprocal_rank for r in rows]):>6.2f}"
        )


def main() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with psycopg.connect(DATABASE_URL) as pg, pg.cursor() as cur:
        support = fetch_keyword_support(cur)
        captioned = fetch_images_with_caption(cur)
        cur.execute("SELECT count(*) FROM images")
        total_images = cur.fetchone()[0]

        results = [
            evaluate_keyword(cur, name, ids, captioned) for name, ids in support.items()
        ]

    blanket = [r for r in results if r.support > BLANKET_TAG_THRESHOLD]
    specific = [r for r in results if r.support <= BLANKET_TAG_THRESHOLD]

    # Many "specific" keywords are aliases applied to the identical image set
    # (e.g. multiple language/spelling variants of the same subject tag the
    # same handful of images). Dedupe by relevant-set identity so the headline
    # number isn't inflated by counting one story N times under N different
    # keyword names.
    seen_sets: dict[frozenset, KeywordResult] = {}
    for r in specific:
        if r.relevant_ids not in seen_sets:
            seen_sets[r.relevant_ids] = r
    deduped_specific = list(seen_sets.values())

    csv_path = os.path.join(RESULTS_DIR, "keyword_retrieval_baseline.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["bucket", "keyword", "support", "ceiling_recall", "p@5", "p@10", "r@10", "r@20", "mrr"]
        )
        print_and_save_table(blanket, "Blanket / catalog-wide tags (not discriminative)", writer)
        print_and_save_table(specific, "Specific keywords (naive, includes aliases)", writer)
        print_and_save_table(
            deduped_specific,
            f"Specific keywords, deduped to {len(deduped_specific)} distinct relevant-sets",
            writer,
        )

    no_match = [r.name for r in results if not r.query_matched_anything]
    print(f"\nKeywords whose text never matched any caption at all: {len(no_match)}/{len(results)}")
    print(f"  {no_match}")
    print(f"\nCaption coverage: {len(captioned)}/{total_images} images have an IPTC caption.")
    print(f"Results written to {csv_path}")


if __name__ == "__main__":
    main()
