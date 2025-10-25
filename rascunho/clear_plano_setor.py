import sqlite3
from pathlib import Path
import json

def clear_plano_setor_column():
    """
    This script connects to the SQLite database and clears all entries
    in the 'plano_setor' column of the 'planejamento' table by setting them to NULL.
    """
    try:
        # Construct the path to the database
        pasta_bd = Path(__file__).parent.parent / 'banco_dados'
        db_path = pasta_bd / 'bd_pcp.sqlite'
        print(f"Connecting to database at: {db_path}")

        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Execute the UPDATE command
        print("Executing: UPDATE planejamento SET plano_setor = NULL")
        cursor.execute("UPDATE planejamento SET plano_setor = NULL")
        
        # Commit the changes and get the number of rows affected
        conn.commit()
        rows_affected = cursor.rowcount
        print(f"Successfully cleared 'plano_setor' column for {rows_affected} rows.")

        # Close the connection
        conn.close()

    except sqlite3.Error as e:
        print(f"An SQLite error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    clear_plano_setor_column() 