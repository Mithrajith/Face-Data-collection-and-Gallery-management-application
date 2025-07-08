import os
import sqlite3
from config.settings import BASE_GALLERY_DIR, BASE_DATA_DIR

def get_gallery_path(year: str, department: str) -> str:
    """Generate a standardized gallery path based on batch year and department"""
    filename = f"{department}_{year}.pth"
    return os.path.join(BASE_GALLERY_DIR, filename)

def get_data_path(year: str, department: str) -> str:
    """Generate a standardized data path for storing preprocessed faces"""
    return os.path.join(BASE_DATA_DIR, f"{department}_{year}")

def get_batch_years_and_departments():
    """Fetch batch years and departments from the main app.db"""
    # Path to the main app.db
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'app.db')
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT year FROM batch_years ORDER BY year')
        years = [row[0] for row in cursor.fetchall()]
        cursor.execute('SELECT department_id, name FROM departments ORDER BY name')
        departments = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
        return {"years": years, "departments": departments}
    finally:
        conn.close()
