from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import cv2 
import time
import face_recognition # COMMAND: Impor library baru
import pickle           # COMMAND: Impor library baru

# COMMAND: HAPUS 'from ultralytics import YOLO'
# COMMAND: HAPUS 'MODEL_PATH = 'best.pt''
# COMMAND: HAPUS 'CONFIDENCE_THRESHOLD...' (Ini punya YOLO, tidak dipakai)

# --- COMMAND: "OTAK" BARU DIMUAT DI SINI ---
# --- INISIALISASI GLOBAL (HANYA SEKALI SAAT SERVER START) ---
try:
    # COMMAND: Perbaiki typo 'encoding.pickles' -> 'encodings.pickle'
    with open("encodings.pickle", "rb") as f:
        database = pickle.load(f)
        # COMMAND: Perbaiki typo 'Dataabse' dan tanda kutip
        print("Database 'encodings.pickle' berhasil dimuat!") 
except FileNotFoundError:
    # COMMAND: Perbaiki typo 'FATAL EROR' dan tanda kutip
    print("FATAL ERROR: 'encodings.pickle' tidak ditemukan. Jalankan pendaftaran dulu.")
    database = None # Tetap lanjutkan server, tapi deteksi akan gagal

# COMMAND: Tambahkan variabel global untuk "Otak" Face Rec
TOLERANSI_JARAK = 0.4
PROSES_SETIAP_N_FRAME = 10
scale_factor = 0.5 # Kita buat jadi global agar konsisten

# COMMAND: Tambahkan variabel state (penyimpanan) untuk Face Rec
# Ini akan menyimpan hasil terakhir agar video tetap smooth
kotak_wajah_terakhir = []
labels_terakhir = []
frame_counter = 0
# --- AKHIR PERUBAHAN GLOBAL ---


# --- VARIABEL GLOBAL KONTROL FLASK ---
# COMMAND: Ini semua (logika remote control) sudah benar, TIDAK DIUBAH
app = Flask(__name__)
CORS(app) 
is_camera_active = False 
current_camera_id = 0     
camera = None       

# ====================================================================
# FUNGSI UTAMA: PEMROSESAN FRAME DAN STREAMING
# ====================================================================

def generate_frames():
    # COMMAND: Panggil variabel global yang kita butuhkan
    global is_camera_active, camera, current_camera_id
    # COMMAND: Panggil juga variabel state Face Rec
    global kotak_wajah_terakhir, labels_terakhir, frame_counter
    
    # Inisialisasi kamera (Logika ini sudah benar, TIDAK DIUBAH)
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(int(current_camera_id), cv2.CAP_DSHOW)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not camera.isOpened():
            is_camera_active = False 
            print(f"ERROR: Gagal membuka kamera dengan ID {current_camera_id}.")
            return

    # Looping untuk membaca frame kamera selama is_camera_active = True
    # (Logika ini sudah benar, TIDAK DIUBAH)
    while is_camera_active:
        success, frame = camera.read() 
        if not success:
            print("Gagal membaca frame, menghentikan stream.")
            is_camera_active = False
            break
        
        # --- COMMAND: "OPERASI GANTI JANTUNG" DIMULAI DI SINI ---
        # --- Hapus semua logika YOLO yang lama (mulai dari 'signal_status' sampai 'r.plot()') ---
        # --- Ganti dengan logika Face Recognition ---

        # 1. Logika Frame Skipping (diambil dari live_test_wajah.py)
        if frame_counter % PROSES_SETIAP_N_FRAME == 0:
            # Lakukan proses berat (Deteksi & Ekstraksi)
            frame_kecil = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
            frame_rgb = cv2.cvtColor(frame_kecil, cv2.COLOR_BGR2RGB)

            kotak_wajah_terakhir = face_recognition.face_locations(frame_rgb, model='hog')
            encodings_live_terakhir = face_recognition.face_encodings(frame_rgb, kotak_wajah_terakhir)
            
            labels_terakhir = [] # Kosongkan list label setiap kali proses
            # Pastikan database 'encodings.pickle' sudah ter-load
            if database is not None:
                for encoding_live in encodings_live_terakhir:
                    matches = face_recognition.compare_faces(database["encodings"], encoding_live, tolerance=TOLERANSI_JARAK)
                    label = "wajah tidak dikenali"

                    if True in matches:
                        matched_idxs = [i for (i, b) in enumerate(matches) if b]
                        counts = {}
                        for i in matched_idxs:
                            nama = database["names"][i]
                            counts[nama] = counts.get(nama, 0) + 1
                        label = max(counts, key=counts.get)
                    
                    labels_terakhir.append(label)
            else:
                # Jika database gagal load, beri label error
                labels_terakhir = ["DB ERROR"] * len(kotak_wajah_terakhir)
        
        # Tambah penghitung frame (di luar 'if' agar tetap menghitung)
        frame_counter += 1

        # 2. Logika Penggambaran (diambil dari live_test_wajah.py)
        # Ini berjalan di SETIAP frame, jadi video tetap smooth
        for (top, right, bottom, left), label in zip(kotak_wajah_terakhir, labels_terakhir):
            
            if label == "wajah tidak dikenali" or label == "DB ERROR":
                warna_kotak = (0, 0, 255) # Merah
            else:
                warna_kotak = (0, 255, 0) # Hijau
                
            # Kembalikan ukuran kotak ke frame asli
            top = int(top * (1/scale_factor))
            right = int(right * (1/scale_factor))
            bottom = int(bottom * (1/scale_factor))
            left = int(left * (1/scale_factor))

            # Gambar kotak
            cv2.rectangle(frame, (left, top), (right, bottom), warna_kotak, 2)

            # Logika teks (sudah benar)
            font = cv2.FONT_HERSHEY_DUPLEX
            font_scale = 1.0 
            font_thickness = 2
            (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
            text_box_top = bottom - text_height - baseline - 10 
            text_box_bottom = bottom 
            text_box_left = left 
            text_box_right = left + text_width + 10 
                      
            cv2.rectangle(frame, (text_box_left, text_box_top), (text_box_right, text_box_bottom), warna_kotak, cv2.FILLED)
            cv2.putText(frame, label, (left + 5, bottom - baseline - 5), font, font_scale, (255, 255, 255), font_thickness)

        # --- "OPERASI GANTI JANTUNG" SELESAI DI SINI ---
        # -----------------------------------------------------
        
        # 3. Encoding dan Streaming Frame
        # COMMAND: Pastikan variabelnya 'frame', bukan 'annotated_frame' (karena kita menggambar di 'frame')
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # COMMAND: HAPUS 'time.sleep(0.03)' jika ada. Logika 'PROSES_SETIAP_N_FRAME' sudah cukup
        
    # ... (Sisa kode cleanup) ...
    if camera:
        camera.release()
        camera = None
    print("Streaming kamera dihentikan dan dilepaskan.")
    # COMMAND: Reset variabel state saat kamera stop
    kotak_wajah_terakhir = []
    labels_terakhir = []
    frame_counter = 0

# --- ROUTE DAN RUN SERVER (TETAP SAMA) ---
# COMMAND: SEMUA KODE DI BAWAH INI TIDAK PERLU DIUBAH
# Ini adalah "Remote Control" dan "Layar TV" Anda.
# Mereka tidak peduli isi siarannya (YOLO atau Face Rec).
@app.route('/')
def index():
    # COMMAND: Pastikan 'Web Hisyam.html' ada di folder 'templates'
    return render_template('Web Hisyam.html')

@app.route('/start_monitoring', methods=['POST'])
def start_monitoring():
    global is_camera_active, current_camera_id
    data = request.get_json(silent=True)
    if data:
        current_camera_id = data.get('camera_id', 0)
        try:
            current_camera_id = int(current_camera_id)
        except ValueError:
            current_camera_id = 0
    
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