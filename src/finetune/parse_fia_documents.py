import re
import json
from pathlib import Path
import pdfplumber

DATA_ROOT = Path("src/datapipeline/data")  # <--- YOUR DATA LOCATION


def is_penalty_document(text):
    """
    Identify real FIA 'Decision' or 'Offence' documents.
    """
    return "From The Stewards" in text and (
        "Offence" in text or "Decision" in text or "Fact" in text
    )


def extract_field(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None


def generate_incident_id(grand_prix, year, driver_number, fact):
    gp = re.sub(r"[^a-z0-9]", "", grand_prix.lower().replace("grandprix", "gp"))
    short_fact = fact[:30].lower().replace(" ", "_")
    short_fact = re.sub(r"[^a-z0-9_]", "", short_fact)
    return f"{year}_{gp}_{driver_number}_{short_fact}"


def parse_pdf(path):
    """
    Parse an FIA penalty PDF and extract structured fields.
    Returns None if not a valid decision/offence document.
    """
    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    if not is_penalty_document(text):
        return None

    data = {}
    data["file_path"] = str(path)
    data["file_name"] = path.name

    # Grand Prix
    gp_match = re.search(r"\d{4}\s+(.+?)\s+GRAND PRIX", text, re.IGNORECASE)
    data["grand_prix"] = gp_match.group(1).strip() if gp_match else None

    # Year
    year_match = re.search(r"(20\d{2})", text)
    data["year"] = year_match.group(1) if year_match else None

    # Driver info
    driver_line = extract_field(r"No\s*/\s*Driver\s*(.+)", text)
    if driver_line and "-" in driver_line:
        num, name = driver_line.split("-", 1)
        data["driver_number"] = num.strip()
        data["driver_name"] = name.strip()
    else:
        data["driver_number"] = None
        data["driver_name"] = None

    # Other fields
    data["competitor"] = extract_field(r"Competitor\s*(.+)", text)
    data["session"] = extract_field(r"Session\s*(.+)", text)
    data["fact"] = extract_field(r"Fact\s*(.+)", text)
    data["offence"] = extract_field(r"Offence\s*(.+)", text)
    data["decision"] = extract_field(r"Decision\s*(.+)", text)
    data["reason"] = extract_field(r"Reason\s*(.+)", text)

    # Construct incident ID
    if data["grand_prix"] and data["year"] and data["driver_number"] and data["fact"]:
        data["incident_id"] = generate_incident_id(
            data["grand_prix"], data["year"], data["driver_number"], data["fact"]
        )
    else:
        data["incident_id"] = None

    return data


def parse_all_pdfs(data_root=DATA_ROOT, output_json="incidents_raw.json"):
    """
    Recursively walk through src/datapipeline/data/<season> directories
    and parse all PDFs that look like penalty documents.
    """
    incidents = []
    pdf_count = 0

    for pdf_path in data_root.rglob("*.pdf"):  # <--- RECURSIVE
        pdf_count += 1
        parsed = parse_pdf(pdf_path)
        if parsed:
            incidents.append(parsed)

    # Write output
    output_path = Path("src/finetune/data") / output_json
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(incidents, f, indent=2)

    print(f"Scanned {pdf_count} PDFs.")
    print(f"Extracted {len(incidents)} valid penalty incidents.")
    print(f"Saved to {output_path}")

    return incidents


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        folder = Path(sys.argv[1])
        parse_all_pdfs(data_root=folder)
    else:
        parse_all_pdfs()  # default scans all seasons
