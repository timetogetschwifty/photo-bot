"""
Export database tables to CSV for analysis in Excel/Google Sheets.
Usage: python reports/export_csv.py [table_name]
"""

import sys
import csv
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db


def export_table_to_csv(table_name: str, output_dir: str = "exports"):
    """Export a database table to CSV."""
    Path(output_dir).mkdir(exist_ok=True)

    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        # Get all rows
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        if not rows:
            print(f"Table {table_name} is empty.")
            conn.close()
            return

        # Get column names
        columns = [description[0] for description in cursor.description]

        # Write to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{output_dir}/{table_name}_{timestamp}.csv"

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

        print(f"✅ Exported {len(rows)} rows to {filename}")
    except Exception as e:
        print(f"❌ Failed to export {table_name}: {e}")
    finally:
        conn.close()


def export_all():
    """Export all tables."""
    tables = ['users', 'generations', 'purchases', 'promo_codes', 'promo_redemptions', 'notification_log']
    for table in tables:
        export_table_to_csv(table)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        table = sys.argv[1]
        export_table_to_csv(table)
    else:
        print("Exporting all tables...")
        export_all()
