#!/usr/bin/env python3
"""
GasRadar - Data refresh script for GitHub Actions
Fetches fuel price data from MINETUR Spain API and uploads to Base44 CDN
"""

import json
import urllib.request
import urllib.error
import os
import sys
from datetime import datetime, timezone

MINETUR_URL = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
BASE44_APP_ID = "69bc75f3240b4a7a928e73ed"
BASE44_UPLOAD_URL = f"https://base44.app/api/apps/{BASE44_APP_ID}/files/upload-public"

PRICE_MAP = {
    "PrecioGasoleoA": "gasoilA",
    "PrecioGasolina95E5": "gasolina95",
    "PrecioGasolina98E5": "gasolina98",
    "PrecioGasoleo Premium": "gasoilPremium",
    "PrecioGLP": "glp",
}

def parse_price(val):
    if not val or val == "":
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
            "id": s.get("IDEESS", ""),
            "name": s.get("Rótulo", "").strip(),
            "address": s.get("Dirección", "").strip(),
            "municipality": s.get("Municipio", "").strip(),
            "province": s.get("Provincia", "").strip(),
            "lat": lat,
            "lon": lon,
            "schedule": s.get("Horario", "").strip(),
            "prices": prices,
        })
    print(f"✅ Normalized {len(stations)} stations")
    return stations

def upload_to_base44(data, api_key):
    print("📤 Uploading to Base44 CDN...")
    json_bytes = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="gasdata_normalized.json"\r\n'
        f"Content-Type: application/json\r\n\r\n"
    ).encode("utf-8") + json_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        BASE44_UPLOAD_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    
    cdn_url = result.get("url") or result.get("file_url")
    print(f"✅ Uploaded to CDN: {cdn_url}")
    return cdn_url

def main():
    api_key = os.environ.get("BASE44_API_KEY")
    if not api_key:
        print("❌ BASE44_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    stations_raw = fetch_minetur()
    stations = normalize(stations_raw)

    now = datetime.now(timezone.utc)
    # Format in Madrid time
    from datetime import timedelta
    madrid_offset = timedelta(hours=1)  # CET (adjust for DST if needed)
    madrid_time = now + madrid_offset
    updated_at = madrid_time.strftime("%d/%m/%Y %H:%M")

    output = {
        "updated": updated_at,
        "total": len(stations),
        "stations": stations,
    }

    cdn_url = upload_to_base44(output, api_key)
    print(f"🎉 Done! {len(stations)} stations · Updated: {updated_at}")
    print(f"CDN URL: {cdn_url}")

if __name__ == "__main__":
    main()
