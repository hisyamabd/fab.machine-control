from flask import Flask, request, jsonify, Response, redirect, url_for, session
from flask_cors import CORS
from functools import wraps
import cv2 
import face_recognition
import pickle
import threading
import time
import numpy as np

print("="*60)
print("🚀 FLASK SERVER - MULTI-DEVICE CAMERA ACCESS")
print("="*60)

# --- INISIALISASI FLASK ---
app = Flask(__name__)
app.secret_key = 'change-this-secret-key-in-production-12345'
CORS(app)

# --- DATABASE USERS ---
USERS = {
    'admin': {
        'password': 'admin123',
        'role': 'administrator',
        'name': 'Administrator'
    },
    'operator': {
        'password': 'operator123',
        'role': 'operator',
        'name': 'Operator User'
    },
    'supervisor': {
        'password': 'super123',
        'role': 'supervisor',
        'name': 'Supervisor'
    }
}

# --- DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# --- DATABASE FACE RECOGNITION ---
try:
    with open("encodings.pickle", "rb") as f:
        database = pickle.load(f)
        print("✅ Database face recognition dimuat!") 
        print(f"   Total wajah terdaftar: {len(set(database['names']))}")
except FileNotFoundError:
    print("❌ WARNING: 'encodings.pickle' tidak ditemukan.")
    database = None

# ===== PARAMETER OPTIMASI =====
TOLERANSI_JARAK = 0.45
PROSES_SETIAP_N_FRAME = 3
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
scale_factor = 0.4
JPEG_QUALITY = 85

# ===== MULTI-CAMERA SUPPORT =====
# Simpan frame terakhir dalam buffer
frame_buffer = None
buffer_lock = threading.Lock()
capture_thread = None
capture_active = False

# Variabel state
kotak_wajah_terakhir = []
labels_terakhir = []
frame_counter = 0

# Status operator
status_lock = threading.Lock()
operator_detected_now = False
operator_name_now = None

# Variabel kontrol
is_camera_active = False 
current_camera_id = 0     
camera = None

print("✅ Variabel global diinisialisasi")

# ===========================
# HTML LOGIN (EMBEDDED)
# ===========================

LOGIN_HTML = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Login - Fabrication Machine Control</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: Inter, system-ui, Arial, sans-serif;
            padding: 20px;
        }
        .login-container {
            background: #fff;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
            max-width: 900px;
            width: 100%;
            display: flex;
        }
        .login-left {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .machine-image {
            width: 100%;
            max-width: 350px;
            height: auto;
            margin-bottom: 30px;
            filter: drop-shadow(0 10px 20px rgba(0,0,0,0.3));
        }
        .login-left h2 {
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 15px;
            text-align: center;
        }
        .login-left p {
            text-align: center;
            font-size: 0.95rem;
            opacity: 0.9;
            line-height: 1.5;
        }
        .login-right {
            padding: 50px 40px;
            flex: 1;
        }
        .login-right h3 {
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 10px;
            color: #333;
        }
        .form-control {
            padding: 12px 15px;
            border-radius: 8px;
            border: 1px solid #ddd;
        }
        .form-control:focus {
            border-color: #0d6efd;
            box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.15);
        }
        .btn-login {
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }
        .btn-login:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(13, 110, 253, 0.4);
        }
        .alert {
            border-radius: 8px;
            display: none;
        }
        .copyright-footer {
            margin-top: 25px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
        }
        .copyright-footer .year {
            font-weight: 600;
            color: #333;
        }
        .copyright-footer .company {
            font-weight: 700;
            color: #667eea;
        }
        @media (max-width: 768px) {
            .login-container { flex-direction: column; }
            .login-left { padding: 30px 20px; }
            .machine-image { max-width: 250px; }
            .login-right { padding: 30px 25px; }
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-left">
            <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgZmlsbD0icmdiYSgyNTUsMjU1LDI1NSwwLjEpIi8+CiAgPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMjAwLDIwMCkiPgogICAgPCEtLSBNYWNoaW5lIEJhc2UgLS0+CiAgICA8cmVjdCB4PSItMTIwIiB5PSI0MCIgd2lkdGg9IjI0MCIgaGVpZ2h0PSI4MCIgZmlsbD0iIzJjM2U1MCIgcng9IjUiLz4KICAgIDxyZWN0IHg9Ii0xMDAiIHk9IjYwIiB3aWR0aD0iMjAwIiBoZWlnaHQ9IjQwIiBmaWxsPSIjMzQ0OTVlIi8+CiAgICAKICAgIDwhLS0gQ29udHJvbCBQYW5lbCAtLT4KICAgIDxyZWN0IHg9Ii0xMTAiIHk9IjIwIiB3aWR0aD0iMjIwIiBoZWlnaHQ9IjQwIiBmaWxsPSIjMzQ0OTVlIiByeD0iMyIvPgogICAgPGNpcmNsZSBjeD0iLTgwIiBjeT0iNDAiIHI9IjUiIGZpbGw9IiNlNzRjM2MiLz4KICAgIDxjaXJjbGUgY3g9Ii02MCIgY3k9IjQwIiByPSI1IiBmaWxsPSIjZjM5YzEyIi8+CiAgICA8Y2lyY2xlIGN4PSItNDAiIGN5PSI0MCIgcj0iNSIgZmlsbD0iIzI3YWU2MCIvPgogICAgCiAgICA8IS0tIE1hY2hpbmUgQXJtIC0tPgogICAgPHJlY3QgeD0iLTIwIiB5PSItNjAiIHdpZHRoPSI0MCIgaGVpZ2h0PSI4MCIgZmlsbD0iIzM0NDk1ZSIvPgogICAgPHJlY3QgeD0iLTE1IiB5PSItMTAwIiB3aWR0aD0iMzAiIGhlaWdodD0iNTAiIGZpbGw9IiMyYzNlNTAiLz4KICAgIAogICAgPCEtLSBXb3JrIFN1cmZhY2UgLS0+CiAgICA8cmVjdCB4PSItODAiIHk9Ii0xMCIgd2lkdGg9IjE2MCIgaGVpZ2h0PSIzMCIgZmlsbD0iIzk1YTVhNiIgcng9IjIiLz4KICAgIAogICAgPCEtLSBXaGVlbHMgLS0+CiAgICA8Y2lyY2xlIGN4PSItOTAiIGN5PSIxMjAiIHI9IjEyIiBmaWxsPSIjMmMzZTUwIi8+CiAgICA8Y2lyY2xlIGN4PSItMzAiIGN5PSIxMjAiIHI9IjEyIiBmaWxsPSIjMmMzZTUwIi8+CiAgICA8Y2lyY2xlIGN4PSIzMCIgY3k9IjEyMCIgcj0iMTIiIGZpbGw9IiMyYzNlNTAiLz4KICAgIDxjaXJjbGUgY3g9IjkwIiBjeT0iMTIwIiByPSIxMiIgZmlsbD0iIzJjM2U1MCIvPgogIDwvZz4KPC9zdmc+" 
                 alt="Fabrication Machine" 
                 class="machine-image">
            <h2>Fabrication Machine Control</h2>
            <p>Sistem kontrol mesin fabrikasi dengan face recognition untuk keamanan operator</p>
        </div>
        <div class="login-right">
            <h3>Selamat Datang</h3>
            <p>Silakan login untuk melanjutkan</p>
            <div id="alertBox" class="alert" role="alert">
                <i class="fas fa-exclamation-circle me-2"></i>
                <span id="alertMessage"></span>
            </div>
            <form id="loginForm">
                <div class="mb-3">
                    <label class="form-label">Username</label>
                    <div class="input-group">
                        <span class="input-group-text"><i class="fas fa-user"></i></span>
                        <input type="text" class="form-control" id="username" placeholder="Masukkan username" required>
                    </div>
                </div>
                <div class="mb-4">
                    <label class="form-label">Password</label>
                    <div class="input-group">
                        <span class="input-group-text"><i class="fas fa-lock"></i></span>
                        <input type="password" class="form-control" id="password" placeholder="Masukkan password" required>
                        <button class="btn btn-outline-secondary" type="button" id="togglePassword">
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary btn-login" id="btnLogin">
                    <span id="btnText">Login</span>
                    <span id="btnSpinner" class="spinner-border spinner-border-sm ms-2" style="display:none;"></span>
                </button>
            </form>
            <div class="copyright-footer">
                <p style="margin: 0; color: #6c757d; font-size: 0.9rem;">
                    <i class="fas fa-copyright"></i> 
                    <span class="year">2025</span> 
                    <span class="company">Fabrication Process Machine</span>
                </p>
                <p style="margin: 5px 0 0 0; color: #95a5a6; font-size: 0.8rem;">
                    All rights reserved
                </p>
            </div>
        </div>
    </div>
    <script>
        const FLASK_URL = window.location.origin;
        document.addEventListener('DOMContentLoaded', function() {
            const loginForm = document.getElementById('loginForm');
            const username = document.getElementById('username');
            const password = document.getElementById('password');
            const btnLogin = document.getElementById('btnLogin');
            const btnText = document.getElementById('btnText');
            const btnSpinner = document.getElementById('btnSpinner');
            const alertBox = document.getElementById('alertBox');
            const alertMessage = document.getElementById('alertMessage');
            const togglePassword = document.getElementById('togglePassword');
            
            togglePassword.addEventListener('click', function() {
                const type = password.getAttribute('type') === 'password' ? 'text' : 'password';
                password.setAttribute('type', type);
                const icon = this.querySelector('i');
                icon.classList.toggle('fa-eye');
                icon.classList.toggle('fa-eye-slash');
            });
            
            function showAlert(message, type) {
                alertBox.className = 'alert alert-' + type;
                alertMessage.textContent = message;
                alertBox.style.display = 'block';
                setTimeout(() => { alertBox.style.display = 'none'; }, 5000);
            }
            
            loginForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const usernameValue = username.value.trim();
                const passwordValue = password.value.trim();
                
                if (!usernameValue || !passwordValue) {
                    showAlert('Username dan password harus diisi!', 'warning');
                    return;
                }
                
                btnLogin.disabled = true;
                btnText.textContent = 'Memverifikasi...';
                btnSpinner.style.display = 'inline-block';
                
                fetch(FLASK_URL + '/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: usernameValue, password: passwordValue })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAlert('Login berhasil! Mengalihkan...', 'success');
                        setTimeout(() => { window.location.href = '/dashboard'; }, 1000);
                    } else {
                        showAlert(data.message || 'Username atau password salah!', 'danger');
                        btnLogin.disabled = false;
                        btnText.textContent = 'Login';
                        btnSpinner.style.display = 'none';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showAlert('Gagal terhubung ke server!', 'danger');
                    btnLogin.disabled = false;
                    btnText.textContent = 'Login';
                    btnSpinner.style.display = 'none';
                });
            });
        });
    </script>
</body>
</html>"""

# ===========================
# AUTHENTICATION ROUTES
# ===========================

@app.route('/')
def index():
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('dashboard'))
    return LOGIN_HTML

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username dan password harus diisi!'}), 400
    
    if username in USERS and USERS[username]['password'] == password:
        session['logged_in'] = True
        session['username'] = username
        session['role'] = USERS[username]['role']
        session['name'] = USERS[username]['name']
        
        print(f"✅ Login: {username}")
        return jsonify({
            'success': True,
            'message': 'Login berhasil!',
            'user': {'username': username, 'name': USERS[username]['name'], 'role': USERS[username]['role']}
        }), 200
    else:
        return jsonify({'success': False, 'message': 'Username atau password salah!'}), 401

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    username = session.get('username', 'Unknown')
    session.clear()
    print(f"👋 Logout: {username}")
    return redirect(url_for('login_page'))

@app.route('/check_session')
def check_session():
    if 'logged_in' in session and session['logged_in']:
        return jsonify({
            'logged_in': True,
            'username': session.get('username'),
            'name': session.get('name'),
            'role': session.get('role')
        })
    else:
        return jsonify({'logged_in': False}), 401

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        with open('Web Hisyam.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: Web Hisyam.html tidak ditemukan!</h1>", 404

# ===========================
# CAMERA CAPTURE THREAD (BARU!)
# ===========================

def camera_capture_thread():
    """Thread terpisah untuk capture frame dari kamera"""
    global frame_buffer, buffer_lock, capture_active
    global camera, current_camera_id, is_camera_active
    global kotak_wajah_terakhir, labels_terakhir, frame_counter
    global operator_detected_now, operator_name_now, status_lock
    
    print(f"📹 Thread capture dimulai - Camera ID: {current_camera_id}")
    
    # Buka kamera dengan SHARED access
    cam = cv2.VideoCapture(current_camera_id)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cam.set(cv2.CAP_PROP_FPS, 30)
    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    if not cam.isOpened():
        print("❌ Gagal membuka kamera di thread")
        capture_active = False
        return
    
    print("✅ Kamera berhasil dibuka di thread capture")
    local_frame_counter = 0
    
    while capture_active and is_camera_active:
        ret, frame = cam.read()
        
        if not ret:
            print("⚠️ Gagal membaca frame")
            time.sleep(0.1)
            continue
        
        # FACE DETECTION (setiap N frame)
        if local_frame_counter % PROSES_SETIAP_N_FRAME == 0:
            frame_kecil = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
            frame_rgb = cv2.cvtColor(frame_kecil, cv2.COLOR_BGR2RGB)
            
            kotak_wajah_terakhir = face_recognition.face_locations(frame_rgb, model='hog')
            encodings_live = face_recognition.face_encodings(frame_rgb, kotak_wajah_terakhir)
            
            labels_terakhir = []
            temp_detected = False
            temp_name = None
            
            if database and len(encodings_live) > 0:
                for enc in encodings_live:
                    matches = face_recognition.compare_faces(database["encodings"], enc, tolerance=TOLERANSI_JARAK)
                    label = "wajah tidak dikenali"
                    
                    if True in matches:
                        matched_idxs = [i for i, b in enumerate(matches) if b]
                        counts = {}
                        for i in matched_idxs:
                            nama = database["names"][i]
                            counts[nama] = counts.get(nama, 0) + 1
                        label = max(counts, key=counts.get)
                        temp_detected = True
                        temp_name = label
                    
                    labels_terakhir.append(label)
            
            # Update status
            with status_lock:
                operator_detected_now = temp_detected
                operator_name_now = temp_name if temp_detected else None
        
        local_frame_counter += 1
        
        # DRAW bounding boxes
        for (top, right, bottom, left), label in zip(kotak_wajah_terakhir, labels_terakhir):
            warna = (0, 255, 0) if label != "wajah tidak dikenali" else (0, 0, 255)
            
            top = int(top / scale_factor)
            right = int(right / scale_factor)
            bottom = int(bottom / scale_factor)
            left = int(left / scale_factor)
            
            cv2.rectangle(frame, (left, top), (right, bottom), warna, 2)
            
            font = cv2.FONT_HERSHEY_DUPLEX
            (tw, th), baseline = cv2.getTextSize(label, font, 0.7, 2)
            cv2.rectangle(frame, (left, bottom - th - baseline - 10), 
                         (left + tw + 10, bottom), warna, cv2.FILLED)
            cv2.putText(frame, label, (left + 5, bottom - baseline - 5), 
                       font, 0.7, (255, 255, 255), 2)
        
        # Simpan frame ke buffer (SHARED untuk multiple clients)
        with buffer_lock:
            frame_buffer = frame.copy()
        
        time.sleep(0.01)  # Small delay
    
    cam.release()
    print("🛑 Thread capture dihentikan")

# ===========================
# STREAMING GENERATOR (BARU!)
# ===========================

def generate_frames_from_buffer():
    """Generator yang membaca dari buffer (untuk multiple clients)"""
    global frame_buffer, buffer_lock
    
    print("📹 Client baru terhubung ke stream")
    
    while is_camera_active:
        with buffer_lock:
            if frame_buffer is None:
                time.sleep(0.1)
                continue
            
            frame = frame_buffer.copy()
        
        # Encode JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
        ret, buffer = cv2.imencode('.jpg', frame, encode_param)
        
        if not ret:
            continue
        
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.033)  # ~30 FPS
    
    print("📹 Client disconnect dari stream")

# ===========================
# API ROUTES
# ===========================

@app.route('/operator_status', methods=['GET'])
@login_required
def operator_status():
    global operator_detected_now, operator_name_now, status_lock
    
    with status_lock:
        detected = operator_detected_now
        name = operator_name_now
    
    return jsonify({
        "detected": bool(detected),
        "name": str(name) if name else "Unknown"
    })

@app.route('/start_monitoring', methods=['POST'])
@login_required
def start_monitoring():
    global is_camera_active, current_camera_id, capture_active, capture_thread
    
    data = request.get_json(silent=True)
    if data:
        current_camera_id = data.get('camera_id', 0)
        try:
            current_camera_id = int(current_camera_id)
        except ValueError:
            current_camera_id = 0
    
    if is_camera_active:
        return jsonify({"status": "warning", "message": "Kamera sudah aktif."}), 200
    
    print(f"▶️ START - Multi-device mode - User: {session.get('username')}")
    
    is_camera_active = True
    capture_active = True
    
    # Start capture thread
    capture_thread = threading.Thread(target=camera_capture_thread, daemon=True)
    capture_thread.start()
    
    return jsonify({"status": "success", "message": "Monitoring dimulai (multi-device)."}), 200

@app.route('/stop_monitoring', methods=['POST'])
@login_required
def stop_monitoring():
    global is_camera_active, capture_active
    global operator_detected_now, operator_name_now, status_lock
    
    if not is_camera_active:
        return jsonify({"status": "warning", "message": "Kamera sudah tidak aktif."}), 200
    
    print(f"⏹️ STOP - User: {session.get('username')}")
    
    is_camera_active = False
    capture_active = False
    
    with status_lock:
        operator_detected_now = False
        operator_name_now = None
    
    return jsonify({"status": "success", "message": "Kamera dimatikan."}), 200

@app.route('/video_feed')
@login_required
def video_feed():
    """Video stream dari buffer (support multiple clients)"""
    return Response(
        generate_frames_from_buffer(),
        mimetype='multipart/x-mixed-replace; boundary=frame',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 FLASK SERVER - MULTI-DEVICE CAMERA ACCESS!")
    print("="*60)
    print("📍 URL: http://127.0.0.1:5000")
    print("="*60)
    print("🎥 MODE: Multi-device streaming (HP + Laptop simultaneous)")
    print(f"⚙️  Resolution: {FRAME_WIDTH}x{FRAME_HEIGHT}")
    print(f"⚙️  JPEG Quality: {JPEG_QUALITY}%")
    print("="*60)
    print("👥 USERS:")
    for u, i in USERS.items():
        print(f"   • {u} / {i['password']}")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)