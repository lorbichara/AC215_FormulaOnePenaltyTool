import json


def convert_jsonl(in_path, out_path):
    """
    Converts a JSONL file with {"input": ..., "output": ...}
    into Gemini Console fine-tuning format with "contents".
    """
    with (
        open(in_path, "r", encoding="utf-8") as f_in,
        open(out_path, "w", encoding="utf-8") as f_out,
    ):

        for line in f_in:
            if not line.strip():
                continue

            ex = json.loads(line)

            converted = {
                "contents": [
                    {"role": "user", "parts": [{"text": ex["input"]}]},
                    {"role": "model", "parts": [{"text": ex["output"]}]},
                ]
            }

            f_out.write(json.dumps(converted, ensure_ascii=False) + "\n")

    print(f"✓ Converted {in_path} → {out_path}")


# ----------------------------
# Run conversion
# ----------------------------

convert_jsonl("train.jsonl", "train_converted.jsonl")
convert_jsonl("valid.jsonl", "valid_converted.jsonl")
