// static/js/main.js
// =======================================
// FABRICATION MACHINE CONTROL - MAIN JS
// =======================================

console.log("🚀 Main.js loaded!");

// =======================================
// Konfigurasi & State Global
// =======================================
const FLASK_URL = window.location.origin;
const VIDEO_FEED_URL = FLASK_URL + '/video_feed';

let operatorDetected = false;
let operatorStatusInterval = null;
let machineRunning = false;
let runtime = 0;
let runtimeTimer = null;

// =======================================
// Utility: Activity Log
// =======================================
function addLog(message) {
    const logArea = document.getElementById("log");
    if (!logArea) return;
    
    const time = new Date().toLocaleTimeString("id-ID", { hour12: false });
    const line = document.createElement("div");
    line.textContent = `[${time}] ${message}`;
    
    logArea.appendChild(line);
    logArea.scrollTop = logArea.scrollHeight;
    console.log(`[${time}] ${message}`);
}

// =======================================
// Session Management
// =======================================
function checkSession() {
    fetch(FLASK_URL + '/check_session')
        .then(resp => {
            if (!resp.ok) {
                window.location.href = '/login';
                return;
            }
            return resp.json();
        })
        .then(data => {
            if (data && data.logged_in) {
                const userName = document.getElementById("userName");
                const userRole = document.getElementById("userRole");
                
                if (userName) userName.textContent = data.name || data.username;
                if (userRole) userRole.textContent = data.role || 'User';
                
                addLog(`👋 Selamat datang, ${data.name}!`);
            } else {
                window.location.href = '/login';
            }
        })
        .catch(() => {
            window.location.href = '/login';
        });
}

function logout() {
    if (confirm('Apakah Anda yakin ingin logout?')) {
        addLog('👋 Logging out...');
        
        fetch(FLASK_URL + '/logout', { method: 'POST' })
            .then(() => {
                window.location.href = '/login';
            })
            .catch(() => {
                window.location.href = '/login';
            });
    }
}

// =======================================
// Operator Status Management
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

    // 2. Update BANNER BESAR (pojok kanan atas)
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
        
        // Auto-stop machine jika operator hilang
        if (machineRunning) {
            stopMachine();
            addLog("🛑 Mesin dimatikan otomatis (operator tidak terdeteksi).");
        }
    }
}

function pollOperatorStatus() {
    fetch(FLASK_URL + '/operator_status', { cache: 'no-store' })
        .then(resp => {
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return resp.json();
        })
        .then(data => {
            console.log("📦 Operator status dari server:", data);
            const detected = Boolean(data.detected);
            const name = data.name || "Unknown";
            updateOperatorFromServer(detected, name);
        })
        .catch(error => {
            console.error("❌ Poll error:", error);
        });
}

function startOperatorPolling() {
    if (operatorStatusInterval) {
        console.log("⚠️ Polling sudah aktif");
        return;
    }
    
    console.log("🔄 Memulai polling status operator...");
    
    // Panggil sekali segera
    pollOperatorStatus();
    
    // Set interval polling setiap 1 detik
    operatorStatusInterval = setInterval(pollOperatorStatus, 1000);
    addLog("🔄 Monitoring status operator AKTIF");
}

function stopOperatorPolling() {
    if (!operatorStatusInterval) return;
    
    console.log("⏹️ Stop polling");
    clearInterval(operatorStatusInterval);
    operatorStatusInterval = null;
    
    updateOperatorFromServer(false, null);
    addLog("⏹️ Monitoring status operator dihentikan");
}

// =======================================
// Camera Control
// =======================================
function setStreamActive(isActive) {
    const cameraStream = document.getElementById("cameraStream");
    const videoFallback = document.getElementById("videoFallback");
    const cameraStatus = document.getElementById("cameraStatus");
    
    if (isActive) {
        if (cameraStream) {
            cameraStream.src = VIDEO_FEED_URL + '?t=' + Date.now();
            cameraStream.style.display = 'block';
        }
        if (videoFallback) videoFallback.style.display = 'none';
        if (cameraStatus) cameraStatus.style.display = 'flex';
    } else {
        if (cameraStream) {
            cameraStream.src = "";
            cameraStream.style.display = 'none';
        }
        if (videoFallback) videoFallback.style.display = 'block';
        if (cameraStatus) cameraStatus.style.display = 'none';
    }
}

function startCamera() {
    const cameraID = 0;
    addLog("ℹ️ Memulai kamera...");

    fetch(FLASK_URL + '/start_monitoring', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_id: cameraID })
    })
    .then(response => {
        if (!response.ok) throw new Error('Server error');
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            setStreamActive(true);
            startOperatorPolling();
            addLog(`✅ Kamera aktif`);
        } else {
            addLog(`⚠️ ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        addLog("❌ Gagal start kamera");
        alert("Pastikan Flask server berjalan!");
    });
}

function stopCamera() {
    addLog("ℹ️ Menghentikan kamera...");

    fetch(FLASK_URL + '/stop_monitoring', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => {
        if (!response.ok) throw new Error('Server error');
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            setStreamActive(false);
            stopOperatorPolling();
            addLog(`🛑 Kamera dimatikan`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        addLog("❌ Gagal stop kamera");
    });
}

// =======================================
// Machine Control
// =======================================
function startMachine() {
    if (machineRunning) return;
    
    machineRunning = true;
    
    const machineText = document.getElementById("machineText");
    const machineBox = document.getElementById("machineBox");
    const runtimeEl = document.getElementById("runtime");
    
    if (machineText) machineText.textContent = "MENYALA";
    if (machineBox) machineBox.classList.add("machine-on");
    
    addLog("🟢 Mesin ON");
    
    // Reset runtime
    runtime = 0;
    if (runtimeEl) runtimeEl.textContent = "0 s";
    
    // Start runtime counter
    runtimeTimer = setInterval(() => {
        runtime++;
        if (runtimeEl) runtimeEl.textContent = runtime + " s";
    }, 1000);
}

function stopMachine() {
    if (!machineRunning) return;
    
    machineRunning = false;
    
    const machineText = document.getElementById("machineText");
    const machineBox = document.getElementById("machineBox");
    
    if (machineText) machineText.textContent = "MATI";
    if (machineBox) machineBox.classList.remove("machine-on");
    
    addLog("🔴 Mesin OFF");
    
    // Stop runtime counter
    if (runtimeTimer) {
        clearInterval(runtimeTimer);
        runtimeTimer = null;
    }
}

// =======================================
// Emergency Stop
// =======================================
function initEmergencyStop() {
    const btnEStop = document.getElementById("btnEStop");
    const estopProgress = document.getElementById("estopProgress");
    
    if (!btnEStop || !estopProgress) return;
    
    let holdInterval;
    
    btnEStop.addEventListener("mousedown", () => {
        let progress = 0;
        estopProgress.style.width = "0%";
        
        holdInterval = setInterval(() => {
            progress += 5;
            estopProgress.style.width = progress + "%";
            
            if (progress >= 100) {
                clearInterval(holdInterval);
                stopMachine();
                addLog("🚨 EMERGENCY STOP!");
                alert("EMERGENCY STOP!");
            }
        }, 50);
    });
    
    btnEStop.addEventListener("mouseup", () => {
        if (holdInterval) clearInterval(holdInterval);
        estopProgress.style.width = "0%";
    });
    
    btnEStop.addEventListener("mouseleave", () => {
        if (holdInterval) clearInterval(holdInterval);
        estopProgress.style.width = "0%";
    });
}

// =======================================
// Log Management
// =======================================
function clearLog() {
    const logArea = document.getElementById("log");
    if (logArea) {
        logArea.innerHTML = "";
        addLog("🗑️ Log cleared");
    }
}

function exportLog() {
    const logArea = document.getElementById("log");
    if (!logArea) return;
    
    const logs = Array.from(logArea.children).map(el => el.textContent).join("\n");
    const blob = new Blob([logs], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "activity_log_" + new Date().toISOString().slice(0,10) + ".txt";
    link.click();
    
    addLog("📥 Log exported");
}

// =======================================
// Ripple Effect for Buttons
// =======================================
function initRippleEffect() {
    document.querySelectorAll(".btn-ripple").forEach(btn => {
        btn.addEventListener("click", function (e) {
            const circle = document.createElement("span");
            const diameter = Math.max(this.clientWidth, this.clientHeight);
            const rect = this.getBoundingClientRect();
            
            circle.style.width = circle.style.height = `${diameter}px`;
            circle.style.left = `${e.clientX - rect.left - diameter / 2}px`;
            circle.style.top = `${e.clientY - rect.top - diameter / 2}px`;
            circle.classList.add("ripple");
            
            const existingRipple = this.getElementsByClassName("ripple")[0];
            if (existingRipple) existingRipple.remove();
            
            this.appendChild(circle);
        });
    });
}

// =======================================
// DOM Ready - Initialize Everything
// =======================================
document.addEventListener('DOMContentLoaded', function () {
    console.log("✅ DOM ready - Initializing...");

    // Update copyright year
    const yearEl = document.getElementById('currentYear');
    if (yearEl) yearEl.textContent = new Date().getFullYear();

    // Check user session
    checkSession();

    // Initialize ripple effects
    initRippleEffect();

    // Initialize emergency stop
    initEmergencyStop();

    // Event Listeners - Camera Controls
    const btnStartCamera = document.getElementById("btnStartCamera");
    const btnStopCamera = document.getElementById("btnStopCamera");
    const btnSnap = document.getElementById("btnSnap");
    
    if (btnStartCamera) btnStartCamera.addEventListener("click", startCamera);
    if (btnStopCamera) btnStopCamera.addEventListener("click", stopCamera);
    if (btnSnap) btnSnap.addEventListener("click", () => {
        alert("Snapshot feature: Coming soon!");
    });

    // Event Listeners - Machine Controls
    const btnStart = document.getElementById("btnStart");
    const btnStop = document.getElementById("btnStop");
    
    if (btnStart) {
        btnStart.addEventListener("click", () => {
            if (!operatorDetected) {
                addLog("⚠️ Operator belum terdeteksi!");
                alert("⚠️ Operator belum terdeteksi!\nMesin tidak dapat dinyalakan.");
                return;
            }
            startMachine();
        });
    }
    
    if (btnStop) btnStop.addEventListener("click", stopMachine);

    // Event Listeners - Log Controls
    const btnClear = document.getElementById("btnClear");
    const btnExport = document.getElementById("btnExport");
    
    if (btnClear) btnClear.addEventListener("click", clearLog);
    if (btnExport) btnExport.addEventListener("click", exportLog);

    // Event Listener - Logout
    const btnLogout = document.getElementById("btnLogout");
    if (btnLogout) btnLogout.addEventListener("click", logout);

    // Event Listener - Test Toggle (for development)
    const btnToggleOp = document.getElementById("btnToggleOp");
    if (btnToggleOp) {
        btnToggleOp.addEventListener("click", () => {
            updateOperatorFromServer(!operatorDetected, "Test Manual");
            addLog("🔧 Manual test toggle digunakan");
        });
    }

    // Initialize UI state
    setStreamActive(false);
    updateOperatorFromServer(false, null);
    
    addLog("🚀 System ready");
    console.log("✅ All systems initialized");
});