from typing import List, Optional, Dict, Any
import sqlite3
import json
from .connection import get_db_connection

def init_db():
    """Initialize the database with required tables."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create batch_years table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS batch_years (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create departments table with custom department_id
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_id TEXT UNIQUE NOT NULL,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create galleries table to track gallery files
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS galleries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year_id INTEGER,
            department_id INTEGER,
            file_path TEXT UNIQUE NOT NULL,
            identity_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (year_id) REFERENCES batch_years (id),
            FOREIGN KEY (department_id) REFERENCES departments (id)
        )
        ''')

        # Create quality_check_reports table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS quality_check_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department TEXT NOT NULL,
            year TEXT NOT NULL,
            total_checked INTEGER NOT NULL,
            passed_count INTEGER NOT NULL,
            failed_count INTEGER NOT NULL,
            borderline_count INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(department, year, created_at)
        )
        ''')

        # Create quality_check_results table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS quality_check_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            student_id TEXT NOT NULL,
            status TEXT NOT NULL,
            issues TEXT,
            FOREIGN KEY (report_id) REFERENCES quality_check_reports (id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,    
            register_no BIGINT,
            name TEXT,
            dob DATE,
            department_id INT,
            department TEXT,
            batch TEXT,
            regulation TEXT,
            semester TEXT,
            section TEXT DEFAULT NULL
        )
        ''')
        
        # Add section column to existing students table if it doesn't exist
        try:
            cursor.execute("ALTER TABLE students ADD COLUMN section TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            # Column already exists
            pass

        # Insert default data if tables are empty
        cursor.execute("SELECT COUNT(*) FROM batch_years")
        if cursor.fetchone()[0] == 0:
            default_years = ["2029", "2028", "2027", "2026"]
            cursor.executemany("INSERT OR IGNORE INTO batch_years (year) VALUES (?)", 
                              [(year,) for year in default_years])
        
        cursor.execute("SELECT COUNT(*) FROM departments")
        if cursor.fetchone()[0] == 0:
            default_departments = [
                ("DPT001", "CS"),
                ("DPT002", "IT"), 
                ("DPT003", "ECE"),
                ("DPT004", "EEE"),
                ("DPT005", "CIVIL")
            ]
            cursor.executemany("INSERT OR IGNORE INTO departments (department_id, name) VALUES (?, ?)", 
                             default_departments)
        
        conn.commit()

def get_batch_years():
    """Get all batch years from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT year FROM batch_years ORDER BY year")
        return [row['year'] for row in cursor.fetchall()]

def get_departments():
    """Get all departments from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT department_id, name FROM departments ORDER BY name, department_id")
        return [{"id": row['department_id'], "name": row['name']} for row in cursor.fetchall()]

def get_department_names():
    """Get just the department names (for backward compatibility)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM departments ORDER BY name")
        return [row['name'] for row in cursor.fetchall()]

def get_department_ids():
    """Get just the department IDs (for backward compatibility)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT department_id FROM departments ORDER BY name")
        return [row['department_id'] for row in cursor.fetchall()]

def get_department_by_id(department_id: str) -> Optional[Dict[str, str]]:
    """Get department by its custom ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT department_id, name FROM departments WHERE department_id = ?", (department_id,))
        row = cursor.fetchone()
        if row:
            return {"name": row['name']}
        return None

def get_department_by_name(name: str) -> Optional[Dict[str, str]]:
    """Get department by its name."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT department_id, name FROM departments WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return {"id": row['department_id'], "name": row['name']}
        return None

def get_department_by_name_or_id(name_or_id: str) -> Optional[Dict[str, str]]:
    """Get department by either its name or ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        print(f"Looking for department with name or ID: {name_or_id}")
        
        # Try to find by name first
        cursor.execute("SELECT department_id, name FROM departments WHERE name = ?", (name_or_id,))
        row = cursor.fetchone()
        if row:
            print(f"Found by name: ID={row['department_id']}, Name={row['name']}")
            return {"department_id": row['department_id'], "name": row['name']}
        
        # Then try by ID
        cursor.execute("SELECT department_id, name FROM departments WHERE department_id = ?", (name_or_id,))
        row = cursor.fetchone()
        if row:
            print(f"Found by ID: ID={row['department_id']}, Name={row['name']}")
            return {"department_id": row['department_id'], "name": row['name']}
        
        # Special case: check if the name_or_id is a numeric string that might be stored incorrectly
        if name_or_id.isdigit():
            cursor.execute("SELECT department_id, name FROM departments WHERE department_id LIKE ?", (f"%{name_or_id}%",))
            row = cursor.fetchone()
            if row:
                print(f"Found by partial ID match: ID={row['department_id']}, Name={row['name']}")
                return {"department_id": row['department_id'], "name": row['name']}
        
        print(f"Department not found: {name_or_id}")
        return None

def add_batch_year(year):
    """Add a new batch year to the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO batch_years (year) VALUES (?)", (year,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Year already exists
            return False

def delete_batch_year(year):
    """Delete a batch year from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM batch_years WHERE year = ?", (year,))
        conn.commit()
        return cursor.rowcount > 0

def add_department(department_id: str, name: str):
    """Add a new department to the database with custom ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO departments (department_id, name) VALUES (?, ?)", (department_id, name))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Department ID or name already exists
            return False

def delete_department(department_id: str):
    """Delete a department from the database by its custom ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM departments WHERE department_id = ?", (department_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_gallery_info(year: str, department: str) -> Optional[Dict[str, Any]]:
    """Get gallery information for a specific year and department."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT g.*, by.year, d.name as department_name, d.department_id
        FROM galleries g
        JOIN batch_years by ON g.year_id = by.id
        JOIN departments d ON g.department_id = d.id
        WHERE by.year = ? AND d.name = ?
        ''', (year, department))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def register_gallery(year: str, department: str, file_path: str, identity_count: int = 0) -> bool:
    """Register a gallery file in the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get year and department IDs
        cursor.execute("SELECT id FROM batch_years WHERE year = ?", (year,))
        year_row = cursor.fetchone()
        if not year_row:
            return False
        
        cursor.execute("SELECT id FROM departments WHERE name = ?", (department,))
        dept_row = cursor.fetchone()
        if not dept_row:
            return False
        
        year_id = year_row[0]
        dept_id = dept_row[0]
        
        try:
            cursor.execute('''
            INSERT OR REPLACE INTO galleries (year_id, department_id, file_path, identity_count, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (year_id, dept_id, file_path, identity_count))
            conn.commit()
            return True
        except sqlite3.Error:
            return False

def update_gallery_count(file_path: str, identity_count: int) -> bool:
    """Update the identity count for a gallery."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE galleries 
        SET identity_count = ?, updated_at = CURRENT_TIMESTAMP
        WHERE file_path = ?
        ''', (identity_count, file_path))
        conn.commit()
        return cursor.rowcount > 0

def list_all_galleries() -> List[Dict[str, Any]]:
    """List all registered galleries with their details."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT g.*, by.year, d.name as department_name, d.department_id
        FROM galleries g
        JOIN batch_years by ON g.year_id = by.id
        JOIN departments d ON g.department_id = d.id
        ORDER BY by.year, d.name
        ''')
        
        return [dict(row) for row in cursor.fetchall()]

def remove_gallery(year: str, department: str) -> bool:
    """Remove a gallery registration from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        DELETE FROM galleries 
        WHERE year_id = (SELECT id FROM batch_years WHERE year = ?)
        AND department_id = (SELECT id FROM departments WHERE name = ?)
        ''', (year, department))
        conn.commit()
        return cursor.rowcount > 0

def get_database_stats() -> Dict[str, Any]:
    """Get database statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM batch_years")
        batch_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM departments")
        dept_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM galleries")
        gallery_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(identity_count) FROM galleries")
        total_identities = cursor.fetchone()[0] or 0
        
        from .connection import DB_PATH
        return {
            "batch_years_count": batch_count,
            "departments_count": dept_count,
            "galleries_count": gallery_count,
            "total_identities": total_identities,
            "database_path": DB_PATH
        }

def save_quality_check_report(report_data: Dict[str, Any]) -> int:
    """Save a quality check report and its results to the database. Overwrites existing report for same dept-year."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if a report already exists for this department-year combination
        cursor.execute('''
        SELECT id FROM quality_check_reports 
        WHERE department = ? AND year = ?
        ORDER BY created_at DESC LIMIT 1
        ''', (report_data['department'], report_data['year']))
        
        existing_report = cursor.fetchone()
        
        if existing_report:
            # Delete existing report and its results
            report_id = existing_report['id']
            cursor.execute('DELETE FROM quality_check_results WHERE report_id = ?', (report_id,))
            cursor.execute('DELETE FROM quality_check_reports WHERE id = ?', (report_id,))
            print(f"Overwriting existing quality check report for {report_data['department']} {report_data['year']}")
        
        # Insert the new report
        cursor.execute('''
        INSERT INTO quality_check_reports (department, year, total_checked, passed_count, failed_count, borderline_count)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            report_data['department'],
            report_data['year'],
            report_data['total_checked'],
            len(report_data['passed_students']),
            len(report_data['failed_students']),
            len(report_data['borderline_students'])
        ))
        report_id = cursor.lastrowid
        
        # Insert passed students
        for student_id in report_data['passed_students']:
            cursor.execute('''
            INSERT INTO quality_check_results (report_id, student_id, status)
            VALUES (?, ?, 'pass')
            ''', (report_id, student_id))
            
        # Insert failed students
        for student_id in report_data['failed_students']:
            cursor.execute('''
            INSERT INTO quality_check_results (report_id, student_id, status)
            VALUES (?, ?, 'fail')
            ''', (report_id, student_id))
            
        # Insert borderline students
        for student in report_data['borderline_students']:
            cursor.execute('''
            INSERT INTO quality_check_results (report_id, student_id, status, issues)
            VALUES (?, ?, 'borderline', ?)
            ''', (report_id, student['regNo'], json.dumps(student['issues'])))
            
        conn.commit()
        return report_id

def get_quality_check_reports(department: Optional[str] = None, year: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get quality check reports, optionally filtered by department and year."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM quality_check_reports"
        params = []
        
        if department or year:
            query += " WHERE "
            if department:
                query += "department = ?"
                params.append(department)
            if year:
                if department:
                    query += " AND "
                query += "year = ?"
                params.append(year)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_quality_check_report_details(report_id: int) -> Optional[Dict[str, Any]]:
    """Get a single quality check report and its detailed results."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get the main report
        cursor.execute("SELECT * FROM quality_check_reports WHERE id = ?", (report_id,))
        report = cursor.fetchone()
        
        if not report:
            return None
        
        # Get the detailed results
        cursor.execute("SELECT * FROM quality_check_results WHERE report_id = ?", (report_id,))
        results = [dict(row) for row in cursor.fetchall()]
        
        report_details = dict(report)
        report_details['results'] = results
        
        return report_details

# Initialize the database when the module is imported
init_db()

def get_students_by_dept_and_batch(dept: str, batch: str):
    """Get all students from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE department_id = ? AND batch = ?", (dept, batch))
        print('[DEBUG] Executing query to get students by department and batch:', dept, batch)
        return [dict(row) for row in cursor.fetchall()]

def save_student_to_database(student_data: dict) -> bool:
    """Save student data to the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            # Check if student already exists
            cursor.execute("SELECT id FROM students WHERE register_no = ?", (student_data.get('regNo'),))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing student with section data
                cursor.execute("""
                    UPDATE students 
                    SET name = ?, department = ?, batch = ?, section = ?
                    WHERE register_no = ?
                """, (
                    student_data.get('name'),
                    student_data.get('dept'),
                    student_data.get('batch'),
                    student_data.get('section'),
                    student_data.get('regNo')
                ))
            else:
                # Insert new student
                cursor.execute("""
                    INSERT INTO students (register_no, name, department, batch, section)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    student_data.get('regNo'),
                    student_data.get('name'),
                    student_data.get('dept'),
                    student_data.get('batch'),
                    student_data.get('section')
                ))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving student to database: {e}")
            conn.rollback()
            return False

def get_existing_quality_results(department: str, year: str) -> Optional[Dict[str, Any]]:
    """Get existing quality check results for a specific department-year combination."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get the most recent report for this department-year
        cursor.execute('''
        SELECT * FROM quality_check_reports 
        WHERE department = ? AND year = ?
        ORDER BY created_at DESC LIMIT 1
        ''', (department, year))
        
        report = cursor.fetchone()
        if not report:
            return None
        
        report_dict = dict(report)
        
        # Get the detailed results
        cursor.execute('''
        SELECT student_id, status, issues FROM quality_check_results 
        WHERE report_id = ?
        ''', (report['id'],))
        
        results = cursor.fetchall()
        
        # Organize results by status
        passed_students = []
        failed_students = []
        borderline_students = []
        
        for result in results:
            if result['status'] == 'pass':
                passed_students.append(result['student_id'])
            elif result['status'] == 'fail':
                failed_students.append(result['student_id'])
            elif result['status'] == 'borderline':
                issues = json.loads(result['issues']) if result['issues'] else []
                borderline_students.append({
                    'regNo': result['student_id'],
                    'issues': issues
                })
        
        return {
            "success": True,
            "message": f"Found existing quality results for {department} {year}",
            "has_results": True,
            "passed_students": passed_students,
            "failed_students": failed_students,
            "borderline_students": borderline_students,
            "total_checked": report_dict['total_checked'],
            "pass_rate": (len(passed_students) / report_dict['total_checked'] * 100) if report_dict['total_checked'] > 0 else 0,
            "created_at": report_dict['created_at']
        }