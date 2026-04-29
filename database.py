import mysql.connector
from mysql.connector import Error
import json
import logging

import os

def get_connection():
    """Establishes connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', 'uday'),
            database=os.environ.get('DB_NAME', 'face_attendance_db'),
            port=int(os.environ.get('DB_PORT', 3306))
        )
        return connection
    except Error as e:
        if e.errno == 1049:  # Unknown database
            return create_database_and_connect()
        logging.error(f"Error connecting to MySQL: {e}")
        return None

def create_database_and_connect():
    """Creates the database if it doesn't exist and connects to it."""
    try:
        connection = mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', 'uday'),
            port=int(os.environ.get('DB_PORT', 3306))
        )
        if connection.is_connected():
            cursor = connection.cursor()
            db_name = os.environ.get('DB_NAME', 'face_attendance_db')
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            cursor.close()
            connection.close()
            return get_connection()
    except Error as e:
        logging.error(f"Error creating database: {e}")
        return None

def init_db(admin_username="admin", admin_password_hash=None):
    """Initializes tables in the database if they do not exist."""
    conn = get_connection()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()

        # Students table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                roll_no VARCHAR(50) UNIQUE NOT NULL,
                department VARCHAR(100) NOT NULL,
                year VARCHAR(20) NOT NULL,
                face_encoding TEXT NOT NULL
            )
        ''')

        # Attendance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                status VARCHAR(20) DEFAULT 'Present',
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE KEY unique_attendance (student_id, date)
            )
        ''')

        # Faculty table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faculty (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            )
        ''')
        
        # Insert default admin if table is empty and hash is provided
        if admin_password_hash:
            cursor.execute("SELECT COUNT(*) FROM faculty")
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.execute("INSERT INTO faculty (username, password) VALUES (%s, %s)", (admin_username, admin_password_hash))

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        logging.error(f"Error initializing database: {e}")
        return False


def add_student(name, roll_no, department, year, face_encoding_list):
    """Adds a new student to the database. face_encoding_list should be a python list of floats."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed"
    try:
        cursor = conn.cursor()
        encoding_json = json.dumps(face_encoding_list)
        cursor.execute(
            "INSERT INTO students (name, roll_no, department, year, face_encoding) VALUES (%s, %s, %s, %s, %s)",
            (name, roll_no, department, year, encoding_json)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Student registered successfully"
    except Error as e:
        if e.errno == 1062: # Duplicate entry
            return False, "Roll number already exists"
        return False, str(e)


def get_all_students():
    """Retrieves all students' details along with their face encodings."""
    conn = get_connection()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    
    # Parse the json strings back to lists
    for st in students:
        st['face_encoding'] = json.loads(st['face_encoding'])
        
    cursor.close()
    conn.close()
    return students


def mark_attendance(student_id):
    """Marks attendance for a student. Returns (Success_Bool, Message_String)."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed"
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO attendance (student_id, date, time, status) VALUES (%s, CURDATE(), CURTIME(), 'Present')", (student_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Attendance marked successfully"
    except Error as e:
        if e.errno == 1062: # Duplicate entry because of unique constraint on student_id + date
            return False, "Attendance already marked for today"
        return False, str(e)

def get_attendance_records(date=None, student_id=None):
    """Gets attendance records. Can filter by date or student_id."""
    conn = get_connection()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    
    query = '''
        SELECT a.id, s.name, s.roll_no, s.department, a.date, a.time, a.status 
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE 1=1
    '''
    params = []
    
    if date:
        query += " AND a.date = %s"
        params.append(date)
    
    if student_id:
        query += " AND a.student_id = %s"
        params.append(student_id)
        
    query += " ORDER BY a.date DESC, a.time DESC"
    
    cursor.execute(query, tuple(params))
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    return records


def delete_student(student_id):
    """Deletes a student and their attendance records via cascade."""
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
        conn.commit()
        row_count = cursor.rowcount
        cursor.close()
        conn.close()
        return row_count > 0
    except Error as e:
        logging.error(f"Error deleting student: {e}")
        return False

def get_student_by_roll(roll_no):
    """Get student details by roll number"""
    conn = get_connection()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE roll_no = %s", (roll_no,))
    student = cursor.fetchone()
    cursor.close()
    conn.close()
    return student

def get_faculty_by_username(username):
    """Get faculty by username"""
    conn = get_connection()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM faculty WHERE username = %s", (username,))
    faculty = cursor.fetchone()
    cursor.close()
    conn.close()
    return faculty
