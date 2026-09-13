"""Clean and standardize price/MSP dataset records.

This file normalizes mandi identifiers, crop names, districts, dates, and
numeric price values so downstream analysis works with consistent data.
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path

# Base directory containing the raw dataset files.
root = Path(r"c:\Users\Manya\Downloads\track3_agritech_dataset_files")
json_path = root / "track3_price_and_msp.json"
master_path = root / "track3_mandi_master.csv"

# Standardized crop names used for consistent crop analysis across varied spellings.
crop_map = {
    "kapas": "Cotton",
    "cotton": "Cotton",
    "कपास": "Cotton",
    "wheat": "Wheat",
    "gehun": "Wheat",
    "गेहूं": "Wheat",
    "kanak": "Wheat",
    "rice": "Rice",
    "dhaan": "Rice",
    "धान": "Rice",
    "paddy": "Rice",
    "basmati": "Rice",
    "sugarcane": "Sugarcane",
    "ganna": "Sugarcane",
    "गन्ना": "Sugarcane",
    "maize": "Maize",
    "makka": "Maize",
    "corn": "Maize",
    "मक्का": "Maize",
    "mustard": "Mustard",
    "sarson": "Mustard",
    "सरसों": "Mustard",
    "barley": "Barley",
    "gram": "Gram",
    "chana": "Gram",
    "soyabean": "Soyabean",
    "soybean": "Soyabean",
    "groundnut": "Groundnut",
    "moong": "Moong",
    "urad": "Urad",
}


def clean_mandi_id(value):
    """Convert mandi identifiers to a consistent MANDI### format."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return None

    # Extract only numbers to normalize values such as 'Mandi 012', 'A-12', etc.
    digits = re.sub(r"\D+", "", s)
    if not digits:
        return None
    return f"MANDI{int(digits):03d}"


def clean_crop(value):
    """Normalize crop names to a standard English label with common aliases."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return ""

    # Normalize spacing and separators so variants like 'wheat-crop' match the map.
    key = s.lower().replace("_", " ").replace("-", " ")
    key = " ".join(key.split())

    canonical = crop_map.get(key)
    if canonical:
        return canonical

    # Fallback to partial alias matching for values containing a known crop phrase.
    for alias, name in crop_map.items():
        if alias in key:
            return name

    return s.title()


def clean_district(value):
    """Standardize district names by trimming whitespace and title-casing them."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "null", ""}:
        return ""
    return s.title()


def parse_numeric(value, *, price_mode=False):
    """Convert currencies and numeric strings into clean float values."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        num = float(value)
    else:
        s = str(value).strip()
        if not s or s.lower() in {"nan", "none", "null", ""}:
            return None

        # Strip currency symbols and formatting characters commonly found in raw data.
        s = s.replace("₹", "").replace("Rs", "").replace("INR", "").replace(",", "").replace("/-", "").replace("-", "")
        s = s.replace(" ", "")
        s = re.sub(r"[^0-9.\-]", "", s)
        if s in {"", ".", "-", "-."}:
            return None
        try:
            num = float(s)
        except ValueError:
            return None

    if price_mode and 0 < abs(num) < 1:
        num *= 10000
    return num


def parse_date(value):
    """Normalize dates from common formats into a consistent YYYY-MM-DD string."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d-%b-%Y",
        "%d/%b/%Y",
        "%d-%B-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%m-%d-%Y",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # If the date is already in a valid but unrecognized format, keep the original text.
    return s


# Load the raw JSON dataset.
with json_path.open("r", encoding="utf-8") as f:
    records = json.load(f)

# Build a lookup of mandi_id to district using the master reference dataset.
master_lookup = {}
if master_path.exists():
    with master_path.open("r", encoding="utf-8") as f:
        import csv

        reader = csv.DictReader(f)
        for row in reader:
            mid = clean_mandi_id(row.get("mandi_id"))
            district = clean_district(row.get("district"))
            if mid:
                if mid not in master_lookup:
                    master_lookup[mid] = district
                elif not master_lookup[mid] and district:
                    master_lookup[mid] = district

# Clean each record in place before saving the output back to the JSON file.
for record in records:
    record["date"] = parse_date(record.get("date"))
    record["mandi_id"] = clean_mandi_id(record.get("mandi_id"))

    district = record.get("district")
    if district is not None and str(district).strip() not in {"", "nan", "None", "null"}:
        record["district"] = clean_district(district)
    else:
        # Fill missing district values using the master mandi reference when available.
        record["district"] = master_lookup.get(record.get("mandi_id"), "")

    record["crop_name"] = clean_crop(record.get("crop_name"))
    for field in ["min_price", "max_price", "modal_price", "msp"]:
        value = record.get(field)
        record[field] = parse_numeric(value, price_mode=True)

# Write the cleaned dataset back to disk with consistent formatting.
with json_path.open("w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)
    f.write("\n")

# Export the cleaned price dataset to CSV for downstream analysis and dashboards.
price_columns = [
    "record_id",
    "date",
    "mandi_id",
    "district",
    "crop_name",
    "min_price",
    "max_price",
    "modal_price",
    "msp",
]
csv_path = root / "cleaned_price_and_msp.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=price_columns)
    writer.writeheader()
    for record in records:
        row = {field: record.get(field) for field in price_columns}
        for price_field in ["min_price", "max_price", "modal_price", "msp"]:
            value = row.get(price_field)
            if value is not None:
                row[price_field] = round(float(value), 2)
        writer.writerow(row)

# Summary statistics for quick validation after cleaning.
clean_count = sum(1 for x in records if x.get("crop_name") and x.get("mandi_id"))
print(f"Cleaned {len(records)} records.")
print(f"Valid crop+mandi rows: {clean_count}")
print(f"CSV exported to: {csv_path}")
print("Sample cleaned record:")
print(json.dumps(records[0], ensure_ascii=False, indent=2))
