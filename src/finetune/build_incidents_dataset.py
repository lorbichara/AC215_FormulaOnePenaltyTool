import json
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


RAW_PATH = Path("src/finetune/data/incidents_raw.json")
OUT_PATH = Path("src/finetune/data/incidents.json")


# ---------- helpers ----------


def load_raw_incidents() -> List[Dict[str, Any]]:
    with RAW_PATH.open("r") as f:
        return json.load(f)


def is_real_incident(item: Dict[str, Any]) -> bool:
    """
    Keep only driver-specific penalty incidents that make sense
    for fairness analysis.
    """
    if not item.get("incident_id"):
        return False
    if not item.get("driver_number") or not item.get("driver_name"):
        return False
    if not item.get("fact") or not item.get("decision"):
        return False

    text = " ".join(
        [
            item.get("file_name", ""),
            item.get("fact", "") or "",
            item.get("decision", "") or "",
        ]
    ).lower()

    # Filter out timing sheets, schedule notes, etc.
    bad_keywords = [
        "deleted lap time",
        "deleted lap times",
        "sc2-sc1",
        "sc2 sc1",
        "schedule clarification",
        "drivers meeting",
        "championship points",
        "track familiarisation",
        "right of review",
        "race deleted lap times",
        "qualifying deleted lap times",
        "sprint shootout deleted lap times",
    ]

    if any(k in text for k in bad_keywords):
        return False

    return True


def infer_category(item: Dict[str, Any]) -> str:
    """
    Rough incident category based on fact/offence/filename.
    Used only for grouping similar incidents for precedents.
    """
    text = " ".join(
        [
            item.get("file_name", ""),
            item.get("fact", "") or "",
            item.get("offence", "") or "",
        ]
    ).lower()

    if "collision" in text or "collided" in text:
        return "collision"
    if "leaving the track" in text or "track limits" in text:
        return "track_limits"
    if "pit lane speeding" in text or "pit lane speed" in text:
        return "pit_lane_speeding"
    if "unsafe release" in text or "released in an unsafe condition" in text:
        return "unsafe_release"
    if "yellow flag" in text:
        return "yellow_flags"
    if "power unit" in text or "pu element" in text or "pu elements" in text:
        return "power_unit"
    if "parc ferme" in text:
        return "parc_ferme"
    if (
        "incorrect starting location" in text
        or "moved before start signal" in text
        or "jump start" in text
    ):
        return "start_procedure"
    if "equipment in the pit lane" in text:
        return "pit_lane_equipment"
    return "other"


def format_gp_name(raw: str) -> str:
    if not raw:
        return ""
    # "MEXICO CITY" -> "Mexico City", "ITALIAN" -> "Italian"
    return raw.title()


def build_embedding_text(item: Dict[str, Any]) -> str:
    gp = format_gp_name(item.get("grand_prix", ""))
    return (
        f"{item.get('year', '')} {gp} Grand Prix. "
        f"Session: {item.get('session', '')}. "
        f"Car {item.get('driver_number', '')} {item.get('driver_name', '')}. "
        f"Fact: {item.get('fact', '')}. "
        f"Decision: {item.get('decision', '')}."
    )


def compute_embeddings(incidents: List[Dict[str, Any]]) -> np.ndarray:
    texts = [build_embedding_text(i) for i in incidents]
    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    return emb


def group_by_category(incidents: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    groups: Dict[str, List[int]] = {}
    for idx, inc in enumerate(incidents):
        cat = inc["category"]
        groups.setdefault(cat, []).append(idx)
    return groups


def choose_precedents(
    incidents: List[Dict[str, Any]],
    embeddings: np.ndarray,
    top_k: int = 3,
) -> Dict[int, List[int]]:
    """
    For each incident index i, return a list of indices of precedent incidents.
    Only choose precedents within the same category.
    """
    category_groups = group_by_category(incidents)
    precedents: Dict[int, List[int]] = {}

    for cat, idxs in category_groups.items():
        if len(idxs) <= 1:
            # Nothing to compare within this category
            for idx in idxs:
                precedents[idx] = []
            continue

        cat_emb = embeddings[idxs]
        sim = cosine_similarity(cat_emb, cat_emb)

        for local_i, idx_i in enumerate(idxs):
            # Exclude self
            sim[local_i, local_i] = -1.0
            # Top-k most similar
            order = np.argsort(sim[local_i])[::-1]
            chosen = []
            for j in order:
                if sim[local_i, j] <= 0:
                    # skip negative / zero similarity
                    continue
                chosen.append(idxs[j])
                if len(chosen) >= top_k:
                    break
            precedents[idx_i] = chosen

    return precedents


def build_gold_answer_template(
    inc: Dict[str, Any],
    precedents: List[Dict[str, Any]],
) -> str:
    gp = format_gp_name(inc.get("grand_prix", ""))
    summary = f"""[Incident Summary]
- Driver: {inc.get('driver_name', '')} (Car {inc.get('driver_number', '')})
- Race: {inc.get('year', '')} {gp} Grand Prix ({inc.get('session', '')})
- Infringement: {inc.get('fact', '').strip()}
- Penalty Applied: {inc.get('decision', '').strip()}

[Comparable Precedents]"""

    lines = [summary]

    if precedents:
        for idx, p in enumerate(precedents, start=1):
            pgp = format_gp_name(p.get("grand_prix", ""))
            line = (
                f"\n{idx}) {p.get('year', '')} {pgp} Grand Prix – "
                f"Car {p.get('driver_number', '')} ({p.get('driver_name', '')}) – "
                f"{(p.get('fact') or '').strip()} → {(p.get('decision') or '').strip()}\n"
                f"   Similarities:\n"
                f"   Differences:"
            )
            lines.append(line)
    else:
        lines.append(
            "\n1) <Add a precedent manually>\n   Similarities:\n   Differences:"
        )

    framework = """
[Fairness Framework]
- Safety Impact:
- Advantage Gained:
- Intent:
- Consistency with Precedent:

[Fairness Score]
Score: X/5
Judgement:
Explanation:
"""

    lines.append(framework.rstrip() + "\n")
    return "\n".join(lines)


def build_question(inc: Dict[str, Any]) -> str:
    gp = format_gp_name(inc.get("grand_prix", ""))
    return (
        f"Was the penalty for Car {inc.get('driver_number', '')} "
        f"({inc.get('driver_name', '')}) in the {inc.get('year', '')} "
        f"{gp} Grand Prix fair?"
    )


# ---------- main pipeline ----------


def build_incidents_dataset() -> List[Dict[str, Any]]:
    print(f"Loading raw incidents from {RAW_PATH} ...")
    raw = load_raw_incidents()
    print(f"Total rows in incidents_raw.json: {len(raw)}")

    # 1) filter
    filtered: List[Dict[str, Any]] = []
    for item in raw:
        if is_real_incident(item):
            # add category
            item = dict(item)  # shallow copy
            item["category"] = infer_category(item)
            filtered.append(item)

    print(f"Kept {len(filtered)} driver-specific penalty incidents.")

    if not filtered:
        print("No valid incidents found after filtering. Aborting.")
        return []

    # 2) embeddings + precedents
    print("Computing embeddings for precedent matching ...")
    embeddings = compute_embeddings(filtered)

    print("Selecting precedents based on cosine similarity within categories ...")
    idx_to_precedent_idxs = choose_precedents(filtered, embeddings, top_k=3)

    # index by incident_id for lookups
    by_idx = {i: inc for i, inc in enumerate(filtered)}

    # 3) build final records
    final_records: List[Dict[str, Any]] = []

    for idx, inc in enumerate(filtered):
        precedent_idxs = idx_to_precedent_idxs.get(idx, [])
        precedent_items = [by_idx[j] for j in precedent_idxs]

        record = {
            "current_id": inc["incident_id"],
            "precedent_ids": [p["incident_id"] for p in precedent_items],
            "question": build_question(inc),
            "gold_answer": build_gold_answer_template(inc, precedent_items),
            "meta": {
                "category": inc["category"],
                "file_path": inc.get("file_path"),
                "grand_prix": format_gp_name(inc.get("grand_prix", "")),
                "year": inc.get("year"),
                "driver_number": inc.get("driver_number"),
                "driver_name": inc.get("driver_name"),
                "session": inc.get("session"),
                "fact": inc.get("fact"),
                "decision": inc.get("decision"),
            },
        }

        final_records.append(record)

    # 4) save
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        json.dump(final_records, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(final_records)} labeled templates to {OUT_PATH}")
    return final_records


if __name__ == "__main__":
    build_incidents_dataset()
