import cv2
from ultralytics import YOLO 

# --- PENGATURAN MODEL & KAMERA ---

# PATH MODEL: Pastikan 'best.pt' ada di folder yang sama
MODEL_PATH = 'best.pt' 

# KAMERA ID: Webcam eksternal berada di no 1 
WEBCAM_ID = 3

# AMBANG BATAS SINYAL: Hanya confidence > 0.90 yang akan dianggap TRUE
CONFIDENCE_THRESHOLD_SIGNAL = 0.90 

# AMBANG BATAS DISPLAY: Deteksi apa saja yang ditampilkan di layar (misalnya 0.50)
CONFIDENCE_THRESHOLD_DISPLAY = 0.50 

# DAFTAR KELAS: Hanya satu kelas 'human'
CLASS_LABELS = ['human'] 


# --- INISIALISASI ---

try:
    model = YOLO(MODEL_PATH)
    print(f"Model YOLO {MODEL_PATH} berhasil dimuat!")
except Exception as e:
    print(f"ERROR: Gagal memuat model. Pastikan path benar. {e}")
    exit()

cap = cv2.VideoCapture(WEBCAM_ID) 

if not cap.isOpened():
    print("ERROR: Gagal mengakses kamera.")
    exit()

print("\n--- Mulai Real-time Object Detection ---")
print("Tekan 'q' untuk keluar.")


# --- LOOP UTAMA REAL-TIME ---

while True:
    ret, frame = cap.read()
    if not ret:
        print("Gagal menerima frame. Exiting ...")
        break

    # 1. RESET Sinyal dan Lakukan Prediksi
    signal_status = 0 # 0 = FALSE
    
    # model.predict hanya menampilkan deteksi >= CONFIDENCE_THRESHOLD_DISPLAY
    # Pastikan conf di sini cukup rendah agar banyak bounding box terlihat untuk analisis
    results = model.predict(
        frame, 
        conf=CONFIDENCE_THRESHOLD_DISPLAY, 
        verbose=False, 
        classes=[0],
        stream=True
    ) 

    # --- START OF CHANGE ---
    # Kita perlu mengambil frame yang sudah di-plot oleh YOLO.
    # r.plot() akan menggambar bounding box, label, dan confidence.
    # Jika tidak ada deteksi, ini akan mengembalikan frame asli.
    annotated_frame = frame.copy() # Mulai dengan frame asli

    # Loop hasil untuk mencari deteksi yang SANGAT YAKIN untuk sinyal
    for r in results:
        # PENTING: Lakukan r.plot() di sini untuk menggambar bounding box
        # dan simpan ke annotated_frame. Jika tidak ada deteksi, r.plot() akan mengembalikan frame asli.
        annotated_frame = r.plot() # Ini yang akan menampilkan bounding box!

        # Loop semua bounding box yang ditemukan oleh YOLO untuk mengecek ambang batas sinyal
        for box in r.boxes:
            confidence = box.conf.item() 
            
            if confidence >= CONFIDENCE_THRESHOLD_SIGNAL:
                signal_status = 1 # 1 = TRUE
                break # Hentikan looping box karena sudah ketemu 1 yang memenuhi syarat
        
        if signal_status == 1:
            break # Hentikan looping r (results)
    # --- END OF CHANGE ---
            
    # 3. Visualisasi Sinyal dan Deteksi di Frame

    # Tentukan teks status sinyal
    signal_text = "TRUE" if signal_status == 1 else "FALSE"
    
    # Teks dasar (Human Detection : )
    base_text = "Human Detection : "
    
    # Warna dasar: Putih (RBG: 255, 255, 255)
    COLOR_WHITE = (255, 255, 255) 
    
    # Warna yang berubah: Hijau (TRUE) atau Merah (FALSE)
    COLOR_TRUE = (0, 255, 0)   # Hijau
    COLOR_FALSE = (0, 0, 255)  # Merah
    status_color = COLOR_TRUE if signal_status == 1 else COLOR_FALSE
    
    # Font dan Posisi Dasar
    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_SCALE = 1
    THICKNESS = 2
    START_POS = (10, 30)
    
    # --- TULISAN PERTAMA (BASIC TEXT - WARNA PUTIH) ---
    cv2.putText(
        annotated_frame, 
        base_text, 
        START_POS, 
        FONT, 
        FONT_SCALE, 
        COLOR_WHITE, 
        THICKNESS
    )

    # --- TULISAN KEDUA (TRUE/FALSE - WARNA BERUBAH) ---
    
    # Hitung posisi X baru agar tulisan TRUE/FALSE muncul setelah "Human Detection : "
    (text_width, text_height), baseline = cv2.getTextSize(
        base_text, 
        FONT, 
        FONT_SCALE, 
        THICKNESS
    )
    
    new_x_pos = START_POS[0] + text_width
    
    cv2.putText(
        annotated_frame, 
        signal_text, 
        (new_x_pos, START_POS[1]), 
        FONT, 
        FONT_SCALE, 
        status_color, 
        THICKNESS
    )

    # Tampilkan Frame
    cv2.imshow('YOLO Real-Time Human Detection Monitor', annotated_frame)

    # 4. Keluar dari Loop
    if cv2.waitKey(1) == ord('q'):
        break

# --- CLEANUP ---
cap.release()
cv2.destroyAllWindows()
print("\nProgram selesai.")