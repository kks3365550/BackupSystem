// web/static/js/backup_migration.js
// 1-Click 라이브 SSD 마이그레이션(클론 & 부트로더 주입) 프론트엔드 모듈

let migrationPollingInterval = null;
let migrationDrivesCache = [];

async function loadMigrationDrives() {
    const selectEl = document.getElementById("migration-target-select");
    const infoEl = document.getElementById("migration-drive-info");
    const btnStart = document.getElementById("btn-start-migration");

    if (!selectEl) return;

    selectEl.innerHTML = '<option value="">드라이브 목록 검색 중...</option>';
    selectEl.disabled = true;

    try {
        const res = await fetch("/api/migration/disks");
        const data = await res.json();

        if (!data.success || !data.drives || data.drives.length === 0) {
            selectEl.innerHTML = '<option value="">선택 가능한 대상 드라이브가 없습니다 (C: 외 물리 드라이브 필요)</option>';
            selectEl.disabled = true;
            if (infoEl) infoEl.innerHTML = '<span class="text-amber-400">⚠️ 복제할 추가 SSD/HDD가 감지되지 않았습니다. 새 SSD를 연결해 주세요.</span>';
            if (btnStart) btnStart.disabled = true;
            return;
        }

        migrationDrivesCache = data.drives;
        selectEl.innerHTML = "";

        data.drives.forEach(d => {
            const opt = document.createElement("option");
            opt.value = d.drive;
            const acceptTag = d.acceptable ? " [복제 가능]" : " [용량 부족]";
            opt.textContent = `${d.drive} (총 ${d.total_gb} GB / 여유 ${d.free_gb} GB)${acceptTag}`;
            if (!d.acceptable) {
                opt.classList.add("text-zinc-500");
            }
            selectEl.appendChild(opt);
        });

        selectEl.disabled = false;
        onMigrationDriveChange();
    } catch (err) {
        console.error("마이그레이션 드라이브 목록 로드 실패:", err);
        selectEl.innerHTML = '<option value="">드라이브 목록 조회 실패</option>';
        if (infoEl) infoEl.innerHTML = `<span class="text-rose-400">조회 실패: ${err.message}</span>`;
    }
}

function onMigrationDriveChange() {
    const selectEl = document.getElementById("migration-target-select");
    const infoEl = document.getElementById("migration-drive-info");
    const btnStart = document.getElementById("btn-start-migration");

    if (!selectEl || !infoEl) return;
    const selectedVal = selectEl.value;
    const drive = migrationDrivesCache.find(d => d.drive === selectedVal);

    if (!drive) {
        infoEl.innerHTML = '<span class="text-zinc-400">대상을 선택하세요.</span>';
        if (btnStart) btnStart.disabled = true;
        return;
    }

    if (drive.acceptable) {
        const espTag = drive.can_auto_esp 
            ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-950 text-purple-300 border border-purple-800">100% UEFI ESP 자동생성 지원</span>' 
            : '<span class="px-2 py-0.5 rounded text-[10px] font-medium bg-zinc-800 text-zinc-400">동일 디스크 (파티션 복제 모드)</span>';
        infoEl.innerHTML = `
            <div class="space-y-1">
                <div class="flex items-center gap-2 text-emerald-400 font-medium">
                    <i data-lucide="check-circle" class="w-4 h-4"></i>
                    <span>마이그레이션 적합: 총 ${drive.total_gb} GB (C: 사용량 ${drive.c_used_gb} GB 완벽 수용 가능)</span>
                </div>
                <div class="flex items-center gap-2 text-[11px] text-zinc-400">
                    <span>물리 디스크: Disk ${drive.disk_number !== null ? drive.disk_number : '감지됨'}</span>
                    <span>|</span>
                    ${espTag}
                </div>
            </div>
        `;
        if (btnStart) btnStart.disabled = false;
    } else {
        infoEl.innerHTML = `
            <div class="flex items-center gap-2 text-rose-400 font-medium">
                <i data-lucide="alert-triangle" class="w-4 h-4"></i>
                <span>${drive.reason}</span>
            </div>
        `;
        if (btnStart) btnStart.disabled = true;
    }

    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function openMigrationConfirmModal() {
    const selectEl = document.getElementById("migration-target-select");
    const targetDrive = selectEl ? selectEl.value : "";
    if (!targetDrive) {
        alert("마이그레이션 대상 SSD 드라이브를 먼저 선택해주세요.");
        return;
    }

    const modalTargetText = document.getElementById("modal-migration-target-text");
    if (modalTargetText) {
        modalTargetText.textContent = targetDrive;
    }

    const drive = migrationDrivesCache.find(d => d.drive === targetDrive);
    const chkEsp = document.getElementById("chk-migration-auto-esp");
    if (chkEsp) {
        if (drive && drive.can_auto_esp) {
            chkEsp.checked = true;
            chkEsp.disabled = false;
        } else {
            chkEsp.checked = false;
            chkEsp.disabled = true;
        }
    }

    const chk = document.getElementById("chk-migration-danger-confirm");
    if (chk) chk.checked = false;

    const btnRun = document.getElementById("btn-run-migration-final");
    if (btnRun) btnRun.disabled = true;

    const modal = document.getElementById("migration-confirm-modal");
    if (modal) modal.classList.remove("hidden");
}

function onMigrationDangerCheckChange() {
    const chk = document.getElementById("chk-migration-danger-confirm");
    const btnRun = document.getElementById("btn-run-migration-final");
    if (btnRun && chk) {
        btnRun.disabled = !chk.checked;
    }
}

async function confirmAndRunMigration() {
    const selectEl = document.getElementById("migration-target-select");
    const targetDrive = selectEl ? selectEl.value : "";
    if (!targetDrive) return;

    const chkEsp = document.getElementById("chk-migration-auto-esp");
    const autoPrepareEsp = chkEsp ? chkEsp.checked : true;

    closeModal("migration-confirm-modal");

    try {
        const res = await fetch("/api/migration/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                target_drive: targetDrive,
                auto_prepare_esp: autoPrepareEsp
            })
        });
        const data = await res.json();

        if (!res.ok || !data.success) {
            alert("마이그레이션 시작 실패: " + (data.detail || data.error || "알 수 없는 오류"));
            return;
        }

        appendMigrationConsoleLog(`[START] ${targetDrive} 드라이브로의 라이브 마이그레이션이 시작되었습니다.`);
        startMigrationPolling();
    } catch (err) {
        alert("네트워크 통신 오류: " + err.message);
    }
}

function startMigrationPolling() {
    if (migrationPollingInterval) {
        clearInterval(migrationPollingInterval);
    }

    pollMigrationStatus();
    migrationPollingInterval = setInterval(pollMigrationStatus, 1500);
}

async function pollMigrationStatus() {
    try {
        const [resSt, resLogs] = await Promise.all([
            fetch("/api/migration/status"),
            fetch("/api/migration/logs?limit=50")
        ]);

        const dataSt = await resSt.json();
        const dataLogs = await resLogs.json();

        if (dataSt.success && dataSt.status) {
            updateMigrationUI(dataSt.status);
        }

        if (dataLogs.success && dataLogs.logs) {
            renderMigrationLogs(dataLogs.logs);
        }
    } catch (err) {
        console.warn("마이그레이션 상태 폴링 실패:", err);
    }
}

function updateMigrationUI(status) {
    const btnStart = document.getElementById("btn-start-migration");
    const btnStop = document.getElementById("btn-stop-migration");
    const progressBar = document.getElementById("migration-progress-bar");
    const progressText = document.getElementById("migration-progress-percent");
    const phaseText = document.getElementById("migration-current-phase");
    const badgeEl = document.getElementById("migration-status-badge");
    const selectEl = document.getElementById("migration-target-select");

    const isRunning = status.is_running;

    if (btnStart) {
        if (isRunning) {
            btnStart.classList.add("hidden");
        } else {
            btnStart.classList.remove("hidden");
        }
    }

    if (btnStop) {
        if (isRunning) {
            btnStop.classList.remove("hidden");
        } else {
            btnStop.classList.add("hidden");
        }
    }

    if (selectEl) {
        selectEl.disabled = isRunning;
    }

    if (progressBar) {
        progressBar.style.width = `${status.progress_percent || 0}%`;
    }

    if (progressText) {
        progressText.textContent = `${status.progress_percent || 0}%`;
    }

    if (phaseText) {
        phaseText.textContent = status.current_phase || "대기 중";
    }

    if (badgeEl) {
        const st = status.status || "idle";
        badgeEl.className = "text-[11px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider ";
        if (st === "idle") {
            badgeEl.className += "bg-zinc-800 text-zinc-400 border border-zinc-700";
            badgeEl.textContent = "대기 중";
        } else if (st === "preparing") {
            badgeEl.className += "bg-blue-950 text-blue-300 border border-blue-800 animate-pulse";
            badgeEl.textContent = "준비 중 (VSS)";
        } else if (st === "copying") {
            badgeEl.className += "bg-indigo-950 text-indigo-300 border border-indigo-800 animate-pulse";
            badgeEl.textContent = "미러링 복제 중";
        } else if (st === "bootloading") {
            badgeEl.className += "bg-purple-950 text-purple-300 border border-purple-800 animate-pulse";
            badgeEl.textContent = "부트로더 주입 중";
        } else if (st === "completed") {
            badgeEl.className += "bg-emerald-950 text-emerald-300 border border-emerald-800";
            badgeEl.textContent = "🎉 마이그레이션 완료";
            if (migrationPollingInterval) {
                clearInterval(migrationPollingInterval);
                migrationPollingInterval = null;
            }
        } else if (st === "failed") {
            badgeEl.className += "bg-rose-950 text-rose-300 border border-rose-800";
            badgeEl.textContent = "❌ 실패";
            if (migrationPollingInterval) {
                clearInterval(migrationPollingInterval);
                migrationPollingInterval = null;
            }
        } else if (st === "cancelled") {
            badgeEl.className += "bg-amber-950 text-amber-300 border border-amber-800";
            badgeEl.textContent = "⚠️ 취소됨";
            if (migrationPollingInterval) {
                clearInterval(migrationPollingInterval);
                migrationPollingInterval = null;
            }
        }
    }
}

function renderMigrationLogs(logs) {
    const consoleEl = document.getElementById("migration-console");
    if (!consoleEl) return;

    if (!logs || logs.length === 0) {
        consoleEl.innerHTML = '<div class="text-zinc-500">[대기] 마이그레이션 시작 시 실시간 로그가 출력됩니다.</div>';
        return;
    }

    consoleEl.innerHTML = logs.map(l => {
        let cls = "text-zinc-300";
        if (l.includes("ERROR") || l.includes("❌") || l.includes("실패")) cls = "text-rose-400 font-bold";
        else if (l.includes("🎉") || l.includes("성공") || l.includes("완료")) cls = "text-emerald-400 font-bold";
        else if (l.includes("VSS") || l.includes("Robocopy") || l.includes("bcdboot")) cls = "text-cyan-300";
        else if (l.includes("💡") || l.includes("안내")) cls = "text-amber-300";
        return `<div class="${cls}">${escapeHtml(l)}</div>`;
    }).join("");

    consoleEl.scrollTop = consoleEl.scrollHeight;
}

function appendMigrationConsoleLog(msg) {
    const consoleEl = document.getElementById("migration-console");
    if (!consoleEl) return;
    const div = document.createElement("div");
    div.className = "text-cyan-300";
    div.textContent = msg;
    consoleEl.appendChild(div);
    consoleEl.scrollTop = consoleEl.scrollHeight;
}

async function stopLiveMigration() {
    if (!confirm("정말 진행 중인 마이그레이션 작업을 중단하시겠습니까?")) return;

    try {
        const res = await fetch("/api/migration/stop", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            appendMigrationConsoleLog("[STOP] 중단 요청이 전달되었습니다.");
            pollMigrationStatus();
        } else {
            alert("중단 실패: " + (data.detail || data.error));
        }
    } catch (err) {
        alert("네트워크 오류: " + err.message);
    }
}

// 탭 전환 시 자동 드라이브 목록 로드
document.addEventListener("DOMContentLoaded", () => {
    // OS 백업 탭이 활성화될 때 또는 첫 로드 시 드라이브 로드
    setTimeout(loadMigrationDrives, 1000);
});
