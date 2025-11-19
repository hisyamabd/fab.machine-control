// static/js/main.js
// =======================================
// Konfigurasi dasar
// =======================================
const FLASK_URL = window.location.origin;  // otomatis ikut http://127.0.0.1:5000

// STATE APLIKASI
let isMonitoring = false;
let operatorDetected = false;
let operatorStatusInterval = null;
let cameraActive = false;
let machineRunning = false;

// =======================================
// Utility: Activity Log
// =======================================
function addLog(message) {
    const logEl = document.getElementById("logOutput");
    const now = new Date();
    const timeStr = now.toLocaleTimeString("id-ID", { hour12: false });
    const finalMsg = `[${timeStr}] ${message}`;

    console.log(finalMsg);

    if (!logEl) return; // kalau elemen log belum ada, jangan error
    // tampilkan log terbaru di atas
    logEl.textContent = finalMsg + "\n" + logEl.textContent;
}

// =======================================
// Kontrol Mesin (opsional, sesuaikan dengan backend Flask Anda)
// =======================================
function setMachineStateUI(running) {
    machineRunning = running;

    const indicator = document.getElementById("machineIndicator");
    if (indicator) {
        indicator.textContent = running ? "MESIN: BERJALAN" : "MESIN: MATI";
        indicator.classList.toggle("running", running);
        indicator.classList.toggle("stopped", !running);
    }

    const btnStart = document.getElementById("btnStartMachine");
    const btnStop  = document.getElementById("btnStopMachine");
    if (btnStart) btnStart.disabled = running;
    if (btnStop)  btnStop.disabled  = !running;
}

function startMachine() {
    fetch(FLASK_URL + "/start_machine", { method: "POST" })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                setMachineStateUI(true);
                addLog("✅ Mesin berhasil dinyalkan");
            } else {
                addLog("❌ Gagal menyalakan mesin");
            }
        })
        .catch(err => {
            console.error(err);
            addLog("❌ Error saat menyalakan mesin");
        });
}

function stopMachine() {
    fetch(FLASK_URL + "/stop_machine", { method: "POST" })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                setMachineStateUI(false);
                addLog("⏹️ Mesin berhasil dimatikan");
            } else {
                addLog("❌ Gagal mematikan mesin");
            }
        })
        .catch(err => {
            console.error(err);
            addLog("❌ Error saat mematikan mesin");
        });
}

// =======================================
// Kontrol Kamera
// =======================================
function setCameraUI(active) {
    cameraActive = active;

    const btnStart = document.getElementById("btnStartCamera");
    const btnStop  = document.getElementById("btnStopCamera");
    if (btnStart) btnStart.disabled = active;
    if (btnStop)  btnStop.disabled  = !active;

    const statusChip = document.getElementById("camStatus");
    if (statusChip) {
        statusChip.textContent = active ? "KAMERA: AKTIF" : "KAMERA: MATI";
        statusChip.classList.toggle("active", active);
        statusChip.classList.toggle("inactive", !active);
    }
}

function startCamera() {
    fetch(FLASK_URL + "/start_camera", { method: "POST" })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                setCameraUI(true);
                addLog("📷 Kamera berhasil dinyalakan");

                // Pastikan <img id="videoFeed" src="/video_feed"> terisi
                const img = document.getElementById("videoFeed");
                if (img && !img.src) {
                    img.src = FLASK_URL + "/video_feed";
                }

                // Mulai polling status operator
                startOperatorPolling();
            } else {
                addLog("❌ Gagal menyalakan kamera");
            }
        })
        .catch(err => {
            console.error(err);
            addLog("❌ Error saat menyalakan kamera");
        });
}

function stopCamera() {
    fetch(FLASK_URL + "/stop_camera", { method: "POST" })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                setCameraUI(false);
                addLog("⏹️ Kamera dimatikan");
                stopOperatorPolling();
            } else {
                addLog("❌ Gagal mematikan kamera");
            }
        })
        .catch(err => {
            console.error(err);
            addLog("❌ Error saat mematikan kamera");
        });
}

// =======================================
// STATUS OPERATOR (VERSI FIXED)
// =======================================
function updateOperatorFromServer(detected, name) {
    const prevDetected = operatorDetected;
    operatorDetected = detected;

    // 1. Update status box kecil (di sidebar)
    const opText = document.getElementById("opText");
    const opStatus = document.getElementById("opStatus");
    const opName = document.getElementById("opName");
    const opNameValue = document.getElementById("opNameValue");
    
    if (opText && opStatus) {
        if (operatorDetected) {
            opStatus.classList.remove("op-bad");
            opStatus.classList.add("op-ok");
            opText.textContent = "TERDETEKSI";
            
            if (name && name !== "Unknown") {
                if (opName) opName.style.display = 'block';
                if (opNameValue) opNameValue.textContent = name;
            } else {
                if (opName) opName.style.display = 'none';
            }
        } else {
            opStatus.classList.remove("op-ok");
            opStatus.classList.add("op-bad");
            opText.textContent = "TIDAK TERDETEKSI";
            if (opName) opName.style.display = 'none';
        }
    }

    // 2. 🎯 UPDATE BANNER BESAR (pojok kanan atas)
    const operatorBanner = document.querySelector('.operator-status-banner');
    if (operatorBanner) {
        if (operatorDetected) {
            operatorBanner.textContent = "Operator Status = OPERATOR DETECTED";
            operatorBanner.classList.remove("not-detected");
            operatorBanner.classList.add("detected");
        } else {
            operatorBanner.textContent = "Operator Status = NOT DETECTED";
            operatorBanner.classList.remove("detected");
            operatorBanner.classList.add("not-detected");
        }
    }

    // 3. Log perubahan
    if (operatorDetected && !prevDetected) {
        const displayName = (name && name !== "Unknown") ? name : "Operator";
        addLog(`✅ ${displayName} terdeteksi di area kerja!`);
    } else if (!operatorDetected && prevDetected) {
        addLog("⚠️ Operator meninggalkan area!");
        if (machineRunning) {
            stopMachine();
            addLog("🛑 Mesin dimatikan otomatis.");
        }
    }
}

        // ===== OPERATOR TIDAK TERDETEKSI =====
        
        // 1. Update status box kecil
        opStatus.classList.remove("op-ok");
        opStatus.classList.add("op-bad");
        opText.textContent = "TIDAK TERDETEKSI";
        opName.style.display = 'none';

        // 2. 🎯 UPDATE BANNER BESAR
        if (operatorBanner) {
            operatorBanner.textContent = "Operator Status = NOT DETECTED";
            operatorBanner.classList.remove("detected");
            operatorBanner.classList.add("not-detected");
            console.log("⚠️ Banner updated to: NOT DETECTED");
        }

        // 3. Log perubahan
        if (prevDetected) {
            addLog("⚠️ Operator meninggalkan area!");
            if (machineRunning) {
                stopMachine();
                addLog("🛑 Mesin dimatikan otomatis.");
            }
        }
    


// =======================================
// POLLING STATUS OPERATOR DARI SERVER
// =======================================
function pollOperatorStatus() {
    if (!isMonitoring) return;
    
    const url = FLASK_URL + '/operator_status';
    
    fetch(url, { cache: 'no-store' }) // Tambahkan ini untuk mencegah caching
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("📦 Operator status dari server:", data);
            const detected = Boolean(data.detected); // Pastikan boolean
            const name = data.name || "Unknown";
            updateOperatorFromServer(detected, name);
        })
        .catch(error => {
            console.error("❌ Poll error:", error);
            addLog(`⚠️ Gagal memperbarui status: ${error.message}`);
            
            // Coba restart polling jika gagal terus-menerus
            if (errorCount > 5) {
                stopOperatorPolling();
                addLog("🛑 Monitoring dihentikan karena terlalu banyak error");
            }
        });
}

function startOperatorPolling() {
    if (operatorStatusInterval) {
        console.log("⚠️ Polling sudah aktif");
        return;
    }
    
    console.log("🔄 Memulai polling status operator...");
    isMonitoring = true;
    
    // Panggil sekali segera
    pollOperatorStatus();
    
    // Lalu set interval
    operatorStatusInterval = setInterval(pollOperatorStatus, 1000);
    addLog("🔄 Monitoring status operator AKTIF");
}
function startOperatorPolling() 
{
    if (operatorStatusInterval) 
    {
        console.log("⚠️ Polling already active");
        return;
    }
    console.log("🔄 Starting polling with 500ms delay...");
    
    // Delay pertama sebelum polling dimulai
    setTimeout(() => 
    {
        pollOperatorStatus();
        operatorStatusInterval = setInterval(pollOperatorStatus, 1000);
        addLog("🔄 Monitoring status operator AKTIF");
    }, 500);
}

function stopOperatorPolling() 
{
    isMonitoring = false;
    if (operatorStatusInterval) 
    {
        clearInterval(operatorStatusInterval);
        operatorStatusInterval = null;
    }
    updateOperatorStatus(false, null);
    addLog("⏹️ Monitoring status operator dihentikan");
}

// =======================================
// INIT EVENT LISTENER SETELAH DOM SIAP
// =======================================
document.addEventListener("DOMContentLoaded", () => {
    const btnStartCam = document.getElementById("btnStartCamera");
    const btnStopCam  = document.getElementById("btnStopCamera");
    const btnStartMon = document.getElementById("btnStartMonitoring");
    const btnStopMon  = document.getElementById("btnStopMonitoring");
    const btnStartM   = document.getElementById("btnStartMachine");
    const btnStopM    = document.getElementById("btnStopMachine");
    const btnToggleOp = document.getElementById("btnToggleOp"); // tombol test, opsional

    if (btnStartCam) btnStartCam.addEventListener("click", startCamera);
    if (btnStopCam)  btnStopCam.addEventListener("click", stopCamera);

    // Kalau kamu punya tombol start/stop monitoring terpisah
    if (btnStartMon) btnStartMon.addEventListener("click", startOperatorPolling);
    if (btnStopMon)  btnStopMon.addEventListener("click", stopOperatorPolling);

    if (btnStartM)   btnStartM.addEventListener("click", startMachine);
    if (btnStopM)    btnStopM.addEventListener("click", stopMachine);

    // Tombol test manual (tidak butuh backend)
    if (btnToggleOp) {
        btnToggleOp.addEventListener("click", () => {
            updateOperatorStatus(!operatorDetected, operatorDetected ? null : "Dummy Operator");
        });
    }

    addLog("✅ Frontend siap digunakan");
});