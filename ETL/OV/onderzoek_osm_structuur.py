"""
Onderzoeksscript: OSM halte-structuur in Fryslân verkennen
Doel: Strategiebepaling voor deduplicatie en OV-type classificatie
Uitvoering: python ETL/OV/onderzoek_osm_structuur.py
"""

import requests
import json
import time
from collections import Counter, defaultdict

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def overpass_query(query: str) -> dict:
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    response = requests.post(OVERPASS_URL, data=f"data={requests.utils.quote(query)}", headers=headers, timeout=90)
    if not response.ok:
        print(f"  HTTP {response.status_code}: {response.text[:200]}")
    response.raise_for_status()
    return response.json()


# ── 1. Leeuwarden station omgeving: exact alle nodes binnen 500m radius ───────
print("=" * 70)
print("STAP 1: Leeuwarden station — alle OV-nodes binnen 500m radius")
print("=" * 70)

q_leeuwarden = """
[out:json][timeout:30];
// Centrum NS station Leeuwarden: 53.1963, 5.7913
node
  (around:500, 53.1963, 5.7913)
  ["public_transport"];
out body;
"""

lw_data = overpass_query(q_leeuwarden)
time.sleep(2)

lw_nodes = lw_data.get("elements", [])
print(f"\nAantal nodes gevonden: {len(lw_nodes)}")
print("\nAlle nodes met tags:")
for node in lw_nodes:
    tags = node.get("tags", {})
    print(f"\n  OSM ID: {node['id']}")
    print(f"  Naam: {tags.get('name', '(geen naam)')}")
    print(f"  public_transport: {tags.get('public_transport', '-')}")
    print(f"  railway: {tags.get('railway', '-')}")
    print(f"  highway: {tags.get('highway', '-')}")
    print(f"  bus: {tags.get('bus', '-')}")
    print(f"  train: {tags.get('train', '-')}")
    print(f"  tram: {tags.get('tram', '-')}")
    print(f"  ferry: {tags.get('ferry', '-')}")
    print(f"  operator: {tags.get('operator', '-')}")
    print(f"  network: {tags.get('network', '-')}")
    print(f"  ref: {tags.get('ref', '-')}")
    print(f"  uic_ref: {tags.get('uic_ref', '-')}")
    print(f"  lat/lon: {node['lat']:.4f}, {node['lon']:.4f}")


# ── 2. Leeuwarden — ook met highway=bus_stop en railway tags ─────────────────
print("\n" + "=" * 70)
print("STAP 2: Leeuwarden — breder: ook highway=bus_stop + railway")
print("=" * 70)

q_lw_breed = """
[out:json][timeout:30];
(
  node(around:500, 53.1963, 5.7913)["highway"="bus_stop"];
  node(around:500, 53.1963, 5.7913)["railway"];
  node(around:500, 53.1963, 5.7913)["public_transport"];
  node(around:500, 53.1963, 5.7913)["amenity"="ferry_terminal"];
);
out body;
"""

lw2_data = overpass_query(q_lw_breed)
time.sleep(2)

lw2_nodes = lw2_data.get("elements", [])
print(f"\nAantal nodes (breed): {len(lw2_nodes)}")

# Samenvatting per tag-combinatie
tag_combos = Counter()
namen = {}
for node in lw2_nodes:
    tags = node.get("tags", {})
    combo = (
        tags.get("public_transport", ""),
        tags.get("railway", ""),
        tags.get("highway", ""),
        tags.get("bus", ""),
        tags.get("train", ""),
    )
    tag_combos[combo] += 1
    naam = tags.get("name", "(geen naam)")
    namen[node["id"]] = naam

print("\nTag-combinaties aanwezig (public_transport, railway, highway, bus, train):")
for combo, count in tag_combos.most_common():
    print(f"  {combo} → {count}x")

print("\nUnieke namen:")
naam_counter = Counter(namen.values())
for naam, count in naam_counter.most_common(20):
    print(f"  '{naam}' → {count}x")


# ── 3. Sample heel Fryslân: tag-verdeling over alle haltes ───────────────────
print("\n" + "=" * 70)
print("STAP 3: Sample heel Fryslân — tag-verdeling alle OV-nodes")
print("=" * 70)
print("(Dit kan 10-20 seconden duren...)")

q_fryslan_sample = """
[out:json][timeout:60];
area["name"="Fryslân"]["admin_level"="4"]["boundary"="administrative"]->.prov;
(
  node["public_transport"](area.prov);
  node["highway"="bus_stop"](area.prov);
  node["railway"="station"](area.prov);
  node["railway"="halt"](area.prov);
  node["amenity"="ferry_terminal"](area.prov);
);
out body;
"""

fr_data = overpass_query(q_fryslan_sample)
time.sleep(2)

fr_nodes = fr_data.get("elements", [])
print(f"\nTotaal nodes Fryslân: {len(fr_nodes)}")

# Analyseer tag-structuur
pt_values = Counter()
railway_values = Counter()
highway_values = Counter()
heeft_naam = 0
heeft_uic = 0
heeft_operator = 0
heeft_ref = 0
naam_freq = Counter()

# Per-naam analyse (voor dubbelen)
naam_nodes = defaultdict(list)  # naam -> lijst van (osm_id, lat, lon, tags)

for node in fr_nodes:
    tags = node.get("tags", {})
    pt = tags.get("public_transport", "")
    rw = tags.get("railway", "")
    hw = tags.get("highway", "")

    if pt:
        pt_values[pt] += 1
    if rw:
        railway_values[rw] += 1
    if hw:
        highway_values[hw] += 1
    if tags.get("name"):
        heeft_naam += 1
        naam = tags["name"]
        naam_freq[naam] += 1
        naam_nodes[naam].append(
            {
                "id": node["id"],
                "lat": node["lat"],
                "lon": node["lon"],
                "pt": pt,
                "railway": rw,
                "highway": hw,
                "operator": tags.get("operator", ""),
                "network": tags.get("network", ""),
                "ref": tags.get("ref", ""),
                "uic_ref": tags.get("uic_ref", ""),
                "bus": tags.get("bus", ""),
                "train": tags.get("train", ""),
                "tram": tags.get("tram", ""),
                "ferry": tags.get("ferry", ""),
            }
        )
    if tags.get("uic_ref"):
        heeft_uic += 1
    if tags.get("operator"):
        heeft_operator += 1
    if tags.get("ref"):
        heeft_ref += 1

print("\n--- public_transport tag waarden ---")
for val, count in pt_values.most_common():
    print(f"  '{val}': {count}")

print("\n--- railway tag waarden ---")
for val, count in railway_values.most_common():
    print(f"  '{val}': {count}")

print("\n--- highway tag waarden ---")
for val, count in highway_values.most_common():
    print(f"  '{val}': {count}")

print(f"\n--- Coverage ---")
print(f"  Heeft naam: {heeft_naam} / {len(fr_nodes)} ({100 * heeft_naam // len(fr_nodes) if fr_nodes else 0}%)")
print(f"  Heeft uic_ref: {heeft_uic} / {len(fr_nodes)}")
print(f"  Heeft operator: {heeft_operator} / {len(fr_nodes)}")
print(f"  Heeft ref: {heeft_ref} / {len(fr_nodes)}")

# Namen die meer dan 1x voorkomen = potentiële duplicaten
duplicaat_namen = {naam: nodes for naam, nodes in naam_nodes.items() if len(nodes) > 1}
print(f"\n--- Namen die >1x voorkomen (potentiële duplicaten): {len(duplicaat_namen)} ---")
print("Top 15 meest voorkomende dubbele namen:")
for naam, nodes in sorted(duplicaat_namen.items(), key=lambda x: -len(x[1]))[:15]:
    print(f"\n  '{naam}' ({len(nodes)}x):")
    for n in nodes[:4]:
        print(
            f"    ID={n['id']} pt={n['pt']} railway={n['railway']} hw={n['highway']} "
            f"bus={n['bus']} train={n['train']} operator={n['operator'][:30]}"
        )


# ── 4. Overpass Attic beschikbaarheid check ───────────────────────────────────
print("\n" + "=" * 70)
print("STAP 4: Overpass Attic — historische data beschikbaar?")
print("=" * 70)

# Test met een kleine attic query (Leeuwarden station, peildatum 2022)
q_attic = """
[out:json][timeout:30][date:"2022-01-01T00:00:00Z"];
node(53.1955, 5.7900, 53.1975, 5.7930)["railway"="station"];
out body;
"""

try:
    attic_data = overpass_query(q_attic)
    attic_nodes = attic_data.get("elements", [])
    print(f"\nAttic query (2022-01-01) werkt! Nodes gevonden: {len(attic_nodes)}")
    for n in attic_nodes:
        tags = n.get("tags", {})
        print(f"  ID={n['id']} naam={tags.get('name', '-')} railway={tags.get('railway', '-')}")
    print("\n✅ Overpass Attic is beschikbaar — historische queries zijn mogelijk")
except Exception as e:
    print(f"\n❌ Attic query mislukt: {e}")

print("\n" + "=" * 70)
print("ONDERZOEK KLAAR")
print("=" * 70)
