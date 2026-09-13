import re
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(r"c:\Users\Manya\Downloads\track3_agritech_dataset_files")
source_path = root / "track3_weather_sensors.xlsx"
out_path = root / "cleaned_weather_sensors.csv"

# Load raw sensor data from Excel
raw_df = pd.read_excel(source_path, sheet_name="sensor_logs")
df = raw_df.drop_duplicates().copy().reset_index(drop=True)

# Standardize ID
if "sensor_id" in df.columns:
    df["sensor_id"] = df["sensor_id"].astype(str).str.strip().str.upper()
    df["is_sensor_unknown"] = df["sensor_id"] == "UNKNOWN"

# Time parsing and timezone normalization to IST

def parse_ts(value):
    if pd.isna(value):
        return pd.NaT, None
    s = str(value).strip()
    patterns = [
        (r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(IST|UTC)$", "%Y-%m-%d %H:%M:%S"),
        (r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", "%Y-%m-%d %H:%M:%S"),
        (r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", "%Y-%m-%dT%H:%M:%S"),
        (r"^\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}$", "%d/%m/%Y %H:%M"),
        (r"^\d{1,2}/\d{1,2}/\d{4}$", "%d/%m/%Y"),
        (r"^\d{1,2}-\d{1,2}-\d{4} \d{1,2}:\d{2} (AM|PM)$", "%m-%d-%Y %I:%M %p"),
        (r"^\d{1,2}-[A-Za-z]{3}-\d{4} \d{2}:\d{2}:\d{2}$", "%d-%b-%Y %H:%M:%S"),
    ]
    for pattern, fmt in patterns:
        m = re.match(pattern, s)
        if not m:
            continue

        if pattern.startswith(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(IST|UTC)$"):
            return pd.to_datetime(m.group(1), format=fmt), m.group(2)

        return pd.to_datetime(m.group(0), format=fmt), None
    return pd.NaT, None

parsed = df["timestamp"].apply(parse_ts)
df["timestamp_local"] = parsed.apply(lambda x: x[0])
df["timestamp_tz"] = parsed.apply(lambda x: x[1])

tz_offset = df["timestamp_tz"].map({
    "UTC": pd.Timedelta(hours=5, minutes=30),
    "IST": pd.Timedelta(0),
}).fillna(pd.Timedelta(0))

df["timestamp"] = df["timestamp_local"] + tz_offset
df["timestamp_tz"] = df["timestamp_tz"].fillna("unspecified")
df["is_timestamp_missing"] = df["timestamp"].isna()

# Temperature cleaning + Celsius conversion
if "temperature" in df.columns:
    raw_temp_str = df["temperature"].astype(str).str.strip()
    extracted = raw_temp_str.str.extract(r"([-]?\d+(?:\.\d+)?)\s*([^A-Za-z0-9]*)\s*([A-Za-z]*)$")
    value_part = pd.to_numeric(extracted[0], errors="coerce")
    unit_text = extracted[2].fillna(extracted[1]).fillna("")
    unit_col_raw = df["temp_unit"].astype(str).str.strip().replace("nan", "") if "temp_unit" in df.columns else ""
    active_unit_raw = unit_text.where(unit_text != "", unit_col_raw)

    def normalize_temp_unit(raw):
        letters = re.sub(r"[^A-Za-z]", "", str(raw)).lower()
        if not letters:
            return np.nan
        if letters.startswith("c"):
            return "Celsius"
        if letters.startswith("f"):
            return "Fahrenheit"
        return np.nan

    active_unit = active_unit_raw.apply(normalize_temp_unit)
    df["reported_temperature"] = value_part
    df["reported_temperature_unit"] = active_unit
    df["temperature_c"] = np.round(np.where(active_unit == "Fahrenheit", (value_part - 32) * 5 / 9, value_part), 2)

# Rainfall cleaning + mm conversion
if "rainfall" in df.columns:
    rainfall_numeric = pd.to_numeric(df["rainfall"], errors="coerce")
    rain_unit_map = {
        "mm": "Millimeter",
        "millimeter": "Millimeter",
        "millimeters": "Millimeter",
        "in": "Inch",
        "inch": "Inch",
        "inches": "Inch",
        '"': "Inch",
    }
    rain_unit_raw = df["rain_unit"].astype(str).str.strip().str.lower() if "rain_unit" in df.columns else pd.Series([""] * len(df))
    reported_rain_unit = rain_unit_raw.map(rain_unit_map).fillna(np.nan)
    df["is_rainfall_negative_flag"] = (df["rainfall"] < 0).fillna(False)
    rainfall_abs = rainfall_numeric.abs()
    df["reported_rainfall"] = rainfall_abs
    df["reported_rainfall_unit"] = reported_rain_unit
    df["rainfall_mm"] = np.round(np.where(reported_rain_unit == "Inch", rainfall_abs * 25.4, rainfall_abs), 2)

# Humidity cleaning
if "humidity_percent" in df.columns:
    df["humidity_percent"] = pd.to_numeric(df["humidity_percent"], errors="coerce")

# Final validation and export
final_cols = [
    "sensor_id",
    "is_sensor_unknown",
    "timestamp",
    "timestamp_tz",
    "is_timestamp_missing",
    "reported_temperature",
    "reported_temperature_unit",
    "temperature_c",
    "reported_rainfall",
    "reported_rainfall_unit",
    "is_rainfall_negative_flag",
    "rainfall_mm",
    "humidity_percent",
]
final_df = df[final_cols].copy()

assert final_df["sensor_id"].notna().all(), "Missing sensor_id!"
assert final_df["sensor_id"].str.match(r"^(SEN\d{3}|UNKNOWN)$").all(), "Bad sensor IDs!"
assert final_df["temperature_c"].notna().all(), "Unparsed temperatures!"
assert final_df["reported_temperature_unit"].dropna().isin(["Celsius", "Fahrenheit"]).all(), "Bad temp units!"
assert final_df["reported_rainfall_unit"].dropna().isin(["Millimeter", "Inch"]).all(), "Bad rainfall units!"
assert (final_df["rainfall_mm"].dropna() >= 0).all(), "Negative rainfall_mm!"
assert ((final_df["humidity_percent"].dropna() >= 0) & (final_df["humidity_percent"].dropna() <= 100)).all(), "Humidity out of range!"

final_df.to_csv(out_path, index=False, encoding="utf-8")
print(f"rows: {len(final_df)}")
print(f"output: {out_path}")
print(final_df.head().to_string())
