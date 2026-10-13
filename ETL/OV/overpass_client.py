#!/usr/bin/env python3
"""
D-OmniTwin ETL — OV Haltes: Overpass Query Module
===================================================
Haalt OV-halte nodes op uit OpenStreetMap via OSMPythonTools / Overpass API.

Gebruik:
    from overpass_client import ophalen_ov_nodes

    nodes = ophalen_ov_nodes("FR")  # Fryslân
    # Retourneert list[dict] met osm_id, naam, lat, lon, ov_type, tags, ...
"""

import logging
import time

from OSMPythonTools.overpass import Overpass

logger = logging.getLogger(__name__)

# ─── Configuratie ────────────────────────────────────────────────────────────

PROVINCIES = {
    "FR": "Fryslân",
    "GR": "Groningen",
    "DR": "Drenthe",
}

# OSMPythonTools voegt zelf [out:json][timeout:N] toe
QUERY_TEMPLATE = """
    area["name"="{naam}"]["admin_level"="4"]["boundary"="administrative"]->.prov;
    (
      node["public_transport"~"platform|station|halt"](area.prov);
      node["highway"="bus_stop"](area.prov);
      node["railway"~"station|halt"](area.prov);
      node["amenity"="ferry_terminal"](area.prov);
    );
    out body;
"""

# Tags die we per node ophalen
TAGS_VAN_BELANG = [
    "name",
    "public_transport",
    "railway",
    "highway",
    "amenity",
    "bus",
    "tram",
    "train",
    "ferry",
    "subway",
    "operator",
    "network",
    "ref",
    "ref:IFOPT",
]


# ─── OV-type bepaling ───────────────────────────────────────────────────────


def bepaal_ov_type(tags: dict) -> str:
    """
    Bepaal OV-type op basis van OSM tags.
    Volgorde: trein > veerboot > tram > metro > bus (default).

    Live data Fryslân (2026-06-03): 85% van nodes is 'platform' zonder
    extra type-tags → bus fallback is correct voor NL.
    """
    rw = tags.get("railway", "")
    hw = tags.get("highway", "")
    amenity = tags.get("amenity", "")

    if rw in ("station", "halt"):
        return "trein"
    if amenity == "ferry_terminal" or tags.get("ferry") == "yes":
        return "veerboot"
    if rw == "tram_stop" or tags.get("tram") == "yes":
        return "tram"
    if tags.get("subway") == "yes":
        return "metro"
    if hw == "bus_stop" or tags.get("bus") == "yes":
        return "bus"
    return "bus"


def bepaal_osm_pt_type(tags: dict) -> str:
    """Bepaal het ruwe OSM public_transport type."""
    pt = tags.get("public_transport", "")
    if pt:
        return pt  # platform, stop_position, station, halt
    if tags.get("highway") == "bus_stop":
        return "bus_stop"
    if tags.get("amenity") == "ferry_terminal":
        return "ferry_terminal"
    if tags.get("railway") in ("station", "halt"):
        return tags["railway"]
    return "onbekend"


# ─── Overpass ophalen ────────────────────────────────────────────────────────


def ophalen_ov_nodes(provincie_code: str, timeout: int = 90) -> list[dict]:
    """
    Haal alle OV-halte nodes op voor een provincie via Overpass API.

    Args:
        provincie_code: "FR", "GR" of "DR"
        timeout: Overpass query timeout in seconden

    Returns:
        List van dicts met:
            osm_id, naam, lat, lon, ov_type, osm_pt_type,
            network, ref, provincie, tags (dict)
    """
    if provincie_code not in PROVINCIES:
        raise ValueError(f"Onbekende provincie: {provincie_code}. Verwacht: {list(PROVINCIES)}")

    naam = PROVINCIES[provincie_code]
    query = QUERY_TEMPLATE.format(naam=naam)

    logger.info(f"Overpass query voor {naam} ({provincie_code})...")
    overpass = Overpass()
    result = overpass.query(query, timeout=timeout)
    elements = result.elements()
    logger.info(f"  → {len(elements)} nodes ontvangen")

    nodes = []
    for el in elements:
        # Verzamel alle relevante tags
        tags = {}
        for tag_key in TAGS_VAN_BELANG:
            val = el.tag(tag_key)
            if val:
                tags[tag_key] = val

        ov_type = bepaal_ov_type(tags)
        osm_pt_type = bepaal_osm_pt_type(tags)

        nodes.append(
            {
                "osm_id": el.id(),
                "naam": tags.get("name"),
                "lat": el.lat(),
                "lon": el.lon(),
                "ov_type": ov_type,
                "osm_pt_type": osm_pt_type,
                "network": tags.get("operator") or tags.get("network"),
                "ref": tags.get("ref") or tags.get("ref:IFOPT"),
                "provincie": provincie_code,
                "tags": tags,
            }
        )

    logger.info(f"  → {len(nodes)} nodes verwerkt voor {naam}")
    return nodes
