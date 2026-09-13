import csv
from pathlib import Path

root = Path(r"c:\Users\Manya\Downloads\track3_agritech_dataset_files")
price_path = root / "cleaned_price_and_msp.csv"
master_path = root / "cleaned_mandi_master.csv"
out_path = root / "price_and_msp_joined_mandi_master.csv"

with price_path.open("r", encoding="utf-8", newline="") as f:
    price_rows = list(csv.DictReader(f))

with master_path.open("r", encoding="utf-8", newline="") as f:
    master_rows = list(csv.DictReader(f))

master_by_id = {}
master_by_district = {}
for row in master_rows:
    mid = (row.get("Mandi_ID") or "").strip()
    district = (row.get("District") or "").strip()
    if mid:
        master_by_id[mid] = row
    if district:
        master_by_district[district.lower()] = row

fieldnames = [
    "record_id", "date", "mandi_id", "district", "crop_name",
    "min_price", "max_price", "modal_price", "msp",
    "Mandi_ID", "Mandi_Name", "District", "State", "Mandi_Type", "Total_Area_Acres"
]

joined_rows = []
for row in price_rows:
    merged = dict(row)
    mid = (row.get("mandi_id") or "").strip()
    district = (row.get("district") or "").strip()
    match = master_by_id.get(mid)
    if not match and district:
        match = master_by_district.get(district.lower())
    if match:
        for k, v in match.items():
            merged[k] = v
    joined_rows.append(merged)

with out_path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in joined_rows:
        write_row = {k: row.get(k, "") for k in fieldnames}
        writer.writerow(write_row)

matched_by_mandi = sum(1 for r in joined_rows if (r.get("Mandi_ID") or "").strip())
matched_by_district = sum(1 for r in joined_rows if not (r.get("Mandi_ID") or "").strip() and (r.get("District") or "").strip())
print(f"Price rows: {len(price_rows)}")
print(f"Joined rows written: {len(joined_rows)}")
print(f"Matched by mandi_id: {matched_by_mandi}")
print(f"Matched by district fallback: {matched_by_district}")
print(f"Output file: {out_path}")
