#!/usr/bin/env python3
"""
GasRadar - Data refresh script for GitHub Actions
Fetches fuel price data from MINETUR Spain API and saves to gasdata_output.json
"""

import json
import urllib.request
import urllib.error
import os
import sys
from datetime import datetime, timezone, timedelta

MINETUR_URL = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"

PRICE_MAP = {
    "Precio Gasoleo A":       "gasoilA",
    "Precio Gasolina 95 E5":  "gasolina95",
    "Precio Gasolina 98 E5":  "gasolina98",
    "Precio Gasoleo Premium": "gasoilPremium",
    "Precio Gases licuados del petróleo": "glp",
}

def parse_price(val):
    if not val or str(val).strip() == "":
        return None
    try:
        return round(float(str(val).replace(",", ".")), 4)
    except:
        return None

def parse_coord(val):
    if not val:
        return None
    try:
        return float(str(val).replace(",", "."))
    except:
        return None

def fetch_minetur():
    print("📡 Fetching from MINETUR...")
    req = urllib.request.Request(
        MINETUR_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    stations_raw = raw.get("ListaEESSPrecio", [])
    print(f"✅ Got {len(stations_raw)} stations from MINETUR")
    return stations_raw

def normalize(stations_raw):
    stations = []
    for s in stations_raw:
        lat = parse_coord(s.get("Latitud"))
        lon = parse_coord(s.get("Longitud (WGS84)") or s.get("Longitud"))
        if not lat or not lon:
            continue
        prices = {}
        for src_key, dest_key in PRICE_MAP.items():
            prices[dest_key] = parse_price(s.get(src_key))
        if all(v is None for v in prices.values()):
            continue
        stations.append({
            "id":           s.get("IDEESS", ""),
            "name":         s.get("Rótulo", "").strip(),
            "address":      s.get("Dirección", "").strip(),
            "locality":     s.get("Localidad", "").strip(),
            "municipality": s.get("Municipio", "").strip(),
            "province":     s.get("Provincia", "").strip(),
            "cp":           s.get("C.P.", "").strip(),
            "lat":          lat,
            "lon":          lon,
            "schedule":     s.get("Horario", "").strip(),
            "prices":       prices,
        })
    print(f"✅ Normalized {len(stations)} stations")
    return stations

def main():
    stations_raw = fetch_minetur()
    stations = normalize(stations_raw)

    madrid_time = datetime.now(timezone.utc) + timedelta(hours=1)
    updated_at = madrid_time.strftime("%d/%m/%Y %H:%M")

    output = {
        "updated": updated_at,
        "total": len(stations),
        "stations": stations,
    }

    with open("gasdata_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

    print(f"🎉 Done! {len(stations)} stations · Updated: {updated_at}")
    print(f"📁 Saved to gasdata_output.json")

if __name__ == "__main__":
    main()
