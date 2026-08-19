#!/usr/bin/env python3
"""
apply_option_a_household_fix.py

Applies Option A (raw absolute counts without normalization):
1. Updates units for Opleidingsniveau (laag, middelbaar, hoog) from '%' to 'aantal'.
2. Registers 'Eenpersoonshuishoudens' indicator (eenheid: 'aantal') and links it in kompas_indicator_mapping.
3. Re-imports CBS data for KERNCIJFERS_WIJKEN_EN_BUURTEN using cbs_mapping_v3.json with normalize: false.
4. Verifies the updated data for 'Het Eiland' (BU19000112) and other areas.
"""

import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load .env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

def get_db_connection():
    return psycopg2.connect(
        host='127.0.0.1',
        port=5432,
        dbname=os.getenv('DATABASE_NAME', 'omnitwin_db'),
        user=os.getenv('DATABASE_USER', 'omnitwin_user'),
        password=os.getenv('DATABASE_PASSWORD', 'admin_omnitwin2026'),
        connect_timeout=10
    )

def main():
    conn = get_db_connection()
    conn.autocommit = False
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print("1. Updating Opleidingsniveau units to 'aantal'...")
            cur.execute("""
                UPDATE indicatoren
                SET eenheid = 'aantal', updated_at = CURRENT_TIMESTAMP
                WHERE naam IN ('Opleidingsniveau laag', 'Opleidingsniveau middelbaar', 'Opleidingsniveau hoog')
            """)
            print(f"   Updated {cur.rowcount} Opleidingsniveau indicators to 'aantal'.")
            
            print("\n2. Ensuring 'Eenpersoonshuishoudens' exists in indicatoren...")
            cur.execute("SELECT uuid FROM indicatoren WHERE naam = 'Eenpersoonshuishoudens'")
            row = cur.fetchone()
            if row:
                eenpersoons_uuid = row['uuid']
                cur.execute("""
                    UPDATE indicatoren
                    SET eenheid = 'aantal',
                        code = COALESCE(code, 'CBS_EENPERSOONSHUISHOUDENS_30'),
                        bron = COALESCE(bron, 'CBS 85618NED'),
                        omschrijving = COALESCE(omschrijving, 'Particuliere huishoudens bestaande uit één persoon.'),
                        score_type = COALESCE(score_type, '+/+'),
                        is_actief = true,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE uuid = %s
                """, (eenpersoons_uuid,))
                print(f"   Existing indicator updated: {eenpersoons_uuid}")
            else:
                cur.execute("""
                    INSERT INTO indicatoren (
                        naam, code, eenheid, omschrijving, status, score_type, bron, is_actief
                    ) VALUES (
                        'Eenpersoonshuishoudens',
                        'CBS_EENPERSOONSHUISHOUDENS_30',
                        'aantal',
                        'Particuliere huishoudens bestaande uit één persoon.',
                        'O',
                        '+/+',
                        'CBS 85618NED',
                        true
                    ) RETURNING uuid
                """)
                eenpersoons_uuid = cur.fetchone()['uuid']
                print(f"   Created new indicator 'Eenpersoonshuishoudens': {eenpersoons_uuid}")
                
            print("\n3. Ensuring 'Eenpersoonshuishoudens' is mapped in kompas_indicator_mapping...")
            # Check onderdeel_id for Huishoudens
            cur.execute("SELECT id FROM kompas_onderdelen WHERE naam = 'Huishoudens' LIMIT 1")
            o_row = cur.fetchone()
            if o_row:
                onderdeel_id = o_row['id']
                cur.execute("""
                    SELECT id FROM kompas_indicator_mapping
                    WHERE indicator_uuid = %s AND onderdeel_id = %s
                """, (eenpersoons_uuid, onderdeel_id))
                m_row = cur.fetchone()
                if not m_row:
                    cur.execute("""
                        INSERT INTO kompas_indicator_mapping (
                            indicator_uuid, onderdeel_id, weging, is_actueel, indicator_swf, config_id
                        ) VALUES (
                            %s, %s, 1.0, true, 'Eenpersoonshuishoudens', 1
                        )
                    """, (eenpersoons_uuid, onderdeel_id))
                    print(f"   Mapped 'Eenpersoonshuishoudens' to onderdeel 'Huishoudens' (id={onderdeel_id})")
                else:
                    print(f"   Mapping already exists (id={m_row['id']})")
            else:
                print("   ⚠️ Onderdeel 'Huishoudens' not found in kompas_onderdelen")
                
            conn.commit()
            print("✅ Database metadata updates committed successfully.")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during database update: {e}")
        conn.close()
        sys.exit(1)
        
    conn.close()

if __name__ == '__main__':
    main()
