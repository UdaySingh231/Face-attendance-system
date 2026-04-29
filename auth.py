import bcrypt
import database as db

def hash_password(password):
    """Hashes a password using bcrypt."""
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password, hashed):
    """Verifies a password against a hash."""
    if not password or not hashed:
        return False
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def login_faculty(username, password):
    """Authenticates a faculty member."""
    faculty = db.get_faculty_by_username(username)
    if faculty:
        if verify_password(password, faculty['password']):
            return True, "Login successful"
        else:
            return False, "Invalid password"
    return False, "Username not found"

def setup_default_admin():
    """Creates a default admin if none exist"""
    password_hash = hash_password("admin123")
    db.init_db(admin_username="admin", admin_password_hash=password_hash)
