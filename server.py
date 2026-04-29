import os
import base64
import cv2
import numpy as np
import traceback
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session

import database as db
import auth
import face_utils
import face_recognition

app = Flask(__name__)
app.secret_key = "super_secret_key_attendance"

# Initialize DB on start
db.init_db()
auth.setup_default_admin()

@app.route('/')
def index():
    return render_template('index.html')

# --- STUDENT API ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    roll_no = data.get('roll_no')
    department = data.get('department')
    year = data.get('year')
    image_data = data.get('image')
    
    if not all([name, roll_no, department, year, image_data]):
        return jsonify({'success': False, 'message': 'Missing required fields'})
        
    try:
        img_str = image_data.split(',')[1]
        img_bytes = base64.b64decode(img_str)
        face_encoding = face_utils.get_face_encoding_from_bytes(img_bytes)
        
        if face_encoding is None:
            return jsonify({'success': False, 'message': 'No face found in the image. Please take a clearer photo.'})
            
        success, msg = db.add_student(name, roll_no, department, year, face_encoding)
        return jsonify({'success': success, 'message': msg})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/attendance/student/<roll_no>', methods=['GET'])
def student_attendance(roll_no):
    student = db.get_student_by_roll(roll_no)
    if not student:
        return jsonify({'success': False, 'message': 'Student not found.'})
        
    records = db.get_attendance_records(student_id=student['id'])
    
    # Format time for JSON serialization
    formatted_records = []
    for r in records:
        time_str = str(r['time'])
        if len(time_str.split(':')) == 3:
            r['time'] = time_str
        elif hasattr(r['time'], 'strftime'):
            r['time'] = r['time'].strftime('%H:%M:%S')
        else:
             r['time'] = str(r['time'])
             
        # Format date    
        r['date'] = str(r['date'])
        formatted_records.append(r)
        
    return jsonify({
        'success': True,
        'student': {'name': student['name'], 'roll_no': student['roll_no']},
        'records': formatted_records
    })

# --- FACULTY API ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    success, msg = auth.login_faculty(username, password)
    if success:
        session['logged_in'] = True
        session['username'] = username
        return jsonify({'success': True, 'message': 'Logged in successfully'})
    return jsonify({'success': False, 'message': msg})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})
    
@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    if session.get('logged_in'):
        return jsonify({'loggedIn': True, 'username': session.get('username')})
    return jsonify({'loggedIn': False})
    
@app.route('/api/faculty/dashboard', methods=['GET'])
def faculty_dashboard():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    today_str = datetime.now().strftime('%Y-%m-%d')
    all_students = db.get_all_students()
    total_students_count = len(all_students)
    today_records = db.get_attendance_records(date=today_str)
    present_today_count = len(today_records)
    
    # Format time
    formatted_today = []
    for r in today_records:
        r['time'] = str(r['time'])
        r['date'] = str(r['date'])
        formatted_today.append(r)
        
    return jsonify({
        'success': True,
        'metrics': {
            'total_students': total_students_count,
            'present_today': present_today_count
        },
        'today_records': formatted_today
    })
    
@app.route('/api/faculty/students', methods=['GET'])
def faculty_students():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    all_stu = db.get_all_students()
    # Strip face_encoding
    for s in all_stu:
        s.pop('face_encoding', None)
        
    return jsonify({'success': True, 'students': all_stu})

@app.route('/api/faculty/student/<int:student_id>', methods=['DELETE'])
def delete_student_api(student_id):
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    if db.delete_student(student_id):
        return jsonify({'success': True, 'message': f'Student {student_id} removed.'})
    return jsonify({'success': False, 'message': 'Student not found or could not be deleted.'})

@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    data = request.json
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({'success': False, 'message': 'No image provided'})
        
    try:
        img_str = image_data.split(',')[1]
        img_bytes = base64.b64decode(img_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)
        
        face_locations = face_recognition.face_locations(small_frame)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)
        
        known_students = db.get_all_students()
        results = []
        
        for face_loc, face_enc in zip(face_locations, face_encodings):
            top, right, bottom, left = [i * 4 for i in face_loc] # Scale back up
            match_id = face_utils.match_face(face_enc.tolist(), known_students)
            
            name = "Unknown"
            status_text = ""
            
            if match_id:
                student = next((s for s in known_students if s['id'] == match_id), None)
                if student:
                    name = student['name']
                    status, msg = db.mark_attendance(match_id)
                    if status:
                        status_text = "Marked!"
                    elif "already marked" in msg.lower():
                        status_text = "Already Marked"
                    else:
                        status_text = msg
                        
            results.append({
                'box': {'top': top, 'right': right, 'bottom': bottom, 'left': left},
                'name': name,
                'status': status_text
            })
            
        return jsonify({'success': True, 'faces': results})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
