import json
import random

INPUT_PATH = "incidents.json"
TRAIN_OUT = "train.jsonl"
VALID_OUT = "valid.jsonl"

# ------------------ Load full dataset ------------------

with open(INPUT_PATH, "r", encoding="utf-8") as f:
    all_data = json.load(f)

# Filter only labeled examples
labeled = [inc for inc in all_data if inc.get("labeled")]
total_labeled = len(labeled)
print(f"Loaded {total_labeled} labeled incidents.")

# ------------------ Split into train/valid ------------------

random.seed(42)
random.shuffle(labeled)

train = labeled[:80]
valid = labeled[80:101]   # 21 total

print(f"Train: {len(train)}, Validation: {len(valid)}")

# ------------------ Build Option A prompt ------------------

def build_input(inc):
    meta = inc["meta"]
    prompt = []

    # Opening question
    prompt.append(
        f"Was the penalty for Car {meta['driver_number']} ({meta['driver_name']}) "
        f"in the {meta['year']} {meta['grand_prix']} Grand Prix fair?"
    )
    prompt.append("")

    # Incident details
    prompt.append("Incident details:")
    prompt.append(f"- Session: {meta.get('session', '')}")
    prompt.append(f"- Fact: {meta.get('fact', '')}")
    prompt.append(f"- Penalty Applied: {meta.get('decision', '')}")
    prompt.append("")

    # Precedents
    prompt.append("Relevant precedents:")
    for pid in inc.get("precedent_ids", []):
        # Look up precedence in the *full* dataset (Option B)
        match = next((x for x in all_data if x["current_id"] == pid), None)
        if match:
            pm = match["meta"]
            prompt.append(
                f"- {pm['year']} {pm['grand_prix']} GP – Car {pm['driver_number']} "
                f"({pm['driver_name']}): {pm.get('fact', '')} → {pm.get('decision', '')}"
            )

    prompt.append("")
    prompt.append("Provide a full fairness assessment.")

    return "\n".join(prompt)


def clean_output(text):
    """
    The incidents.json stores newlines escaped as '\\n'.
    Convert them into actual newlines for Gemini fine-tuning.
    """
    return text.replace("\\n", "\n")

# ------------------ Write JSONL files ------------------

def write_jsonl(path, examples):
    with open(path, "w", encoding="utf-8") as f:
        for inc in examples:
            row = {
                "input": build_input(inc),
                "output": clean_output(inc.get("gold_answer", ""))
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote: {path}")


write_jsonl(TRAIN_OUT, train)
write_jsonl(VALID_OUT, valid)
