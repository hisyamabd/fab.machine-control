from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import cv2 
import time
import face_recognition # COMMAND: Impor library Face Recognition (BARU)
import pickle           # COMMAND: Impor library Pickle untuk load database (BARU)
import serial
import numpy as np      # COMMAND: Impor Numpy (Biasanya dibutuhkan opencv/face_rec)

# --- INISIALISASI GLOBAL (HANYA SEKALI SAAT SERVER START) ---
# COMMAND: Bagian ini BARU. Memuat database wajah saat server mulai.
try:
    # Membuka file database wajah yang sudah dilatih
    with open("encodings.pickle", "rb") as f:
        database = pickle.load(f)
        print("✅ Database 'encodings.pickle' berhasil dimuat!") 
except FileNotFoundError:
    print("❌ FATAL ERROR: 'encodings.pickle' tidak ditemukan. Jalankan pendaftaran wajah dulu.")
    database = None # Server tetap jalan, tapi deteksi wajah akan gagal

# COMMAND: Konfigurasi parameter Face Recognition (BARU)
TOLERANSI_JARAK = 0.4  # Semakin kecil semakin ketat (akurat tapi sulit detect)
PROSES_SETIAP_N_FRAME = 5 # Proses 1 frame setiap 5 frame (Agar tidak lag)
scale_factor = 0.5 # Perkecil frame untuk mempercepat proses

# COMMAND: Variabel state untuk menyimpan hasil deteksi terakhir (Agar video smooth)
kotak_wajah_terakhir = []
labels_terakhir = []
frame_counter = 0
# --- AKHIR PERUBAHAN GLOBAL ---


# --- VARIABEL GLOBAL KONTROL FLASK (TIDAK DIUBAH) ---
app = Flask(__name__)
CORS(app) 
is_camera_active = False 
current_camera_id = 0     
camera = None       

ESP32_PORT = 'COM9' 

# COMMAND: Variabel Global untuk status Operator (BARU)
# Ini akan dibaca oleh route '/status_operator'
current_operator_status = {
    "detected": False,
    "name": ""
}


try:
    # Baud rate (115200) harus SAMA dengan Serial.begin() di kode ESP32-mu
    esp32_gateway = serial.Serial(port=ESP32_PORT, baudrate=115200, timeout=.1) 
    print(f"Berhasil terhubung ke ESP32 Gateway di {ESP32_PORT}")
except Exception as e:
    print(f"GAGAL terhubung ke ESP32 Gateway: {e}")
    print("Pastikan ESP32 tercolok dan TIDAK dibuka di Serial Monitor lain.")
    esp32_gateway = None


# ====================================================================
# FUNGSI UTAMA: PEMROSESAN FRAME DAN STREAMING
# ====================================================================

def generate_frames():
    # COMMAND: Panggil variabel global yang dibutuhkan (DITAMBAHKAN)
    global is_camera_active, camera, current_camera_id
    global kotak_wajah_terakhir, labels_terakhir, frame_counter, current_operator_status
    
    # Inisialisasi kamera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(int(current_camera_id), cv2.CAP_DSHOW)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not camera.isOpened():
            is_camera_active = False 
            print(f"ERROR: Gagal membuka kamera dengan ID {current_camera_id}.")
            return

    while is_camera_active:
        success, frame = camera.read() 
        if not success:
            print("Gagal membaca frame, menghentikan stream.")
            is_camera_active = False
            break
        
        # --- COMMAND: LOGIKA FACE RECOGNITION DIMULAI DI SINI ---
        
        # 1. Optimasi: Hanya proses deteksi berat setiap N frame
        if frame_counter % PROSES_SETIAP_N_FRAME == 0:
            
            # Perkecil frame untuk mempercepat deteksi
            frame_kecil = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
            # Ubah BGR (OpenCV) ke RGB (Face_Recognition)
            frame_rgb = cv2.cvtColor(frame_kecil, cv2.COLOR_BGR2RGB)

            # Deteksi Lokasi Wajah
            kotak_wajah_terakhir = face_recognition.face_locations(frame_rgb, model='hog')
            # Ekstraksi Fitur Wajah (Encoding)
            encodings_live_terakhir = face_recognition.face_encodings(frame_rgb, kotak_wajah_terakhir)
            
            labels_terakhir = [] # Reset label
            nama_terdeteksi_saat_ini = "" # Reset nama
            status_deteksi_saat_ini = False

            if database is not None:
                for encoding_live in encodings_live_terakhir:
                    # Bandingkan wajah di kamera dengan database
                    matches = face_recognition.compare_faces(database["encodings"], encoding_live, tolerance=TOLERANSI_JARAK)
                    label = "Tidak Dikenali"
                    

                    if True in matches:
                        # Jika ada yang cocok, cari nama terbanyak (voting)
                        matched_idxs = [i for (i, b) in enumerate(matches) if b]
                        counts = {}
                        for i in matched_idxs:
                            nama = database["names"][i]
                            counts[nama] = counts.get(nama, 0) + 1
                        label = max(counts, key=counts.get)
                        
                        # Set status detected
                        nama_terdeteksi_saat_ini = label
                        status_deteksi_saat_ini = True
                    
                    labels_terakhir.append(label)
            else:
                labels_terakhir = ["DB ERROR"] * len(kotak_wajah_terakhir)
            
            # COMMAND: UPDATE STATUS GLOBAL (Agar bisa dibaca route /status_operator)
            if status_deteksi_saat_ini:
                current_operator_status["detected"] = True
                current_operator_status["name"] = nama_terdeteksi_saat_ini
            else:
                # Jika tidak ada wajah atau Unknown, set ke False
                # (Kecuali jika ada logika timeout, tapi ini sederhana dulu)
                if not labels_terakhir: # Jika list kosong (tidak ada wajah sama sekali)
                     current_operator_status["detected"] = False
                     current_operator_status["name"] = ""
                # Jika ada wajah tapi Unknown, biarkan detected=False atau True tergantung kebutuhanmu
                # Di sini kita anggap Unknown = Not Detected (Operator Sah)
                elif "Tidak Dikenali" in labels_terakhir:
                     current_operator_status["detected"] = False
                     current_operator_status["name"] = ""

        
        frame_counter += 1

        # 2. Menggambar Kotak dan Nama di Frame (Visualisasi)
        for (top, right, bottom, left), label in zip(kotak_wajah_terakhir, labels_terakhir):
            # Kembalikan koordinat ke ukuran asli
            top = int(top * (1/scale_factor))
            right = int(right * (1/scale_factor))
            bottom = int(bottom * (1/scale_factor))
            left = int(left * (1/scale_factor))

            # Tentukan warna kotak
            if label == "Tidak Dikenali" or label == "DB ERROR":
                warna_kotak = (0, 0, 255) # Merah
            else:
                warna_kotak = (0, 255, 0) # Hijau (Dikenali)

            # Gambar Kotak
            cv2.rectangle(frame, (left, top), (right, bottom), warna_kotak, 2)

            # Gambar Label Nama
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), warna_kotak, cv2.FILLED)
            cv2.putText(frame, label, (left + 6, bottom - 6), font, 1, (255, 255, 255), 2)
        
        # --- COMMAND: AKHIR LOGIKA FACE RECOGNITION ---

        # Encoding frame untuk streaming
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
    if camera:
        camera.release()
        camera = None
    print("Streaming kamera dihentikan dan dilepaskan.")
    
    # COMMAND: Reset state saat kamera mati
    kotak_wajah_terakhir = []
    labels_terakhir = []
    frame_counter = 0
    current_operator_status["detected"] = False
    current_operator_status["name"] = ""


# --- ROUTE DAN RUN SERVER ---

@app.route('/')
def index():
    return render_template('Web Hisyam.html')

# ... (Route start_monitoring, stop_monitoring, video_feed TETAP SAMA) ...

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


# --- COMMAND: ROUTE BARU UNTUK POLLING STATUS OPERATOR ---
@app.route('/status_operator', methods=['GET'])
def status_operator():
    # Mengembalikan JSON berisi status deteksi (True/False) dan Nama
    return jsonify(current_operator_status)
# ---------------------------------------------------------


@app.route('/start')
def start_mesin():
    if esp32_gateway:
        try:
            esp32_gateway.write(b'1') 
            print("Perintah '1' (START) terkirim ke ESP32.")
            return jsonify(message="OK! Perintah START terkirim ke PLC.")
        except Exception as e:
            print(f"Gagal mengirim ke ESP32: {e}")
            return jsonify(message="Error! Gagal mengirim perintah ke ESP32."), 500
    else:
        return jsonify(message="Error! ESP32 Gateway tidak terhubung."), 500

@app.route('/stop')
def stop_mesin():
    if esp32_gateway:
        esp32_gateway.write(b'0') 
        print("Perintah '0' (STOP) terkirim ke ESP32.")
        return jsonify(message="OK! Perintah STOP terkirim ke PLC.")
    else:
        return jsonify(message="Error! ESP32 Gateway tidak terhubung."), 500

@app.route('/emergency')
def emergency_stop():
    if esp32_gateway:
        esp32_gateway.write(b'E') 
        print("Perintah 'E' (EMERGENCY) terkirim ke ESP32.")
        return jsonify(message="OK! Perintah EMERGENCY terkirim ke PLC.") 
    else:
        return jsonify(message="Error! ESP32 Gateway tidak terhubung."), 500
    

@app.route('/get-plc-status')
def get_plc_status():
    if esp32_gateway:
        try:
            esp32_gateway.flushInput()
            esp32_gateway.flushOutput()
            esp32_gateway.write(b'R')
            time.sleep (0.5)
            response = esp32_gateway.read(1) 
            
            if response == b'1':
                return jsonify(status="ON", message="PLC M95 sedang ON.")
            elif response == b'0':
                return jsonify(status="OFF", message="PLC M95 sedang OFF.")
            else:
                return jsonify(status="ERROR", message="Gagal membaca Modbus (Timeout)."), 500

        except Exception as e:
            print(f"Gagal membaca dari ESP32: {e}")
            return jsonify(status="ERROR", message="Gagal membaca (ESP32 Error)."), 500

    else:
        return jsonify(message="Error! ESP32 Gateway tidak terhubung."), 500






if __name__ == '__main__':
    # COMMAND: Pastikan 'use_reloader=False' jika pakai webcam agar tidak crash/double load
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)