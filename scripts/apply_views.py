import sys
import os

# Add the project root to the python path
sys.path.append(os.getcwd())

from sqlalchemy import text
from omnitwin.database import engine

def apply_views():
    sql_file = "data/schema_v4_views.sql"
    print(f"Applying views from {sql_file}...")
    
    with open(sql_file, "r") as f:
        sql_content = f.read()
    
    with engine.connect() as connection:
        # Split by command to ensure proper execution (though execute usually handles it)
        # But for 'DROP VIEW' and 'CREATE VIEW', simple execute of the whole block might work 
        # if the driver supports multiple statements, or we split properly.
        # SQLAlchemy execute can handle multiple statements if supported by driver, but explicitly committing is good.
        
        # NOTE: SQLAlchemy sometimes wraps in a transaction.
        from sqlalchemy.exc import SQLAlchemyError
        try:
            connection.execute(text(sql_content))
            connection.commit()
            print("Successfully applied views!")
        except SQLAlchemyError as e:
            print(f"Error applying views: {e}")
            sys.exit(1)

if __name__ == "__main__":
    apply_views()
