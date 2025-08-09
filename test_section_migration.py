#!/usr/bin/env python3
"""
Test script to verify the section column migration in the students table.
"""

import os
import sys
import sqlite3

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.models import init_db, save_student_to_database
from database.connection import get_db_connection

def test_section_migration():
    """Test that the section column exists and works correctly."""
    
    print("Testing section column migration...")
    
    # Initialize database (this should create/update the students table)
    init_db()
    print("✓ Database initialized")
    
    # Check if section column exists
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(students)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        if 'section' in columns:
            print("✓ Section column exists in students table")
        else:
            print("✗ Section column missing in students table")
            return False
    
    # Test saving student data with section
    test_student_data = {
        'regNo': '123456789012',
        'name': 'Test Student',
        'dept': 'CS',
        'batch': 'Batch2027',
        'section': 'A'
    }
    
    success = save_student_to_database(test_student_data)
    if success:
        print("✓ Successfully saved student with section data")
    else:
        print("✗ Failed to save student with section data")
        return False
    
    # Verify the data was saved correctly
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE register_no = ?", (test_student_data['regNo'],))
        student = cursor.fetchone()
        
        if student and student['section'] == 'A':
            print("✓ Section data saved and retrieved correctly")
        else:
            print("✗ Section data not saved correctly")
            return False
    
    # Clean up test data
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE register_no = ?", (test_student_data['regNo'],))
        conn.commit()
        print("✓ Test data cleaned up")
    
    print("\n🎉 All tests passed! Section migration completed successfully.")
    return True

if __name__ == "__main__":
    test_section_migration()
