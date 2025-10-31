// ===== Alurnya itu, harus umenunggu semua elemen HTML siap diekseskusi terlebih dahul =====

// ===== GLOBAL STATE (di luar DOMContentLoaded agar bisa diakses global jika diperlukan) =====
let operatorDetected = false;
let machineRunning = false;
let runtime = 0;
let runtimeTimer = null;
let snapshotCount = 0;
// const FLASK_URL dan VIDEO_FEED_URL tidak perlu diubah
const FLASK_URL = 'http://127.0.0.1:5000';
const VIDEO_FEED_URL = FLASK_URL + '/video_feed';

// Memastikan semua kode di bawah ini berjalan setelah HTML dimuat
document.addEventListener('DOMContentLoaded', function() {
    
    // --- COMMAND: Semua DOM Elements dipindahkan ke sini ---
    const opText = document.getElementById("opText");
    const opStatus = document.getElementById("opStatus");
    const btnToggleOp = document.getElementById("btnToggleOp");
    const btnStart = document.getElementById("btnStart");
    const btnStop = document.getElementById("btnStop");
    const machineText = document.getElementById("machineText");
    const machineBox = document.getElementById("machineBox");
    const runtimeEl = document.getElementById("runtime");
    const btnEStop = document.getElementById("btnEStop");
    const estopProgress = document.getElementById("estopProgress");
    const logArea = document.getElementById("log");
    const btnClear = document.getElementById("btnClear");
    const btnExport = document.getElementById("btnExport");
    
    // Elemen Kamera Kritis (yang menyebabkan error 'null')
    const btnStartCamera = document.getElementById("btnStartCamera");
    const btnStopCamera = document.getElementById("btnStopCamera");
    const btnSnap = document.getElementById("btnSnap");
    const cameraStream = document.getElementById("cameraStream"); // Elemen IMG streaming
    const videoFallback = document.getElementById("videoFallback");
    const cameraStatus = document.getElementById("cameraStatus");
    
    // Elemen lain
    const zoomSlider = document.getElementById("zoom");
    const zoomValue = document.getElementById("zoomValue");
    const resolutionSelect = document.getElementById("resolution");
    const btnClearGallery = document.getElementById("btnClearGallery");
    const gallery = document.getElementById("gallery");
    // Karena kita memakai IMG stream dari Flask, elemen 'video' tidak lagi diperlukan.

    // ===== HELPER: ADD LOG (Harus di dalam DOMContentLoaded untuk mengakses logArea) =====
    function addLog(msg) {
        const time = new Date().toLocaleTimeString();
        const line = document.createElement("div");
        line.textContent = `[${time}] ${msg}`;
        logArea.appendChild(line);
        logArea.scrollTop = logArea.scrollHeight;
    }

    // ===== RIPPLE EFFECT (Dipindahkan ke dalam DOMContentLoaded) =====
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

    // ===== FUNGSI KONTROL STREAMING: MENGATUR TAMPILAN =====
    function setStreamActive(isActive) {
        if (isActive) {
            // Kamera Aktif: Tampilkan stream IMG, sembunyikan fallback
            cameraStream.src = VIDEO_FEED_URL; 
            cameraStream.style.display = 'block';
            videoFallback.style.display = 'none';
            cameraStatus.style.display = 'flex';
        } else {
            // Kamera Tidak Aktif: Sembunyikan stream, tampilkan fallback
            cameraStream.src = ""; // Hentikan permintaan stream
            cameraStream.style.display = 'none';
            videoFallback.style.display = 'block';
            cameraStatus.style.display = 'none';
        }
    }

    // ===== CAMERA CONTROL START (Perbaikan error 'null' telah selesai) =====
    btnStartCamera.addEventListener("click", async () => {
        // Ambil ID kamera (default 0 dulu)
        const cameraID = 3; 
        
        addLog("ℹ️ Mengirim permintaan ke server untuk menyalakan kamera...");
        
        fetch(FLASK_URL + '/start_monitoring', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ camera_id: cameraID }) 
        })
        .then(response => {
            if (!response.ok) {
                // Flask tidak merespons 200/OK (misal server mati)
                throw new Error('Gagal terhubung atau server merespons error.');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // COMMAND: Panggil fungsi setStreamActive yang menangani tampilan display
                setStreamActive(true); 
                addLog(`✅ Kamera ID ${cameraID} dinyalakan oleh server.`);
            } else {
                addLog(`⚠️ ${data.message}`); 
            }
        })
        .catch(error => {
            console.error('Terjadi masalah koneksi:', error);
            addLog("❌ Gagal memulai kamera. Pastikan server Flask berjalan.");
            alert("Tidak dapat memulai kamera: " + error.message);
            // COMMAND: Atur tampilan kembali ke fallback jika gagal
            setStreamActive(false); 
        });
    });

    // ===== CAMERA CONTROL STOP (Dimodifikasi untuk menggunakan setStreamActive) =====
    btnStopCamera.addEventListener("click", async () => {
        addLog("ℹ️ Mengirim permintaan ke server untuk mematikan kamera...");

        fetch(FLASK_URL + '/stop_monitoring', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Gagal terhubung atau server merespons error.');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // COMMAND: Panggil fungsi setStreamActive(false)
                setStreamActive(false); 
                addLog(`🛑 ${data.message}`); 
            } else {
                addLog(`⚠️ ${data.message}`); 
            }
        })
        .catch(error => {
            console.error('Terjadi masalah koneksi STOP:', error);
            addLog("❌ Gagal mengirim perintah Stop.");
            alert("Tidak dapat menghentikan kamera: " + error.message);
        });
    });

    // ===== LOGIKA SISANYA DIPINDAHKAN KE BAWAH: =====
    
    // ===== OPERATOR TOGGLE =====
    btnToggleOp.addEventListener("click", () => {
        // ... (kode tetap sama) ...
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
            if (machineRunning) {
                stopMachine();
                addLog("Mesin otomatis dimatikan karena operator tidak terdeteksi.");
            }
        }
    });

    // ===== MACHINE CONTROL FUNCTIONS (Dipindahkan ke dalam scope) =====
    function startMachine() {
        if (machineRunning) return;
        machineRunning = true;
        machineText.textContent = "MENYALA";
        machineBox.classList.add("machine-on");
        addLog("🟢 Mesin dinyalakan.");
        runtimeTimer = setInterval(() => {
            runtime++;
            runtimeEl.textContent = runtime + " s";
        }, 1000);
    }

    function stopMachine() {
        if (!machineRunning) return;
        machineRunning = false;
        machineText.textContent = "MATI";
        machineBox.classList.remove("machine-on");
        addLog("🔴 Mesin dimatikan.");
        clearInterval(runtimeTimer);
        runtimeTimer = null;
    }

    // ===== MACHINE CONTROL LISTENERS =====
    btnStart.addEventListener("click", () => {
        if (!operatorDetected) {
            addLog("⚠️ Tidak bisa menyalakan mesin. Operator tidak terdeteksi.");
            alert("Operator belum terdeteksi!");
            return;
        }
        startMachine();
    });

    btnStop.addEventListener("click", stopMachine);

    // ===== EMERGENCY STOP =====
    let holdInterval;
    btnEStop.addEventListener("mousedown", () => {
        let progress = 0;
        estopProgress.style.width = "0%";
        holdInterval = setInterval(() => {
            progress += 5;
            estopProgress.style.width = progress + "%";
            if (progress >= 100) {
                estopProgress.style.width = "100%";
                clearInterval(holdInterval);
                stopMachine();
                addLog("🚨 EMERGENCY STOP diaktifkan!");
                alert("EMERGENCY STOP AKTIF!");
            }
        }, 50);
    });
    btnEStop.addEventListener("mouseup", () => clearInterval(holdInterval));
    btnEStop.addEventListener("mouseleave", () => clearInterval(holdInterval));

    // ===== CLEAR & EXPORT LOG =====
    btnClear.addEventListener("click", () => {
        logArea.innerHTML = "";
        addLog("Log telah dikosongkan.");
    });

    btnExport.addEventListener("click", () => {
        const logs = Array.from(logArea.children).map(el => el.textContent).join("\n");
        const blob = new Blob([logs], { type: "text/plain" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "log_activity.txt";
        link.click();
        addLog("Log diekspor ke file log_activity.txt");
    });
    
    // ===== SNAPSHOT (MEMPERBAIKI ERROR 'video' not found) =====
    btnSnap.addEventListener("click", () => {
        // COMMAND: Menguji apakah stream IMG sudah aktif sebelum mengambil snapshot
        if (cameraStream.style.display !== 'block') { 
            alert("Kamera belum aktif!");
            return;
        }

        // --- COMMAND: Karena kita memakai IMG streaming, kita TIDAK BISA 
        // --- menggunakan ctx.drawImage(video, ...) secara langsung.
        // --- Jika ingin snapshot, kita harus meminta Flask mengirim frame tunggal.
        
        alert("Snapshot sementara tidak bisa dilakukan karena Anda menggunakan MJPEG streaming dari Flask. Fitur ini akan dikembangkan setelah integrasi deteksi objek selesai!");
        addLog("⚠️ Snapshot gagal. Perlu fungsi API khusus di Flask.");
    });

    // ===== ZOOM (Memperbaiki error 'video' not found) =====
    // COMMAND: Mengubah logika zoom untuk diterapkan pada elemen cameraStream (IMG)
    zoomSlider.addEventListener("input", () => {
        const zoom = zoomSlider.value / 100;
        // COMMAND: Menerapkan scale pada elemen IMG
        cameraStream.style.transform = `scale(${zoom})`;
        // COMMAND: Menerapkan transform-origin ke tengah agar zoom fokus di tengah
        cameraStream.style.transformOrigin = `center center`;
        zoomValue.textContent = `${zoomSlider.value}%`;
    });

    // ===== CLEAR GALLERY =====
    btnClearGallery.addEventListener("click", () => {
        gallery.innerHTML = `<small class="text-muted">No images captured yet</small>`;
        snapshotCount = 0;
        addLog("🗑️ Semua snapshot dihapus.");
    });
    
    // COMMAND: Panggil fungsi setStreamActive di awal untuk memastikan tampilan fallback benar
    setStreamActive(false);

}); // Akhir dari DOMContentLoaded
