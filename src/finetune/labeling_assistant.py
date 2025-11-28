import json
from pathlib import Path
import tempfile
import subprocess
import hashlib

INCIDENTS_PATH = Path("src/finetune/data/incidents.json")
BACKUP_PATH = Path("src/finetune/data/incidents_backup.json")


def load_incidents():
    with INCIDENTS_PATH.open("r") as f:
        return json.load(f)


def save_incidents(data):
    with INCIDENTS_PATH.open("w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def show_incident(inc):
    meta = inc["meta"]
    print("\n" + "=" * 80)
    print(f"Incident   : {inc['current_id']}")
    print(f"Grand Prix : {meta['year']} {meta['grand_prix']}")
    print(f"Driver     : {meta['driver_name']} (Car {meta['driver_number']})")
    print(f"Session    : {meta['session']}")
    print(f"Fact       : {meta['fact']}")
    print(f"Decision   : {meta['decision']}")
    print("=" * 80)


def get_precedents(inc, all_incidents):
    items = []
    print("\n--- PRECEDENTS ---")
    for pid in inc["precedent_ids"]:
        p = next((x for x in all_incidents if x["current_id"] == pid), None)
        if p:
            meta = p["meta"]
            print("\n-----------------------------------------------")
            print(f"Precedent ID: {pid}")
            print(f"Grand Prix  : {meta['year']} {meta['grand_prix']}")
            print(f"Driver      : {meta['driver_name']} (Car {meta['driver_number']})")
            print(f"Fact        : {meta['fact']}")
            print(f"Decision    : {meta['decision']}")
            print("-----------------------------------------------")
            items.append(p)
    return items


def make_json_safe(text):
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def build_blank_template(current_inc, precedents):
    meta = current_inc["meta"]
    t = []

    t.append("[Incident Summary]")
    t.append(f"- Driver: {meta['driver_name']} (Car {meta['driver_number']})")
    t.append(
        f"- Race: {meta['year']} {meta['grand_prix']} Grand Prix ({meta['session']})"
    )
    t.append(f"- Infringement: {meta['fact']}")
    t.append(f"- Penalty Applied: {meta['decision']}")
    t.append("")

    t.append("[Comparable Precedents]")
    for i, p in enumerate(precedents, start=1):
        pm = p["meta"]
        t.append(
            f"{i}) {pm['year']} {pm['grand_prix']} GP – Car {pm['driver_number']} ({pm['driver_name']}) – {pm['fact']} → {pm['decision']}"
        )
        t.append("   Similarities:")
        t.append("   Differences:")
        t.append("")

    t.append("[Fairness Framework]")
    t.append("- Safety Impact:")
    t.append("- Advantage Gained:")
    t.append("- Intent:")
    t.append("- Consistency with Precedent:")
    t.append("")

    t.append("[Fairness Score]")
    t.append("Score:")
    t.append("Judgement:")
    t.append("Explanation:")

    return "\n".join(t)


def open_editor_with_text(initial_text):
    """
    Open macOS TextEdit to edit the gold_answer.
    """

    # Create temp file
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w+") as tf:
        tf.write(initial_text)
        tf.flush()
        temp_path = tf.name

    # Open with TextEdit
    subprocess.call(["open", "-a", "TextEdit", temp_path])

    input(
        "\nPress ENTER when you have finished editing and saved the file in TextEdit... "
    )

    # Read saved content back
    with open(temp_path, "r") as f:
        return f.read()


# -------------------------------------------------------------------------
# NEW: DUPLICATE DETECTION
# -------------------------------------------------------------------------


def make_signature(inc):
    """
    Create a normalized signature to detect duplicates, including symmetric
    collisions (e.g., Car A collided with Car B == Car B collided with Car A).
    """
    meta = inc.get("meta", {})

    def safe(val):
        if val is None:
            return ""
        return str(val).strip().lower()

    fact = safe(meta.get("fact"))

    # Handle symmetric collision wording
    # Look for patterns like "car 22 collided with car 81"
    import re

    match = re.search(r"car\s*(\d+)\s*collided with car\s*(\d+)", fact)
    if match:
        a, b = sorted([match.group(1), match.group(2)])
        # Normalize collision description to "car a-car b"
        fact = f"collision cars {a}-{b}"

    key = (
        safe(meta.get("grand_prix"))
        + safe(meta.get("year"))
        + safe(meta.get("session"))
        + fact
    )

    return hashlib.md5(key.encode("utf-8")).hexdigest()


def detect_duplicates(incidents):
    signatures = {}
    for inc in incidents:
        sig = make_signature(inc)
        if sig in signatures:
            inc["duplicate"] = True
        else:
            inc["duplicate"] = False
            signatures[sig] = True


# -------------------------------------------------------------------------


def labeling_loop():
    incidents = load_incidents()

    # Backup once
    if not BACKUP_PATH.exists():
        with BACKUP_PATH.open("w") as f:
            json.dump(incidents, f, indent=2, ensure_ascii=False)
        print(f"Backup created at {BACKUP_PATH}")

    # Add labeled flag if missing
    for inc in incidents:
        if "labeled" not in inc:
            inc["labeled"] = False

    # Detect duplicates before labeling begins
    detect_duplicates(incidents)

    print("\nStarting full-screen labeling assistant...\n")

    for idx, inc in enumerate(incidents):
        print(f"\n##### INCIDENT {idx + 1} OF {len(incidents)} #####")

        # NEW: Skip duplicates
        if inc.get("duplicate", False):
            print("Duplicate incident — skipping.")
            continue

        # Show incident even if labeled so user can re-do
        show_incident(inc)
        precedents = get_precedents(inc, incidents)

        redo = "y"
        if inc["labeled"]:
            redo = (
                input("\nAlready labeled. Re-do this incident? (y/n): ").strip().lower()
            )

        if redo != "y":
            continue

        # Build blank template
        template = build_blank_template(inc, precedents)

        print("\nOpening editor for you to fill in the gold_answer...\n")

        user_text = open_editor_with_text(template)

        print("\n--- Your Entered Text ---\n")
        print(user_text)

        save = input("\nSave this answer? (y/n): ").strip().lower()
        if save == "y":
            inc["gold_answer"] = make_json_safe(user_text)
            inc["labeled"] = True
            save_incidents(incidents)
            print("Saved ✓")
        else:
            print("Skipped — not saved.")

        cont = input("\nContinue to next incident? (y/n): ").strip().lower()
        if cont != "y":
            break

    print("\nLabeling complete or paused. Resume anytime.")


if __name__ == "__main__":
    labeling_loop()
