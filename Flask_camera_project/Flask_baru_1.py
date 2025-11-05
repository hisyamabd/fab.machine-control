from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import cv2 
import time
from ultralytics import YOLO # COMMAND: Impor YOLO dari kode deteksi orangmu!

# Kalo ingin mengganti kamera yg digunakan untuk website, 
# setting nomor kamera pada file Js dan Python . 

# COMMAND: Konfigurasi ini dipindahkan dari file Deteksi orang.
MODEL_PATH = 'best.pt' 
CONFIDENCE_THRESHOLD_SIGNAL = 0.90 
CONFIDENCE_THRESHOLD_DISPLAY = 0.50 

# --- INISIALISASI GLOBAL (HANYA SEKALI SAAT SERVER START) ---
try:
    # COMMAND: Model diinisialisasi SATU KALI di sini.
    model = YOLO(MODEL_PATH)
    print(f"Model YOLO {MODEL_PATH} berhasil dimuat!")
except Exception as e:
    print(f"FATAL ERROR: Gagal memuat model. Pastikan file '{MODEL_PATH}' ada di folder yang sama. {e}")
    # Jika model gagal dimuat, biarkan server berjalan, tapi logging akan menunjukkan kegagalan
    model = None # Set model menjadi None jika gagal

# --- VARIABEL GLOBAL KONTROL FLASK ---
app = Flask(__name__)
CORS(app) 
is_camera_active = False 
current_camera_id = 0    
camera = None       

# ====================================================================
# FUNGSI UTAMA: PEMROSESAN FRAME DAN STREAMING
# ====================================================================

def generate_frames():
    global is_camera_active, camera, current_camera_id
    
    # Inisialisasi kamera JIKA diperintah oleh tombol START
    if camera is None or not camera.isOpened():
        # COMMAND: Menggunakan ID kamera yang dikirim dari website (current_camera_id)
        # Kami mengonversi ID ke integer, dan menggunakan backend MSMF yang sudah berhasil
        
        camera = cv2.VideoCapture(int(current_camera_id), cv2.CAP_DSHOW)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # Memaksa Lebar 1280
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720) # Memaksa Tinggi 720

        if not camera.isOpened():
            is_camera_active = False 
            # COMMAND: Ubah pesan error agar mencantumkan ID kamera yang gagal
            print(f"ERROR: Gagal membuka kamera dengan ID {current_camera_id} dan backend MSMF.")
            return

    # Looping untuk membaca frame kamera selama is_camera_active = True
    while is_camera_active:
        success, frame = camera.read() 
        if not success:
            print("Gagal membaca frame, menghentikan stream.")
            is_camera_active = False
            break
        
        # --- COMMAND: 1. LOGIKA DETEKSI ORANG DIMULAI DI SINI ---
        
        signal_status = 0 # 0 = FALSE
        
        # 1. Jalankan Prediksi YOLO
        # COMMAND: Menggunakan model.predict dari kodemu
        results = model.predict(
            frame, 
            conf=CONFIDENCE_THRESHOLD_DISPLAY, 
            verbose=False, 
            classes=[0] # Asumsi kelas 0 adalah 'human'
        ) 

        annotated_frame = frame.copy() # Frame asli untuk dimodifikasi

        for r in results:
            # PENTING: r.plot() ini yang menggambar kotak/label ke frame
            annotated_frame = r.plot() 
            
            # Loop untuk mengecek sinyal yang SANGAT YAKIN
            for box in r.boxes:
                confidence = box.conf.item() 
                if confidence >= CONFIDENCE_THRESHOLD_SIGNAL:
                    signal_status = 1 # 1 = TRUE
                    break 
            
            if signal_status == 1:
                break 
        
        # 2. Visualisasi Status Sinyal di Frame
        signal_text = "TRUE" if signal_status == 1 else "FALSE"
        base_text = "Human Detection : "
        COLOR_WHITE = (255, 255, 255) 
        COLOR_TRUE = (0, 255, 0) 
        COLOR_FALSE = (0, 0, 255)
        status_color = COLOR_TRUE if signal_status == 1 else COLOR_FALSE
        FONT = cv2.FONT_HERSHEY_SIMPLEX
        FONT_SCALE = 1
        THICKNESS = 2
        START_POS = (10, 30)
        
        # Tulis Base Text
        cv2.putText(annotated_frame, base_text, START_POS, FONT, FONT_SCALE, COLOR_WHITE, THICKNESS)
        
        # Hitung posisi untuk teks TRUE/FALSE
        (text_width, _), _ = cv2.getTextSize(base_text, FONT, FONT_SCALE, THICKNESS)
        new_x_pos = START_POS[0] + text_width
        
        # Tulis Sinyal Status
        cv2.putText(annotated_frame, signal_text, (new_x_pos, START_POS[1]), FONT, FONT_SCALE, status_color, THICKNESS)

        # !!! KODE DETEKSI ORANG SELESAI DI SINI !!!
        # ----------------------------------------------------------------
        
        # 3. Encoding dan Streaming Frame
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.03) 
    
    # ... (Sisa kode cleanup) ...
    if camera:
        camera.release()
        camera = None
    print("Streaming kamera dihentikan dan dilepaskan.")

# --- ROUTE DAN RUN SERVER (TETAP SAMA) ---
@app.route('/')
def index():
    return render_template('Web Hisyam.html')

@app.route('/start_monitoring', methods=['POST'])
def start_monitoring():
    global is_camera_active, current_camera_id
    data = request.get_json(silent=True)
    if data:
        # COMMAND: Menerima ID kamera dari JavaScript dan pastikan formatnya adalah angka integer
        current_camera_id = data.get('camera_id', 0)
        # Tambahkan konversi ke integer karena cv2.VideoCapture butuh angka
        try:
            current_camera_id = int(current_camera_id)
        except ValueError:
            current_camera_id = 0 # Default ke 0 jika gagal konversi
    
    if is_camera_active:
        return jsonify({"status": "warning", "message": "Kamera sudah aktif."}), 200

    is_camera_active = True
    print(f"Perintah diterima: Mulai monitoring dengan kamera ID: {current_camera_id}")
    
    return jsonify({
        "status": "success",
        "message": "Monitoring telah dimulai."
    }), 200

@app.route('/stop_monitoring', methods=['POST'])
def stop_monitoring():
    global is_camera_active
    if not is_camera_active:
        return jsonify({"status": "warning", "message": "Kamera sudah tidak aktif."}), 200
        
    is_camera_active = False
    print("Perintah diterima: Menghentikan monitoring.")
    
    return jsonify({
        "status": "success",
        "message": "Kamera dimatikan oleh server."
    }), 200

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
