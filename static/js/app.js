// --- UI Utilities ---
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'fa-info-circle';
    if(type === 'success') icon = 'fa-check-circle';
    if(type === 'error') icon = 'fa-exclamation-circle';
    
    toast.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <div>${message}</div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease-out forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// --- Navigation & Routing ---
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        
        const targetId = e.target.getAttribute('data-target');
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        document.getElementById(targetId).classList.add('active');

        // Stop live camera if switching away from faculty
        if (targetId !== 'faculty-panel' && isLiveCameraRunning) {
            stopLiveCamera();
        }
    });
});

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const parentId = e.target.closest('.panel').id;
        document.querySelectorAll(`#${parentId} .tab-btn`).forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        
        const targetId = e.target.getAttribute('data-tab');
        document.querySelectorAll(`#${parentId} .tab-content`).forEach(p => p.classList.remove('active'));
        document.getElementById(targetId).classList.add('active');
        
        // Refresh data on specific tabs
        if(targetId === 'analytics-tab') fetchFacultyDashboard();
        if(targetId === 'manage-tab') fetchStudents();
        if(targetId !== 'take-attendance-tab' && isLiveCameraRunning) stopLiveCamera();
    });
});


// --- Global Camera State ---
let regStream = null;
let liveStream = null;
let liveInterval = null;
let isLiveCameraRunning = false;

// --- Student Registration ---
const regVideo = document.getElementById('regVideo');
const regCanvas = document.getElementById('regCanvas');
const captureBtn = document.getElementById('captureBtn');
const retakeBtn = document.getElementById('retakeBtn');
let capturedImage = null; // Base64 image

async function startRegCamera() {
    try {
        regStream = await navigator.mediaDevices.getUserMedia({ video: true });
        regVideo.srcObject = regStream;
    } catch (err) {
        showToast("Error accessing camera. Please allow permissions.", "error");
        console.error(err);
    }
}

// Start camera initially if student panel is visible
startRegCamera();

captureBtn.addEventListener('click', () => {
    if (!regStream) return;
    
    regCanvas.width = regVideo.videoWidth;
    regCanvas.height = regVideo.videoHeight;
    regCanvas.getContext('2d').drawImage(regVideo, 0, 0);
    
    capturedImage = regCanvas.toDataURL('image/jpeg');
    
    // Freeze video
    regVideo.pause();
    captureBtn.style.display = 'none';
    retakeBtn.style.display = 'block';
});

retakeBtn.addEventListener('click', () => {
    regVideo.play();
    capturedImage = null;
    captureBtn.style.display = 'inline-flex';
    retakeBtn.style.display = 'none';
});

document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
}); // Override submit normally, handle via captureBtn

captureBtn.addEventListener('click', async () => {
    const name = document.getElementById('regName').value;
    const roll_no = document.getElementById('regRoll').value;
    const department = document.getElementById('regDept').value;
    const year = document.getElementById('regYear').value;

    if (!name || !roll_no) {
        showToast("Name and Roll Number are required before capturing face.", "error");
        retakeBtn.click();
        return;
    }

    if (!capturedImage) return;

    captureBtn.disabled = true;
    captureBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
    
    try {
        const res = await fetch('/api/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name, roll_no, department, year, image: capturedImage })
        });
        const data = await res.json();
        
        if (data.success) {
            showToast(data.message, "success");
            document.getElementById('registerForm').reset();
            retakeBtn.click(); // Reset camera
        } else {
            showToast(data.message, "error");
            retakeBtn.click();
        }
    } catch (err) {
        showToast("Server error during registration", "error");
        retakeBtn.click();
    } finally {
        captureBtn.disabled = false;
        captureBtn.innerHTML = '<i class="fa-solid fa-camera"></i> Capture & Register';
    }
});

// --- View Attendance (Student) ---
document.getElementById('searchBtn').addEventListener('click', async () => {
    const roll_no = document.getElementById('searchRoll').value;
    if(!roll_no) return showToast("Enter a roll number", "error");

    document.getElementById('searchBtn').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    try {
        const res = await fetch(`/api/attendance/student/${roll_no}`);
        const data = await res.json();
        
        if(data.success) {
            document.getElementById('studentRecordsContainer').style.display = 'block';
            document.getElementById('studentNameDisplay').textContent = `Records for ${data.student.name}`;
            
            const tbody = document.getElementById('studentRecordsBody');
            tbody.innerHTML = '';
            
            if(data.records.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;">No records found.</td></tr>';
            } else {
                data.records.forEach(r => {
                    const row = document.createElement('tr');
                    const badgeClass = r.status.toLowerCase() == 'present' ? 'status-present' : 'status-absent';
                    row.innerHTML = `
                        <td>${r.date}</td>
                        <td>${r.time}</td>
                        <td><span class="status-badge ${badgeClass}">${r.status}</span></td>
                    `;
                    tbody.appendChild(row);
                });
            }
        } else {
            showToast(data.message, "error");
            document.getElementById('studentRecordsContainer').style.display = 'none';
        }
    } catch(err) {
        showToast("Error fetching records", "error");
    } finally {
        document.getElementById('searchBtn').innerHTML = '<i class="fa-solid fa-search"></i> Search';
    }
});


// --- Faculty Login & Dashboard ---
checkAuthStatus();

async function checkAuthStatus() {
    try {
        const res = await fetch('/api/auth/status');
        const data = await res.json();
        if(data.loggedIn) {
            showFacultyDashboard();
        }
    } catch(err) {}
}

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        const data = await res.json();
        if(data.success) {
            showToast(data.message, "success");
            showFacultyDashboard();
        } else {
            showToast(data.message, "error");
        }
    } catch(err) {
        showToast("Login error", "error");
    }
});

document.getElementById('logoutBtn').addEventListener('click', async () => {
    await fetch('/api/logout', {method: 'POST'});
    document.getElementById('facultyLoginView').style.display = 'block';
    document.getElementById('facultyDashboardView').style.display = 'none';
    stopLiveCamera();
    showToast("Logged out successfully", "success");
});

function showFacultyDashboard() {
    document.getElementById('facultyLoginView').style.display = 'none';
    document.getElementById('facultyDashboardView').style.display = 'block';
    
    // Stop student reg camera if running
    if(regStream) {
        regStream.getTracks().forEach(t => t.stop());
        regStream = null;
    }
}

// --- Live Attendance Camera (Faculty) ---
const toggleCameraBtn = document.getElementById('toggleCameraSessionBtn');
const liveVideo = document.getElementById('liveVideo');
const liveCanvas = document.getElementById('liveCanvas');
const hiddenFrameCanvas = document.getElementById('hiddenFrameCanvas');

toggleCameraBtn.addEventListener('click', async () => {
    if(isLiveCameraRunning) {
        stopLiveCamera();
    } else {
        await startLiveCamera();
    }
});

async function startLiveCamera() {
    try {
        liveStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
        liveVideo.srcObject = liveStream;
        document.getElementById('liveCameraContainer').style.display = 'block';
        toggleCameraBtn.textContent = 'Stop Camera Selection';
        toggleCameraBtn.classList.remove('pulse');
        toggleCameraBtn.classList.add('danger');
        isLiveCameraRunning = true;
        
        // Setup canvas size
        liveVideo.onloadedmetadata = () => {
            liveCanvas.width = liveVideo.videoWidth;
            liveCanvas.height = liveVideo.videoHeight;
            hiddenFrameCanvas.width = liveVideo.videoWidth;
            hiddenFrameCanvas.height = liveVideo.videoHeight;
            
            // Start sending frames to backend periodically (every ~300ms)
            liveInterval = setInterval(processLiveFrame, 500); 
        };
    } catch(err) {
        showToast("Error accessing camera for live feed.", "error");
    }
}

function stopLiveCamera() {
    if(liveStream) {
        liveStream.getTracks().forEach(t => t.stop());
        liveStream = null;
    }
    if(liveInterval) clearInterval(liveInterval);
    
    document.getElementById('liveCameraContainer').style.display = 'none';
    toggleCameraBtn.textContent = 'Start Camera Session';
    toggleCameraBtn.classList.add('pulse');
    toggleCameraBtn.classList.remove('danger');
    isLiveCameraRunning = false;
    
    // clear canvas
    const ctx = liveCanvas.getContext('2d');
    ctx.clearRect(0,0,liveCanvas.width, liveCanvas.height);
}

let isProcessingFrame = false;

async function processLiveFrame() {
    if(!isLiveCameraRunning || isProcessingFrame) return;
    
    isProcessingFrame = true;
    const ctx = hiddenFrameCanvas.getContext('2d');
    ctx.drawImage(liveVideo, 0, 0, hiddenFrameCanvas.width, hiddenFrameCanvas.height);
    
    // Reduce quality for speed
    const frameDataUrl = hiddenFrameCanvas.toDataURL('image/jpeg', 0.5);
    
    try {
        const res = await fetch('/api/attendance/mark', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({image: frameDataUrl})
        });
        
        if (res.status === 401) {
            stopLiveCamera();
            document.getElementById('logoutBtn').click();
            return;
        }
        
        const data = await res.json();
        if(data.success) {
            drawFacesBox(data.faces);
        }
    } catch (err) {
        // Ignore network errors occasionally to keep polling alive
    } finally {
        isProcessingFrame = false;
    }
}

function drawFacesBox(facesData) {
    const ctx = liveCanvas.getContext('2d');
    ctx.clearRect(0,0,liveCanvas.width, liveCanvas.height);
    
    facesData.forEach(f => {
        const {top, right, bottom, left} = f.box;
        
        // Colors
        let boxColor = '#ef4444'; // Red for unknown
        if (f.name !== 'Unknown') {
            boxColor = '#10b981'; // Green for matched
        }
        
        // Draw Rectangle
        ctx.strokeStyle = boxColor;
        ctx.lineWidth = 3;
        ctx.strokeRect(left, top, right - left, bottom - top);
        
        // Draw Name badge background
        ctx.fillStyle = boxColor;
        ctx.fillRect(left, bottom, (right - left), 30);
        
        // Draw Text
        ctx.fillStyle = 'white';
        ctx.font = 'bold 16px Outfit, sans-serif';
        // Name
        ctx.fillText(f.name, left + 5, bottom + 20);
        
        // Optional Status Text above box
        if(f.status) {
            ctx.fillStyle = boxColor;
            ctx.font = 'bold 16px Outfit, sans-serif';
            ctx.fillText(f.status, left, top - 10);
        }
    });
}

// --- Analytics Data ---
async function fetchFacultyDashboard() {
    try {
        const res = await fetch('/api/faculty/dashboard');
        const data = await res.json();
        if(data.success) {
            document.getElementById('statTotalStudents').textContent = data.metrics.total_students;
            document.getElementById('statPresentToday').textContent = data.metrics.present_today;
            
            const tbody = document.getElementById('todayRecordsBody');
            tbody.innerHTML = '';
            
            if(data.today_records.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No records marked today.</td></tr>';
            } else {
                data.today_records.forEach(r => {
                    const row = document.createElement('tr');
                    const badgeClass = r.status.toLowerCase() == 'present' ? 'status-present' : 'status-absent';
                    row.innerHTML = `
                        <td>${r.name}</td>
                        <td>${r.roll_no}</td>
                        <td>${r.department}</td>
                        <td>${r.time}</td>
                        <td><span class="status-badge ${badgeClass}">${r.status}</span></td>
                    `;
                    tbody.appendChild(row);
                });
            }
        }
    } catch(err) {}
}

// --- Manage Students ---
async function fetchStudents() {
    try {
        const res = await fetch('/api/faculty/students');
        const data = await res.json();
        if(data.success) {
            const tbody = document.getElementById('manageStudentsBody');
            tbody.innerHTML = '';
            
            if(data.students.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No enrolled students.</td></tr>';
            } else {
                data.students.forEach(s => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${s.id}</td>
                        <td>${s.name}</td>
                        <td>${s.roll_no}</td>
                        <td>${s.department}</td>
                        <td>${s.year}</td>
                        <td>
                            <button class="btn danger" style="padding: 0.25rem 0.5rem; font-size: 0.8rem;" onclick="deleteStudent(${s.id}, '${s.name}')">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            }
        }
    } catch(err) {}
}

async function deleteStudent(id, name) {
    if(!confirm(`Are you sure you want to delete ${name} (ID: ${id})?`)) return;
    
    try {
        const res = await fetch(`/api/faculty/student/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if(data.success) {
            showToast(data.message, 'success');
            fetchStudents(); // refresh list
        } else {
            showToast(data.message, 'error');
        }
    } catch(err) {}
}
