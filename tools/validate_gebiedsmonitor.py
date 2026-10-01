#!/usr/bin/env python3
"""
Validatie Script Gebiedsmonitor Data
=====================================
Dit script voert uitgebreide validatie uit op de Gebiedsmonitor database:
- Database tabel statistieken
- Geo-data visualisaties  
- Relatie overzichten (Primary/Foreign Keys)
- SQL View voorbeelden voor joins
- Genereren van een validatierapport in Markdown

Usage:
    python tools/validate_gebiedsmonitor.py
"""

import os
import json
import configparser
import psycopg2
from psycopg2.extras import RealDictCursor
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# ============================================================================
# DATABASE CONNECTIE
# ============================================================================

def get_db_connection():
    """Maak database connectie op basis van config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    config.read(config_path)
    
    return psycopg2.connect(
        host=config['DATABASE']['host'],
        port=config['DATABASE']['port'],
        dbname=config['DATABASE']['dbname'],
        user=config['DATABASE']['user'],
        password=config['DATABASE']['password']
    )

# ============================================================================
# DATABASE INSPECTIE
# ============================================================================

def get_table_stats(conn):
    """Verzamel statistieken van alle relevante tabellen"""
    stats = {}
    
    tables = [
        'gebiedstypes',
        'gebieden',
        'indicatoren',
        'indicator_gebiedstype_relaties',
        'gebied_data',
        'configuratie_instanties'
    ]
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for table in tables:
            # Aantal records
            cur.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cur.fetchone()['count']
            
            # Kolom info
            cur.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table,))
            columns = cur.fetchall()
            
            stats[table] = {
                'count': count,
                'columns': columns
            }
    
    return stats

def get_foreign_keys(conn):
    """Haal alle foreign key relaties op"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
                tc.table_name as from_table,
                kcu.column_name as from_column,
                ccu.table_name AS to_table,
                ccu.column_name AS to_column,
                rc.update_rule,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            JOIN information_schema.referential_constraints AS rc
                ON rc.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.column_name
        """)
        return cur.fetchall()

def get_indexes(conn):
    """Haal alle indexen op"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
                t.relname as table_name,
                i.relname as index_name,
                a.attname as column_name,
                am.amname as index_type
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_am am ON i.relam = am.oid
            LEFT JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            WHERE t.relkind = 'r'
                AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                AND t.relname IN ('gebiedstypes', 'gebieden', 'indicatoren', 
                                  'indicator_gebiedstype_relaties', 'gebied_data')
            ORDER BY t.relname, i.relname
        """)
        return cur.fetchall()

# ============================================================================
# GEO-DATA ANALYSE
# ============================================================================

def analyze_geodata(conn):
    """Analyseer geo-data uit gebieden tabel"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Gebieden per type
        cur.execute("""
            SELECT 
                gt.naam as gebiedstype,
                COUNT(*) as aantal,
                ST_GeometryType(g.geom) as geom_type,
                COUNT(*) FILTER (WHERE g.geom IS NOT NULL) as met_geometrie,
                COUNT(*) FILTER (WHERE g.geom_centroid IS NOT NULL) as met_centroid
            FROM gebieden g
            JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            GROUP BY gt.naam, ST_GeometryType(g.geom)
            ORDER BY gt.naam
        """)
        gebied_stats = cur.fetchall()
        
        # Bbox per gebiedstype
        cur.execute("""
            SELECT 
                gt.naam as gebiedstype,
                ST_XMin(ST_Extent(g.geom)) as min_x,
                ST_YMin(ST_Extent(g.geom)) as min_y,
                ST_XMax(ST_Extent(g.geom)) as max_x,
                ST_YMax(ST_Extent(g.geom)) as max_y
            FROM gebieden g
            JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            WHERE g.geom IS NOT NULL
            GROUP BY gt.naam
        """)
        bbox_stats = cur.fetchall()
        
        # Sample geometrieën voor visualisatie
        cur.execute("""
            SELECT 
                g.id,
                g.naam,
                gt.naam as gebiedstype,
                ST_AsGeoJSON(g.geom_centroid) as centroid_json
            FROM gebieden g
            JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            WHERE g.geom_centroid IS NOT NULL
            LIMIT 100
        """)
        sample_points = cur.fetchall()
        
    return {
        'gebied_stats': gebied_stats,
        'bbox_stats': bbox_stats,
        'sample_points': sample_points
    }

def analyze_data_coverage(conn):
    """Analyseer data coverage per gebied"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Gebieden met data
        cur.execute("""
            SELECT 
                gt.naam as gebiedstype,
                COUNT(DISTINCT g.id) as totaal_gebieden,
                COUNT(DISTINCT gd.gebied_id) as gebieden_met_data,
                ROUND(100.0 * COUNT(DISTINCT gd.gebied_id) / NULLIF(COUNT(DISTINCT g.id), 0), 2) as coverage_percentage
            FROM gebiedstypes gt
            LEFT JOIN gebieden g ON gt.id = g.gebiedstype_id
            LEFT JOIN gebied_data gd ON g.id = gd.gebied_id
            GROUP BY gt.naam
            ORDER BY gt.naam
        """)
        coverage = cur.fetchall()
        
        # Indicatoren per gebiedstype
        cur.execute("""
            SELECT 
                gt.naam as gebiedstype,
                COUNT(DISTINCT igr.indicator_uuid) as aantal_indicatoren,
                COUNT(DISTINCT igr.indicator_uuid) FILTER (WHERE igr.verplicht = true) as aantal_verplicht
            FROM gebiedstypes gt
            LEFT JOIN indicator_gebiedstype_relaties igr ON gt.id = igr.gebiedstype_id
            GROUP BY gt.naam
            ORDER BY gt.naam
        """)
        indicator_stats = cur.fetchall()
        
    return {
        'coverage': coverage,
        'indicator_stats': indicator_stats
    }

# ============================================================================
# VISUALISATIES
# ============================================================================

def create_visualizations(geodata, datacoverage, output_dir):
    """Maak visualisaties van de data"""
    vis_files = {}
    
    # 1. Centroid map
    if geodata['sample_points']:
        fig, ax = plt.subplots(figsize=(12, 10))
        
        colors = {'CBS Buurten': 'blue', 'Welstandsgebieden': 'red'}
        
        for point in geodata['sample_points']:
            geojson = json.loads(point['centroid_json'])
            coords = geojson['coordinates']
            color = colors.get(point['gebiedstype'], 'gray')
            ax.scatter(coords[0], coords[1], c=color, alpha=0.6, s=30, 
                      label=point['gebiedstype'])
        
        # Remove duplicate labels
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='upper right')
        
        ax.set_xlabel('X (RD New)', fontsize=12)
        ax.set_ylabel('Y (RD New)', fontsize=12)
        ax.set_title('Gebieden Centroïden (Sample 100)', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        vis_path = os.path.join(output_dir, 'geodata_centroids.png')
        plt.savefig(vis_path, dpi=150, bbox_inches='tight')
        plt.close()
        vis_files['centroids'] = vis_path
    
    # 2. Data coverage bar chart
    if datacoverage['coverage']:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        gebiedstypes = [row['gebiedstype'] for row in datacoverage['coverage']]
        totaal = [row['totaal_gebieden'] for row in datacoverage['coverage']]
        met_data = [row['gebieden_met_data'] for row in datacoverage['coverage']]
        
        x = np.arange(len(gebiedstypes))
        width = 0.35
        
        ax.bar(x - width/2, totaal, width, label='Totaal Gebieden', color='lightblue')
        ax.bar(x + width/2, met_data, width, label='Met Data', color='darkblue')
        
        ax.set_xlabel('Gebiedstype', fontsize=12)
        ax.set_ylabel('Aantal', fontsize=12)
        ax.set_title('Data Coverage per Gebiedstype', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(gebiedstypes, rotation=15, ha='right')
        ax.legend()
        ax.grid(True, axis='y', alpha=0.3)
        
        # Add percentage labels
        for i, (tot, met) in enumerate(zip(totaal, met_data)):
            if tot > 0:
                pct = 100.0 * met / tot
                ax.text(i, max(tot, met) + 10, f'{pct:.1f}%', 
                       ha='center', va='bottom', fontweight='bold')
        
        vis_path = os.path.join(output_dir, 'data_coverage.png')
        plt.savefig(vis_path, dpi=150, bbox_inches='tight')
        plt.close()
        vis_files['coverage'] = vis_path
    
    # 3. Indicatoren per gebiedstype
    if datacoverage['indicator_stats']:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        gebiedstypes = [row['gebiedstype'] for row in datacoverage['indicator_stats']]
        totaal_ind = [row['aantal_indicatoren'] for row in datacoverage['indicator_stats']]
        verplicht = [row['aantal_verplicht'] for row in datacoverage['indicator_stats']]
        
        x = np.arange(len(gebiedstypes))
        width = 0.35
        
        ax.bar(x - width/2, totaal_ind, width, label='Totaal Indicatoren', color='lightgreen')
        ax.bar(x + width/2, verplicht, width, label='Verplicht', color='darkgreen')
        
        ax.set_xlabel('Gebiedstype', fontsize=12)
        ax.set_ylabel('Aantal Indicatoren', fontsize=12)
        ax.set_title('Indicatoren per Gebiedstype', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(gebiedstypes, rotation=15, ha='right')
        ax.legend()
        ax.grid(True, axis='y', alpha=0.3)
        
        vis_path = os.path.join(output_dir, 'indicatoren_stats.png')
        plt.savefig(vis_path, dpi=150, bbox_inches='tight')
        plt.close()
        vis_files['indicators'] = vis_path
    
    return vis_files

# ============================================================================
# RAPPORT GENERATIE
# ============================================================================

def generate_markdown_report(stats, fkeys, indexes, geodata, datacoverage, vis_files, output_path):
    """Genereer Markdown validatierapport"""
    
    lines = []
    lines.append("# Gebiedsmonitor Database Validatie Rapport")
    lines.append(f"*Gegenereerd: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # ======== TABEL STATISTIEKEN ========
    lines.append("## 📊 Database Tabel Statistieken")
    lines.append("")
    
    for table, data in stats.items():
        lines.append(f"### {table}")
        lines.append(f"- **Aantal records:** {data['count']:,}")
        lines.append(f"- **Aantal kolommen:** {len(data['columns'])}")
        lines.append("")
        
        # Kolom details
        lines.append("| Kolom | Type | Nullable |")
        lines.append("|-------|------|----------|")
        for col in data['columns']:
            nullable = "✅" if col['is_nullable'] == 'YES' else "❌"
            lines.append(f"| `{col['column_name']}` | {col['data_type']} | {nullable} |")
        lines.append("")
    
    # ======== GEO-DATA ANALYSE ========
    lines.append("---")
    lines.append("")
    lines.append("## 🗺️ Geo-Data Analyse")
    lines.append("")
    
    lines.append("### Gebieden per Type")
    lines.append("")
    lines.append("| Gebiedstype | Aantal | Geometrie Type | Met Geometrie | Met Centroïd |")
    lines.append("|-------------|--------|----------------|---------------|--------------|")
    
    for row in geodata['gebied_stats']:
        lines.append(f"| {row['gebiedstype']} | {row['aantal']} | {row['geom_type']} | "
                    f"{row['met_geometrie']} | {row['met_centroid']} |")
    lines.append("")
    
    lines.append("### Bounding Boxes (RD New - EPSG:28992)")
    lines.append("")
    lines.append("| Gebiedstype | Min X | Min Y | Max X | Max Y |")
    lines.append("|-------------|-------|-------|-------|-------|")
    
    for row in geodata['bbox_stats']:
        lines.append(f"| {row['gebiedstype']} | {row['min_x']:.0f} | {row['min_y']:.0f} | "
                    f"{row['max_x']:.0f} | {row['max_y']:.0f} |")
    lines.append("")
    
    # Visualisatie embed
    if 'centroids' in vis_files:
        lines.append("### Centroïden Visualisatie")
        lines.append("")
        lines.append(f"![Gebieden Centroïden]({vis_files['centroids']})")
        lines.append("")
    
    # ======== DATA COVERAGE ========
    lines.append("---")
    lines.append("")
    lines.append("## 📈 Data Coverage Analyse")
    lines.append("")
    
    lines.append("### Gebieden met Data")
    lines.append("")
    lines.append("| Gebiedstype | Totaal Gebieden | Gebieden met Data | Coverage % |")
    lines.append("|-------------|-----------------|-------------------|------------|")
    
    for row in datacoverage['coverage']:
        pct = row['coverage_percentage'] if row['coverage_percentage'] else 0
        lines.append(f"| {row['gebiedstype']} | {row['totaal_gebieden']} | "
                    f"{row['gebieden_met_data']} | {pct}% |")
    lines.append("")
    
    if 'coverage' in vis_files:
        lines.append("### Coverage Visualisatie")
        lines.append("")
        lines.append(f"![Data Coverage]({vis_files['coverage']})")
        lines.append("")
    
    lines.append("### Indicatoren per Gebiedstype")
    lines.append("")
    lines.append("| Gebiedstype | Totaal Indicatoren | Verplichte Indicatoren |")
    lines.append("|-------------|-------------------|------------------------|")
    
    for row in datacoverage['indicator_stats']:
        lines.append(f"| {row['gebiedstype']} | {row['aantal_indicatoren']} | "
                    f"{row['aantal_verplicht']} |")
    lines.append("")
    
    if 'indicators' in vis_files:
        lines.append("### Indicatoren Visualisatie")
        lines.append("")
        lines.append(f"![Indicatoren Stats]({vis_files['indicators']})")
        lines.append("")
    
    # ======== RELATIES ========
    lines.append("---")
    lines.append("")
    lines.append("## 🔗 Database Relaties (Foreign Keys)")
    lines.append("")
    
    lines.append("| Van Tabel | Van Kolom | Naar Tabel | Naar Kolom | On Delete | On Update |")
    lines.append("|-----------|-----------|------------|------------|-----------|-----------|")
    
    for fk in fkeys:
        lines.append(f"| `{fk['from_table']}` | `{fk['from_column']}` | "
                    f"`{fk['to_table']}` | `{fk['to_column']}` | "
                    f"{fk['delete_rule']} | {fk['update_rule']} |")
    lines.append("")
    
    # ======== INDEXES ========
    lines.append("---")
    lines.append("")
    lines.append("## 🚀 Database Indexen")
    lines.append("")
    
    # Groepeer indexen per tabel
    indexes_by_table = {}
    for idx in indexes:
        table = idx['table_name']
        if table not in indexes_by_table:
            indexes_by_table[table] = []
        indexes_by_table[table].append(idx)
    
    for table, table_indexes in sorted(indexes_by_table.items()):
        lines.append(f"### {table}")
        lines.append("")
        lines.append("| Index Naam | Kolom | Type |")
        lines.append("|------------|-------|------|")
        for idx in table_indexes:
            col = idx['column_name'] if idx['column_name'] else '(multi-column)'
            lines.append(f"| `{idx['index_name']}` | `{col}` | {idx['index_type']} |")
        lines.append("")
    
    # ======== SQL VIEW VOORBEELDEN ========
    lines.append("---")
    lines.append("")
    lines.append("## 💡 SQL View Voorbeelden (Joins)")
    lines.append("")
    
    lines.append("### View 1: Gebieden met Type Info")
    lines.append("```sql")
    lines.append("""CREATE OR REPLACE VIEW v_gebieden_volledig AS
SELECT 
    g.id,
    g.naam as gebied_naam,
    gt.naam as gebiedstype_naam,
    gt.code as gebiedstype_code,
    g.geom,
    g.geom_centroid,
    g.metadata,
    g.actief,
    g.created_at
FROM gebieden g
INNER JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
WHERE g.actief = true;""")
    lines.append("```")
    lines.append("")
    
    lines.append("### View 2: Gebied Data met Indicator Details")
    lines.append("```sql")
    lines.append("""CREATE OR REPLACE VIEW v_gebied_data_volledig AS
SELECT 
    gd.id as meting_id,
    g.id as gebied_id,
    g.naam as gebied_naam,
    gt.naam as gebiedstype_naam,
    i.code as indicator_code,
    i.naam as indicator_naam,
    i.eenheid,
    gd.waarde,
    gd.jaar,
    gd.datum,
    gd.bron,
    gd.kwaliteit
FROM gebied_data gd
INNER JOIN gebieden g ON gd.gebied_id = g.id
INNER JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
INNER JOIN indicatoren i ON gd.indicator_uuid = i.uuid
WHERE i.status = 'O';  -- Alleen operationele indicatoren""")
    lines.append("```")
    lines.append("")
    
    lines.append("### View 3: Data Coverage per Gebied")
    lines.append("```sql")
    lines.append("""CREATE OR REPLACE VIEW v_gebied_data_coverage AS
SELECT 
    g.id as gebied_id,
    g.naam as gebied_naam,
    gt.naam as gebiedstype_naam,
    COUNT(DISTINCT gd.indicator_uuid) as aantal_indicatoren,
    COUNT(gd.id) as aantal_metingen,
    MIN(gd.jaar) as oudste_jaar,
    MAX(gd.jaar) as nieuwste_jaar,
    STRING_AGG(DISTINCT i.naam, ', ' ORDER BY i.naam) as indicator_lijst
FROM gebieden g
INNER JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
LEFT JOIN gebied_data gd ON g.id = gd.gebied_id
LEFT JOIN indicatoren i ON gd.indicator_uuid = i.uuid
GROUP BY g.id, g.naam, gt.naam;""")
    lines.append("```")
    lines.append("")
    
    lines.append("### View 4: Indicatoren met Gebiedstype Relaties")
    lines.append("```sql")
    lines.append("""CREATE OR REPLACE VIEW v_indicator_gebiedstype_mapping AS
SELECT 
    i.uuid as indicator_uuid,
    i.code as indicator_code,
    i.naam as indicator_naam,
    gt.id as gebiedstype_id,
    gt.naam as gebiedstype_naam,
    gt.code as gebiedstype_code,
    igr.verplicht,
    igr.display_volgorde
FROM indicatoren i
INNER JOIN indicator_gebiedstype_relaties igr ON i.uuid = igr.indicator_uuid
INNER JOIN gebiedstypes gt ON igr.gebiedstype_id = gt.id
WHERE i.status = 'O'
ORDER BY gt.naam, igr.display_volgorde;""")
    lines.append("```")
    lines.append("")
    
    # ======== CONCLUSIES ========
    lines.append("---")
    lines.append("")
    lines.append("## ✅ Conclusies & Aanbevelingen")
    lines.append("")
    
    total_gebieden = sum(s['count'] for t, s in stats.items() if t == 'gebieden')
    total_metingen = sum(s['count'] for t, s in stats.items() if t == 'gebied_data')
    total_indicatoren = sum(s['count'] for t, s in stats.items() if t == 'indicatoren')
    
    lines.append(f"### Samenvatting")
    lines.append(f"- **Totaal gebieden:** {total_gebieden:,}")
    lines.append(f"- **Totaal indicatoren:** {total_indicatoren:,}")
    lines.append(f"- **Totaal metingen:** {total_metingen:,}")
    lines.append(f"- **Foreign Keys:** {len(fkeys)}")
    lines.append(f"- **Indexen:** {len(indexes)}")
    lines.append("")
    
    lines.append("### Checks")
    lines.append("")
    
    # Check 1: Alle gebieden hebben geometrie?
    has_geom = all(row['met_geometrie'] == row['aantal'] for row in geodata['gebied_stats'])
    check_icon = "✅" if has_geom else "⚠️"
    lines.append(f"{check_icon} **Geometrie completeness:** {'Alle gebieden hebben geometrie' if has_geom else 'Sommige gebieden missen geometrie'}")
    lines.append("")
    
    # Check 2: Data coverage
    avg_coverage = np.mean([row['coverage_percentage'] or 0 for row in datacoverage['coverage']])
    check_icon = "✅" if avg_coverage > 50 else "⚠️"
    lines.append(f"{check_icon} **Data coverage:** {avg_coverage:.1f}% gemiddeld")
    lines.append("")
    
    # Check 3: Foreign keys aanwezig
    expected_fks = ['gebieden->gebiedstypes', 'gebied_data->gebieden', 'gebied_data->indicatoren']
    check_icon = "✅" if len(fkeys) >= len(expected_fks) else "⚠️"
    lines.append(f"{check_icon} **Referential integrity:** {len(fkeys)} foreign keys gedefinieerd")
    lines.append("")
    
    lines.append("### Aanbevelingen")
    lines.append("")
    lines.append("1. **API Development:** De database structuur is klaar voor API endpoints")
    lines.append("2. **Views implementeren:** Gebruik bovenstaande views voor efficiënte queries")
    lines.append("3. **Performance monitoring:** Monitor query performance op `gebied_data` tabel")
    lines.append("4. **Data validatie:** Controleer outliers in meetwaarden")
    lines.append("5. **Documentatie:** Update API docs met schema details")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append(f"*Rapport gegenereerd door `validate_gebiedsmonitor.py`*")
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return output_path

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("🚀 Start Gebiedsmonitor Validatie")
    print("=" * 70)
    
    # Output directory
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'validatie')
    os.makedirs(output_dir, exist_ok=True)
    
    # Database connectie
    conn = get_db_connection()
    print("✅ Database verbinding gemaakt")
    
    # 1. Tabel statistieken
    print("\n📊 Verzamelen tabel statistieken...")
    stats = get_table_stats(conn)
    for table, data in stats.items():
        print(f"   - {table}: {data['count']:,} records")
    
    # 2. Foreign keys
    print("\n🔗 Analyseren foreign keys...")
    fkeys = get_foreign_keys(conn)
    print(f"   - {len(fkeys)} foreign keys gevonden")
    
    # 3. Indexes
    print("\n🚀 Analyseren indexen...")
    indexes = get_indexes(conn)
    print(f"   - {len(indexes)} indexen gevonden")
    
    # 4. Geo-data analyse
    print("\n🗺️  Analyseren geo-data...")
    geodata = analyze_geodata(conn)
    print(f"   - {len(geodata['gebied_stats'])} gebiedstype(n)")
    print(f"   - {len(geodata['sample_points'])} sample punten")
    
    # 5. Data coverage
    print("\n📈 Analyseren data coverage...")
    datacoverage = analyze_data_coverage(conn)
    
    # 6. Visualisaties
    print("\n🎨 Genereren visualisaties...")
    vis_files = create_visualizations(geodata, datacoverage, output_dir)
    for name, path in vis_files.items():
        print(f"   - {name}: {os.path.basename(path)}")
    
    # 7. Rapport genereren
    print("\n📝 Genereren Markdown rapport...")
    report_path = os.path.join(output_dir, f'validatierapport_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md')
    generate_markdown_report(stats, fkeys, indexes, geodata, datacoverage, vis_files, report_path)
    print(f"   ✅ Rapport opgeslagen: {report_path}")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("🎉 Validatie voltooid!")
    print(f"\n📄 Rapport: {report_path}")
    print(f"📁 Output directory: {output_dir}")
    print("=" * 70)

if __name__ == "__main__":
    main()
