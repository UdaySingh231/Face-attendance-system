import cv2
import face_recognition
import numpy as np

def get_face_encoding_from_bytes(image_bytes):
    """Extracts a face encoding from image bytes (e.g., from Streamlit's camera_input)."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    encodings = face_recognition.face_encodings(rgb_img)
    if not len(encodings):
        return None
    return encodings[0].tolist()  # return first face encoding as a list of floats

def match_face(unknown_encoding, known_encodings, tolerance=0.5):
    """
    Finds the best match for unknown_encoding among known_encodings.
    unknown_encoding: list of floats
    known_encodings: list of dicts. Each dict must have 'id' (student id) and 'face_encoding' (list of floats)
    Returns best_match_id or None
    """
    if not known_encodings or not unknown_encoding:
        return None
        
    known_encs = [np.array(e['face_encoding']) for e in known_encodings]
    unk_enc = np.array(unknown_encoding)
    
    matches = face_recognition.compare_faces(known_encs, unk_enc, tolerance=tolerance)
    if not any(matches): # Quick check if no matches at all
        return None
        
    face_distances = face_recognition.face_distance(known_encs, unk_enc)
    best_match_index = np.argmin(face_distances)
    
    if matches[best_match_index]:
        return known_encodings[best_match_index]['id']
        
    return None
