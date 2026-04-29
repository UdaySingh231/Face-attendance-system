import streamlit as st
import cv2
import pandas as pd
from datetime import datetime
import face_recognition

import database as db
import auth
import face_utils
import utils

# --- PAGE CONFIG ---
st.set_page_config(page_title="Face Recognition Attendance", page_icon="📷", layout="wide")

# --- INITIALIZATION ---
def init_system():
    # Initialize DB schema, tables and default admin if they don't exist
    if 'db_initialized' not in st.session_state:
        db.init_db()
        auth.setup_default_admin()
        st.session_state['db_initialized'] = True

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

init_system()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Navigation")
app_mode = st.sidebar.radio("Go To:", ["Student Panel", "Faculty Panel"])

# ----------------- STUDENT PANEL -----------------
if app_mode == "Student Panel":
    st.title("🎓 Student Panel")
    
    tab1, tab2 = st.tabs(["📝 Registration", "📋 View Attendance"])
    
    with tab1:
        st.header("Register New Student")
        with st.form("registration_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name")
                roll_no = st.text_input("Roll Number")
            with col2:
                department = st.selectbox("Department", ["Computer Science", "Electrical", "Mechanical", "Civil", "Other"])
                year = st.selectbox("Year", ["1st Year", "2nd Year", "3rd Year", "4th Year"])
                
            st.write("Capture Face for Recognition Registration")
            webcam_image = st.camera_input("Take a clear photo of your face")
            
            submit_btn = st.form_submit_button("Register Student")
            
        if submit_btn:
            if not name or not roll_no:
                st.error("Name and Roll Number are required.")
            elif not webcam_image:
                st.error("Please take a photo for registration.")
            else:
                with st.spinner("Processing..."):
                    # Process face encoding
                    img_bytes = webcam_image.getvalue()
                    face_encoding = face_utils.get_face_encoding_from_bytes(img_bytes)
                    
                    if face_encoding is None:
                        st.error("No face found in the image. Please take a clearer photo.")
                    else:
                        success, msg = db.add_student(name, roll_no, department, year, face_encoding)
                        if success:
                            st.success(f"Registration Successful for {name} ({roll_no}).")
                        else:
                            st.error(f"Registration Failed: {msg}")
                            
    with tab2:
        st.header("My Attendance Records")
        search_roll = st.text_input("Enter your Roll Number to view records:")
        if st.button("Search"):
            student = db.get_student_by_roll(search_roll)
            if not student:
                st.warning("Student not found.")
            else:
                st.subheader(f"Records for {student['name']}")
                records = db.get_attendance_records(student_id=student['id'])
                if records:
                    df = pd.DataFrame(records)
                    st.dataframe(df[['date', 'time', 'status']], use_container_width=True)
                else:
                    st.info("No attendance records found.")


# ----------------- FACULTY PANEL -----------------
elif app_mode == "Faculty Panel":
    st.title("👨‍🏫 Faculty & Admin Panel")
    
    if not st.session_state['logged_in']:
        st.subheader("Faculty Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            l_btn = st.form_submit_button("Login")
            
            if l_btn:
                success, msg = auth.login_faculty(username, password)
                if success:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error(msg)
                    
        # Dev note/Hint for default creds
        st.info("System defaults to `admin`  `admin123` on first initialization.")
        
    else:
        st.sidebar.button("Logout", on_click=lambda: st.session_state.update({'logged_in': False}))
        
        f_tab1, f_tab2, f_tab3 = st.tabs(["📹 Take Attendance", "📊 Analytics", "👥 Manage Students"])
        
        with f_tab1:
            st.header("Real-Time Attendance Session")
            st.info("Turn on the camera to start real-time face matching.")
            
            run_camera = st.checkbox("Start Camera Session")
            FRAME_WINDOW = st.image([])
            
            if run_camera:
                try:
                    # Added cv2.CAP_DSHOW to prevent Windows black screen camera issues
                    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                    if not camera.isOpened():
                        st.error("Cannot access local webcam.")
                    else:
                        known_students = db.get_all_students()
                        
                        while run_camera:
                            success, frame = camera.read()
                            if not success:
                                st.error("Failed to read frame from camera.")
                                break
                            
                            # Convert frame BGR to RGB for processing
                            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            
                            # Scale down frame for faster processing
                            small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)
                            
                            face_locations = face_recognition.face_locations(small_frame)
                            face_encodings = face_recognition.face_encodings(small_frame, face_locations)
                            
                            for face_loc, face_enc in zip(face_locations, face_encodings):
                                # Scale back up face locations
                                top, right, bottom, left = [i * 4 for i in face_loc]
                                
                                match_id = face_utils.match_face(face_enc.tolist(), known_students)
                                name = "Unknown"
                                box_color = (255, 0, 0) # Red
                                msg_text = ""
                                
                                if match_id:
                                    student = next((s for s in known_students if s['id'] == match_id), None)
                                    if student:
                                        name = student['name']
                                        box_color = (0, 255, 0) # Green
                                        
                                        # Mark attendance
                                        status, msg = db.mark_attendance(match_id)
                                        if status:
                                            msg_text = "Marked!"
                                        elif "already marked" in msg:
                                            msg_text = "Already Marked"
                                        else:
                                            msg_text = "DB Error"
                                            
                                        # Draw message
                                        cv2.putText(frame, msg_text, (left, bottom + 20), cv2.FONT_HERSHEY_DUPLEX, 0.5, box_color, 1)

                                # Draw box highlighting the face
                                cv2.rectangle(frame, (left, top), (right, bottom), box_color, 2)
                                cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

                            # Push back to Streamlit
                            FRAME_WINDOW.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                finally:
                    if 'camera' in locals():
                        camera.release()
            else:
                st.write("Camera is OFF.")

        with f_tab2:
            st.header("Attendance Analytics")
            col1, col2 = st.columns(2)
            today_str = datetime.now().strftime('%Y-%m-%d')
            
            # Overview Metrics
            all_students = db.get_all_students()
            total_students_count = len(all_students)
            today_records = db.get_attendance_records(date=today_str)
            present_today_count = len(today_records)
            
            with col1:
                st.metric("Total Enrolled Students", total_students_count)
            with col2:
                st.metric("Present Today", present_today_count)
                
            st.divider()
            
            # Live Dataframe & CSV Download
            st.subheader(f"Detailed Records for {today_str}")
            if today_records:
                df_today = pd.DataFrame(today_records)
                st.dataframe(df_today[['name', 'roll_no', 'department', 'time', 'status']], use_container_width=True)
                
                csv = df_today.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Today's Attendance CSV",
                    data=csv,
                    file_name=f'attendance_{today_str}.csv',
                    mime='text/csv',
                )
            else:
                st.info("No attendance marked for today yet.")
                
            st.divider()
            st.subheader("Attendance Graphs")
            c1, c2 = st.columns(2)
            with c1:
                # Pie Chart
                if total_students_count > 0:
                    pie_fig = utils.generate_attendance_pie_chart(total_students_count, present_today_count)
                    st.plotly_chart(pie_fig, use_container_width=True)
                else:
                    st.write("No students enrolled yet to show pie chart.")
            with c2:
                # Bar Chart
                all_records = db.get_attendance_records()
                if all_records:
                    bar_fig = utils.generate_weekly_bar_chart(all_records)
                    if bar_fig:
                        st.plotly_chart(bar_fig, use_container_width=True)
                else:
                    st.write("No historical data to show timeline.")

        with f_tab3:
            st.header("Manage Enrolled Students")
            all_stu = db.get_all_students()
            if not all_stu:
                st.info("No students are currently enrolled.")
            else:
                df_stu = pd.DataFrame(all_stu)
                # Hide face encoding blob from display
                st.dataframe(df_stu[['id', 'name', 'roll_no', 'department', 'year']], use_container_width=True)
                
                st.subheader("Remove Student")
                del_id = st.number_input("Enter Student ID to remove", min_value=1, step=1)
                if st.button("Delete Student"):
                    if db.delete_student(del_id):
                        st.success(f"Student {del_id} removed successfully.")
                        st.rerun()
                    else:
                        st.error("Student not found or could not be deleted.")
