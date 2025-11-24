// ===== GLOBAL STATE =====
let operatorDetected = false;
let machineRunning = false;
let runtime = 0;
let runtimeTimer = null;
let snapshotCount = 0;

const FLASK_URL = ''; 
const VIDEO_FEED_URL = FLASK_URL + '/video_feed';

// ====================================================================
// FUNGSI KONTROL MESIN (PLC) - (GLOBAL SCOPE)
// Fungsi ini dipanggil oleh 'onclick' di file index.html
// ====================================================================
function kirimPerintah(perintah) {
    
    // 1. Ambil elemen <p> untuk menampilkan status
    var statusElem = document.getElementById('status');
    if (statusElem) {
      statusElem.innerHTML = "Status: Mengirim " + perintah + "...";
    }
    
    // 2. Menggunakan 'fetch' untuk mengirim request ke server FLASK
    fetch(perintah) // (misal: memanggil http://IP_LAPTOP:5000/start)
        
        // 3. Ubah balasan dari Flask menjadi format JSON
        .then(response => {
          if (!response.ok) {
            throw new Error('Server Flask merespons error!');
          }
          return response.json(); 
        })
        
        // 4. Ambil data JSON (misal: data.message) dan tampilkan
        .then(data => {
          if (statusElem) {
            statusElem.innerHTML = "Status: " + data.message;
          }
        })
        
        // 5. Tangani jika koneksi ke Flask gagal total
        .catch(error => {
          console.error('Error:', error);
          if (statusElem) {
            statusElem.innerHTML = "Status: Error! Gagal terhubung ke Server Flask.";
          }
        });
}

// ====================================================================
// FUNGSI BACA STATUS PLC (POLLING) - (GLOBAL SCOPE)
// ====================================================================
function updatePLCStatus() {
      fetch('/get-plc-status') // Memanggil route baru di Flask
        .then(response => {
            if (!response.ok) { throw new Error('Respon server tidak OK'); }
            return response.json();
        })
        .then(data => {
          // Ambil elemen display status (Pastikan ada <strong id="plc-status-display"> di HTML-mu)
          const statusDisplay = document.getElementById('plc-status-display');
          
          if (statusDisplay) {
              if (data.status === "ON") {
                statusDisplay.innerHTML = "ON";
                statusDisplay.style.color = "lime"; // Hijau
              } else if (data.status === "OFF") {
                statusDisplay.innerHTML = "OFF";
                statusDisplay.style.color = "red"; // Merah
              } else {
                // Jika Modbus gagal (Timeout)
                statusDisplay.innerHTML = "ERROR";
                statusDisplay.style.color = "orange";
              }
          }
        })
        .catch(error => {
          // Jika Flask gagal total
          const statusDisplay = document.getElementById('plc-status-display');
          if (statusDisplay) {
              statusDisplay.innerHTML = "DISCONNECTED";
              statusDisplay.style.color = "grey";
          }
        });
}


// ====================================================================
// KODE UTAMA (Berjalan setelah HTML dimuat)
// ====================================================================
document.addEventListener('DOMContentLoaded', function() {
    
    // --- Elemen DOM yang Masih Dipakai ---
    // (Variabel ini HANYA bisa diakses di dalam DOMContentLoaded)
    const opText = document.getElementById("opText");
    const opStatus = document.getElementById("opStatus");
    const btnToggleOp = document.getElementById("btnToggleOp");
    const logArea = document.getElementById("log");
    const btnClear = document.getElementById("btnClear");
    const btnExport = document.getElementById("btnExport");
    
    // Elemen Kamera
    const btnStartCamera = document.getElementById("btnStartCamera");
    const btnStopCamera = document.getElementById("btnStopCamera");
    const btnSnap = document.getElementById("btnSnap");
    const cameraStream = document.getElementById("cameraStream"); 
    const videoFallback = document.getElementById("videoFallback");
    const cameraStatus = document.getElementById("cameraStatus");
    
    // Elemen Lain
    const zoomSlider = document.getElementById("zoom");
    const zoomValue = document.getElementById("zoomValue");
    const resolutionSelect = document.getElementById("resolution");
    const btnClearGallery = document.getElementById("btnClearGallery");
    const gallery = document.getElementById("gallery");

    // --- KODE LAMA YANG MENYEBABKAN CRASH SUDAH DIHAPUS ---

    // ===== HELPER: ADD LOG =====
    function addLog(msg) {
        if (!logArea) return; // Cek jika logArea ada
        const time = new Date().toLocaleTimeString();
        const line = document.createElement("div");
        line.textContent = `[${time}] ${msg}`;
        logArea.appendChild(line);
        logArea.scrollTop = logArea.scrollHeight;
    }

    // ===== RIPPLE EFFECT =====
    document.querySelectorAll(".btn-ripple").forEach(btn => {
        btn.addEventListener("click", function (e) {
            const circle = document.createElement("span");
            const diameter = Math.max(this.clientWidth, this.clientHeight);
            const rect = this.getBoundingClientRect();
            circle.style.width = circle.style.height = `${diameter}px`;
            circle.style.left = `${e.clientX - rect.left - diameter / 2}px`;
            circle.style.top = `${e.clientY - rect.top - diameter / 2}px`;
            circle.classList.add("ripple");
            const ripple = this.getElementsByClassName("ripple")[0];
            if (ripple) ripple.remove();
            this.appendChild(circle);
        });
    });

    // ===== FUNGSI KONTROL STREAMING =====
    function setStreamActive(isActive) {
        if (!cameraStream || !videoFallback || !cameraStatus) return; // Cek
        if (isActive) {
            cameraStream.src = VIDEO_FEED_URL; 
            cameraStream.style.display = 'block';
            videoFallback.style.display = 'none';
            cameraStatus.style.display = 'flex';
        } else {
            cameraStream.src = ""; 
            cameraStream.style.display = 'none';
            videoFallback.style.display = 'block';
            cameraStatus.style.display = 'none';
        }
    }

    // ===== CAMERA CONTROL (START/STOP) ===== 
    if(btnStartCamera) {
        btnStartCamera.addEventListener("click", async () => {
            const cameraID = 0; 
            addLog("ℹ️ Mengirim permintaan ke server untuk menyalakan kamera...");
            fetch('/start_monitoring', { // Menggunakan relative path
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ camera_id: cameraID }) 
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    setStreamActive(true); 
                    addLog(`✅ Kamera ID ${cameraID} dinyalakan oleh server.`);
                } else {
                    addLog(`⚠️ ${data.message}`); 
                }
            })
            .catch(error => {
                addLog("❌ Gagal memulai kamera. Pastikan server Flask berjalan.");
                setStreamActive(false); 
            });
        });
    }

    if(btnStopCamera) {
        btnStopCamera.addEventListener("click", async () => {
            addLog("ℹ️ Mengirim permintaan ke server untuk mematikan kamera...");
            fetch('/stop_monitoring', { // Menggunakan relative path
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    setStreamActive(false); 
                    addLog(`🛑 ${data.message}`); 
                } else {
                    addLog(`⚠️ ${data.message}`); 
                }
            })
            .catch(error => {
             addLog(" Gagal mengirim perintah Stop.");
               });
     });
    }


//  Event untuk merubah status OPERATOR berdasar wajah yg dibaca

function updateOperatorStatus(isDetected, name = "") {
    // Ambil elemen-elemen HTML
    const opText = document.getElementById("opText");
    const opName = document.getElementById("opName"); // Elemen nama yang baru kita buat
    const opStatus = document.getElementById("opStatus");

    if (isDetected) {
        // --- KONDISI: WAJAH TERDETEKSI ---
        
        // 1. Ubah Teks Status Utama
        opText.textContent = "DETECTED";
        opText.style.color = "var(--success)"; // Hijau (pastikan variabel CSS ada, atau pakai '#198754')

        // 2. Tampilkan Nama Operator
        // Kita ubah jadi huruf besar semua biar keren
        opName.textContent = name.toUpperCase(); 
        opName.style.display = "block"; // MUNCULKAN nama (sebelumnya none)

        // 3. Ubah Warna Kotak Background jadi Hijau (Aman)
        opStatus.classList.remove("op-bad"); 
        opStatus.classList.add("op-ok"); 
        
        // Tambahan visual: Border hijau biar makin jelas
        opStatus.style.border = "1px solid var(--success)"; 

    } else {
        // --- KONDISI: TIDAK ADA WAJAH ---
        
        // 1. Ubah Teks Status Utama
        opText.textContent = "NOT DETECTED";
        opText.style.color = "var(--danger)"; // Merah

        // 2. Sembunyikan Nama Operator
        opName.style.display = "none"; // HILANGKAN nama

        // 3. Ubah Warna Kotak Background jadi Merah (Bahaya)
        opStatus.classList.remove("op-ok");
        opStatus.classList.add("op-bad");
        
        // Tambahan visual: Border merah
        opStatus.style.border = "1px solid var(--danger)";
    }
}

// Event untuk menanyakan status OPERATOR pada Flask
async function pollOperatorStatus() {
    try {
        // Panggil endpoint Flask (pastikan endpoint ini nanti dibuat di Python)
        const response = await fetch(FLASK_URL + '/status_operator');
        const data = await response.json(); 

        // Asumsi data dari Flask nanti bentuknya:
        // { "detected": true, "name": "Roland" }

        if (data.detected) {
            // Jika terdeteksi, panggil fungsi update dengan TRUE dan NAMANYA
            updateOperatorStatus(true, data.name);
        } else {
            // Jika tidak, panggil fungsi update dengan FALSE
            updateOperatorStatus(false);
        }

    } catch (error) {
        // Kalau error koneksi, anggap tidak terdeteksi
        // console.error("Gagal polling status:", error);
        updateOperatorStatus(false);
    }
}

// Jalankan polling setiap 1000ms (1 detik)
setInterval(pollOperatorStatus, 1000);



    // ===== OPERATOR TOGGLE =====
    if(btnToggleOp) { 
      btnToggleOp.addEventListener("click", () => {
          operatorDetected = !operatorDetected;
          if (operatorDetected) {
              opStatus.classList.remove("op-bad");
              opStatus.classList.add("op-ok");
              opText.textContent = "TERDETEKSI";
              addLog("Operator terdeteksi di area kerja.");
          } else {
              opStatus.classList.remove("op-ok");
              opStatus.classList.add("op-bad");
              opText.textContent = "TIDAK TERDETEKSI";
              addLog("Operator meninggalkan area kerja!");
          }
      });
    }

    // ===== CLEAR & EXPORT LOG =====
    if(btnClear) {
        btnClear.addEventListener("click", () => {
            logArea.innerHTML = "";
            addLog("Log telah dikosongkan.");
        });
    }
    
    if(btnExport) {
        btnExport.addEventListener("click", () => {
            const logs = Array.from(logArea.children).map(el => el.textContent).join("\n");
            const blob = new Blob([logs], { type: "text/plain" });
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = "log_activity.txt";
            link.click();
            addLog("Log diekspor ke file log_activity.txt");
        });
    }




    
    setStreamActive(false);

    // --- KODE LAMA (Button Warna) SUDAH DIHAPUS ---
    // (Fungsi handleDetentClick dihapus karena 'onclick' di HTML sudah cukup)
    
    // --- MEMULAI POLLING STATUS PLC ---
    // Panggil fungsi updatePLCStatus() setiap 0.2 detik
    setInterval(updatePLCStatus, 700); 
    // Panggil sekali saat halaman dimuat
    updatePLCStatus();


const controlButtons = document.querySelectorAll('.control-grid-wrapper button');

// Definisi Fungsi yang Akan Dijalankan Saat Diklik
function handleDetentClick (event) {
    const clickedButton = event.currentTarget;
    
    // a. Hapus status 'is-active' dari semua tombol yang lain
    controlButtons.forEach(button => {
        button.classList.remove('is-active');
    });
    // b. Aktifkan status 'is-active' pada tombol yang baru diklik
    clickedButton.classList.add('is-active');
    // c. Log untuk debugging
    console.log(`Tombol ${clickedButton.textContent} ditekan dan statusnya tertahan.`);
        // d. Panggil fungsi pengiriman sinyal Modbus ke Flask (Langkah selanjutnya)
     kirimPerintah(clickedButton.textContent.toLowerCase());
}

//  DAFTARKAN EVENT LISTENER
controlButtons.forEach(button => {
    button.addEventListener('click', handleDetentClick);
});


}); // Akhir dari DOMContentLoaded