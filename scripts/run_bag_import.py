#!/usr/bin/env python3
"""
Import BAG Indicators (Sprint 5C)
--------------------------------
Fresh copy to avoid file corruption/encoding issues.
"""

import os
import sys
import json
import logging
import uuid
from datetime import datetime
import numpy as np
import pandas as pd
import geopandas as gpd
import psycopg2
from psycopg2.extras import execute_values
import configparser
from sqlalchemy import create_engine, text

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
INDICATOR_MAPPING = {
    'woonfunctie': {'uuid': 'b1011f4c-30b1-4088-bcf6-a67893d92c5f', 'name': 'Woonfunctie', 'unit': 'aantal'},
    'winkelfunctie': {'uuid': '49d5687e-c062-40b5-84b9-7e4557b6cee0', 'name': 'Winkelfunctie', 'unit': 'aantal'},
    'kantoorfunctie': {'uuid': '0212e8f8-053d-4287-b924-7bdc20c53bb2', 'name': 'Kantoorfunctie', 'unit': 'aantal'},
    'industriefunctie': {'uuid': '28a7a580-dc3c-4105-9fb3-d9ef47792429', 'name': 'Industriefunctie', 'unit': 'aantal'},
    'onderwijsfunctie': {'uuid': '93048a96-d3cd-4d99-83b5-2b950e8d78a2', 'name': 'Onderwijsfunctie', 'unit': 'aantal'},
    'bijeenkomstfunctie': {'uuid': '5d7ad356-aac8-4815-8da7-97dff60c7873', 'name': 'Bijeenkomstfunctie', 'unit': 'aantal'},
    'gezondheidszorgfunctie': {'uuid': '3baca929-ccc3-48aa-b966-e6877d01cbe7', 'name': 'Gezondheidszorgfunctie', 'unit': 'aantal'},
    'logiesfunctie': {'uuid': 'a990c073-78e3-4490-a26e-1fa8ca6988f9', 'name': 'Logiesfunctie', 'unit': 'aantal'},
    'sportfunctie': {'uuid': 'e2f618ca-0726-4c1f-8442-c1150578622e', 'name': 'Sportfunctie', 'unit': 'aantal'},
    'celfunctie': {'uuid': '29cfacae-021e-4fe5-819b-e9eb655837ae', 'name': 'Celfunctie', 'unit': 'aantal'},
    'overige_gebruiksfunctie': {'uuid': '25405460-907c-4e63-acc4-4f9c949f7cac', 'name': 'Overige gebruiksfunctie', 'unit': 'aantal'},
    
    'gemiddelde_woonoppervlakte': {'uuid': '8841da36-4767-4277-baae-5007de183c5e', 'name': 'Gemiddelde Woonoppervlakte (BAG)', 'unit': 'm2'},
    'diversiteit_functies': {'uuid': None, 'name': 'Diversiteit Functies (Simpson Index)', 'unit': 'index'},
    'aantal_huishoudens_bag': {'uuid': '76465492-3532-47ef-968b-c9a941543886', 'name': 'Huishoudens (BAG woonfunctie)', 'unit': 'aantal'}
}

PERCENTAGE_MAPPINGS = {
    'woonfunctie': 'Percentage Woonfunctie (BAG)',
    'winkelfunctie': 'Percentage Winkelfunctie (BAG)',
    'kantoorfunctie': 'Percentage Kantoorfunctie (BAG)',
    'industriefunctie': 'Percentage Industriefunctie (BAG)',
    'overige_gebruiksfunctie': 'Percentage Overige Functies (BAG)'
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'bag_frl')
VBO_FILE = os.path.join(DATA_DIR, 'cleaned_bag_data_verblijfsobject.gpkg')

def get_db_connection():
    config_path = os.path.join(BASE_DIR, 'config.ini')
    if os.path.exists(config_path):
        config = configparser.ConfigParser()
        config.read(config_path)
        db_config = config['DATABASE']
        conn_str = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    else:
        conn_str = "postgresql://omnitwin_user:admin_omnitwin2026@localhost:5432/omnitwin_db"
    return create_engine(conn_str)

def get_or_create_indicator(conn, naam, eenheid, uuid_fixed=None, bron="Kadaster BAG", score_type="-=-"):
    # Check if exists by UUID (if fixed) or Name
    query_uuid = text("SELECT uuid FROM indicatoren WHERE uuid = :uuid")
    query_name = text("SELECT uuid FROM indicatoren WHERE naam = :naam")
    
    uuid_val = None
    
    with conn.begin() as trans:
        if uuid_fixed:
            # Check if fixed UUID exists
            res = conn.execute(query_uuid, {"uuid": uuid_fixed}).fetchone()
            if res:
                return uuid_fixed
            else:
                # Create with fixed UUID
                logger.info(f"Creating new indicator (fixed UUID): {naam} ({uuid_fixed})")
                insert_query = text("""
                    INSERT INTO indicatoren (uuid, naam, eenheid, bron, score_type, status, begingeldigheid)
                    VALUES (:uuid, :naam, :eenheid, :bron, :score_type, 'actief', NOW())
                """)
                conn.execute(insert_query, {"uuid": uuid_fixed, "naam": naam, "eenheid": eenheid, "bron": bron, "score_type": score_type})
                return uuid_fixed

        # If no fixed UUID, look up by name
        res = conn.execute(query_name, {"naam": naam}).fetchone()
        if res:
            uuid_val = res[0]
        else:
            code_guess = naam.lower().replace(' ', '_').replace('(', '').replace(')', '')
            query_code = text("SELECT uuid FROM indicatoren WHERE code = :code")
            res_code = conn.execute(query_code, {"code": code_guess}).fetchone()
            if res_code:
                 uuid_val = res_code[0]
            else:
                uuid_val = str(uuid.uuid4())
                logger.info(f"Creating new indicator: {naam} ({uuid_val})")
                insert_query = text("""
                    INSERT INTO indicatoren (uuid, naam, eenheid, bron, score_type, status, begingeldigheid)
                    VALUES (:uuid, :naam, :eenheid, :bron, :score_type, 'actief', NOW())
                """)
                conn.execute(insert_query, {"uuid": uuid_val, "naam": naam, "eenheid": eenheid, "bron": bron, "score_type": score_type})
    return uuid_val

def calculate_simpson_index(counts):
    total = sum(counts)
    if total <= 1: return 0.0
    sum_sq_prob = sum([(n/total)**2 for n in counts])
    return 1.0 - sum_sq_prob

def run_import():
    logger.info("Loading BAG VBO data...")
    if not os.path.exists(VBO_FILE):
        logger.error(f"File not found: {VBO_FILE}")
        sys.exit(1)
        
    gdf_vbo = gpd.read_file(VBO_FILE)
    logger.info(f"Loaded {len(gdf_vbo)} VBOs")
    
    gdf_vbo = gdf_vbo[gdf_vbo['status'] == 'Verblijfsobject in gebruik']
    logger.info(f"Active VBOs: {len(gdf_vbo)}")
    
    engine = get_db_connection()
    logger.info("Fetching areas (Buurten) from database...")
    
    sql_areas = text("""
        SELECT id, naam, ST_AsText(geom) as geom_wkt 
        FROM gebieden 
        WHERE gebiedstype_id = (SELECT id FROM gebiedstypes WHERE code = 'CBS_BUURT')
    """)
    try:
        df_areas = pd.read_sql(sql_areas, engine)
        logger.info(f"Loaded {len(df_areas)} areas")
    except Exception as e:
        logger.error(f"Error loading areas: {e}")
        return

    from shapely import wkt
    df_areas['geometry'] = df_areas['geom_wkt'].apply(wkt.loads)
    gdf_areas = gpd.GeoDataFrame(df_areas, geometry='geometry')
    gdf_areas.set_crs(epsg=28992, inplace=True) # DB is RD New
    gdf_areas = gdf_areas.to_crs(epsg=4326)
    
    if gdf_vbo.crs.to_epsg() != 4326:
        logger.info(f"Reprojecting VBOs from {gdf_vbo.crs} to EPSG:4326")
        gdf_vbo = gdf_vbo.to_crs(epsg=4326)
        
    logger.info("Performing spatial join (this may take a while)...")
    logger.info(f"VBO Bounds: {gdf_vbo.total_bounds}")
    logger.info(f"Areas Bounds: {gdf_areas.total_bounds}")
    import time
    start_time = time.time()
    
    # intersects is often faster for points than within
    joined = gpd.sjoin(gdf_vbo, gdf_areas, how='inner', predicate='intersects')
    
    elapsed = time.time() - start_time
    logger.info(f"Spatial join completed in {elapsed:.2f} seconds. Matched {len(joined)} VBOs to areas.")
    
    logger.info("Aggregating data...")
    gebied_data_records = []
    current_year = datetime.now().year
    
    grouped = joined.groupby('id')
    
    ind_uuids = {}
    with engine.connect() as conn:
        for func_key, info in INDICATOR_MAPPING.items():
            ind_uuids[func_key] = get_or_create_indicator(
                conn, info['name'], info['unit'], uuid_fixed=info.get('uuid')
            )
        for func_key, name in PERCENTAGE_MAPPINGS.items():
             ind_uuids[f"{func_key}_pct"] = get_or_create_indicator(
                 conn, name, '%', score_type="-=-"
             )

    for area_id, group in grouped:
        total_vbos = len(group)
        function_counts = {
            'woonfunctie': 0, 'winkelfunctie': 0, 'kantoorfunctie': 0, 
            'industriefunctie': 0, 'onderwijsfunctie': 0, 'bijeenkomstfunctie': 0,
            'gezondheidszorgfunctie': 0, 'logiesfunctie': 0, 'sportfunctie': 0, 
            'celfunctie': 0, 'overige_gebruiksfunctie': 0
        }
        
        for purpose in group['gebruiksdoel']:
            p_lower = str(purpose).lower()
            matched = False
            for k in function_counts.keys():
                if k in p_lower:
                    function_counts[k] += 1
                    matched = True
            if not matched:
                function_counts['overige_gebruiksfunctie'] += 1
                
        diversity = calculate_simpson_index(list(function_counts.values()))
        
        for func_key, count in function_counts.items():
            if func_key in INDICATOR_MAPPING:
                gebied_data_records.append((
                    area_id, ind_uuids[func_key], current_year, int(count), 'BAG', 'current'
                ))
            if func_key in PERCENTAGE_MAPPINGS:
                pct = (count / total_vbos) * 100 if total_vbos > 0 else 0
                gebied_data_records.append((
                    area_id, ind_uuids[f"{func_key}_pct"], current_year, float(round(pct, 1)), 'BAG', 'current'
                ))
            
        woon_vbos = group[group['gebruiksdoel'].str.contains('woonfunctie', case=False, na=False)]
        avg_area = woon_vbos['oppervlakte'].mean() if len(woon_vbos) > 0 else 0
        gebied_data_records.append((
            area_id, ind_uuids['gemiddelde_woonoppervlakte'], current_year, float(round(avg_area, 0)), 'BAG', 'current'
        ))
        
        households = len(woon_vbos)
        gebied_data_records.append((
            area_id, ind_uuids['aantal_huishoudens_bag'], current_year, int(households), 'BAG', 'current'
        ))
        
        gebied_data_records.append((
             area_id, ind_uuids['diversiteit_functies'], current_year, float(round(diversity, 2)), 'BAG', 'current'
        ))

    logger.info(f"Inserting {len(gebied_data_records)} aggregated records into gebied_data...")
    insert_sql = """
        INSERT INTO gebied_data (gebied_id, indicator_uuid, jaar, waarde, bron, scenario_id)
        VALUES %s
        ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id) 
        DO UPDATE SET 
            waarde = EXCLUDED.waarde,
            updated_at = NOW()
    """
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            execute_values(cur, insert_sql, gebied_data_records)
        raw_conn.commit()
    finally:
        raw_conn.close()
    logger.info("Done!")

if __name__ == "__main__":
    run_import()
