// =========================================================================
// [백업시스템] Windows 베어메탈 시스템 이미지 (전체 C드라이브) 백업 로직
// =========================================================================

async function loadSystemImageStatus() {
    const driveSelect = document.getElementById('sysimg-drive-select');
    const targetDrive = driveSelect ? driveSelect.value : 'D:';

    try {
        const data = await fetchAPI(`/api/system-image/status?target_drive=${targetDrive}`);
        if (!data) return;

        // C: drive
        const cUsed = document.getElementById('sysimg-c-used');
        const cTotal = document.getElementById('sysimg-c-total');
        if (cUsed) cUsed.innerText = `${data.c_drive.used_gb} GB`;
        if (cTotal) cTotal.innerText = `전체 ${data.c_drive.total_gb} GB 중 사용 중`;

        // Target drive
        const dTitle = document.getElementById('sysimg-target-title');
        const dFree = document.getElementById('sysimg-d-free');
        const dBadge = document.getElementById('sysimg-space-badge');
        if (dTitle) dTitle.innerText = `백업 저장 드라이브 (${data.target_drive})`;
        if (dFree) dFree.innerText = `${data.target_drive_info.free_gb} GB`;
        if (dBadge) {
            if (data.target_drive_info.sufficient_space) {
                dBadge.innerHTML = '<span class="text-emerald-400 font-semibold">✓ 백업 가능 (여유 공간 충분)</span>';
            } else {
                dBadge.innerHTML = '<span class="text-amber-400 font-semibold">! 여유 공간 부족 주의</span>';
            }
        }

        // Last backup
        const lastStatus = document.getElementById('sysimg-last-status');
        const lastTime = document.getElementById('sysimg-last-time');
        if (lastStatus && lastTime) {
            if (data.backup_info.exists) {
                lastStatus.innerText = `${data.backup_info.size_gb} GB`;
                lastStatus.className = 'text-2xl font-black text-emerald-400 font-mono';
                lastTime.innerText = `최근 백업: ${data.backup_info.last_modified || '-'}`;
            } else {
                lastStatus.innerText = '미생성';
                lastStatus.className = 'text-2xl font-black text-slate-100 font-mono';
                lastTime.innerText = `${data.backup_info.path} 에 이미지 없음`;
            }
        }

        // Running state
        updateSystemImageRunningUI(data.is_running);

        if (data.is_running) {
            startPollingSystemImageLogs();
        }
    } catch (e) {
        console.error('Failed to load system image status:', e);
    }
}

function updateSystemImageRunningUI(isRunning) {
    const btnStart = document.getElementById('btn-start-sysimg');
    const btnStop = document.getElementById('btn-stop-sysimg');
    const badge = document.getElementById('sysimg-running-badge');

    if (isRunning) {
        if (btnStart) {
            btnStart.disabled = true;
            btnStart.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> 백업 생성 진행 중...';
            btnStart.classList.add('opacity-60', 'cursor-not-allowed');
        }
        if (btnStop) btnStop.classList.remove('hidden');
        if (badge) {
            badge.innerText = '백업 실행 중';
            badge.className = 'text-[11px] px-2.5 py-0.5 rounded-full font-bold bg-amber-950/80 text-amber-300 border border-amber-700/60 animate-pulse';
        }
    } else {
        if (btnStart) {
            btnStart.disabled = false;
            btnStart.innerHTML = '<i data-lucide="save" class="w-4 h-4"></i> 지금 OS 전체 백업 시작';
            btnStart.classList.remove('opacity-60', 'cursor-not-allowed');
        }
        if (btnStop) btnStop.classList.add('hidden');
        if (badge) {
            badge.innerText = '대기 중';
            badge.className = 'text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-slate-800 text-slate-400 border border-slate-700';
        }
    }
    lucide.createIcons();
}

async function startSystemImageBackup() {
    const driveSelect = document.getElementById('sysimg-drive-select');
    const targetDrive = driveSelect ? driveSelect.value : 'D:';

    const msg = `윈도우 베어메탈(전체) 시스템 이미지 백업을 시작하시겠습니까?\n\n` +
        `• 대상: C: 전체 (부팅 EFI 파티션, 복구 파티션, OS 전체)\n` +
        `• 저장 위치: ${targetDrive}\\WindowsImageBackup\n\n` +
        `※ 시스템 권한을 위해 윈도우 관리자(UAC) 확인 창이 뜨면 '예'를 눌러주세요.`;

    if (!confirm(msg)) return;

    updateSystemImageRunningUI(true);

    const consoleBox = document.getElementById('sysimg-console');
    if (consoleBox) {
        consoleBox.innerHTML = '<div class="text-blue-400">[시작] 윈도우 wbadmin 시스템 이미지 백업 명령을 호출합니다...</div>';
    }

    try {
        const res = await fetchAPI('/api/system-image/start', {
            method: 'POST',
            body: JSON.stringify({ target_drive: targetDrive })
        });

        if (res && res.success) {
            startPollingSystemImageLogs();
        } else {
            alert('백업 시작 실패: ' + (res ? res.error : '알 수 없는 오류'));
            updateSystemImageRunningUI(false);
        }
    } catch (e) {
        alert('백업 요청 오류: ' + e.message);
        updateSystemImageRunningUI(false);
    }
}

function startPollingSystemImageLogs() {
    if (sysImageLogTimer) clearInterval(sysImageLogTimer);

    sysImageLogTimer = setInterval(async () => {
        try {
            const data = await fetchAPI('/api/system-image/logs');
            if (!data) return;

            const consoleBox = document.getElementById('sysimg-console');
            if (consoleBox && data.logs) {
                consoleBox.innerHTML = data.logs.map(line => {
                    let color = 'text-slate-300';
                    if (line.includes('[SUCCESS]') || line.includes('성공적으로 완료')) color = 'text-emerald-400 font-bold';
                    if (line.includes('[ERROR]') || line.includes('오류') || line.includes('실패')) color = 'text-red-400 font-bold';
                    if (line.includes('[WARNING]')) color = 'text-amber-400';
                    return `<div class="${color}">${line}</div>`;
                }).join('');
                consoleBox.scrollTop = consoleBox.scrollHeight;
            }

            if (!data.is_running) {
                clearInterval(sysImageLogTimer);
                sysImageLogTimer = null;
                updateSystemImageRunningUI(false);
                loadSystemImageStatus();
            }
        } catch (e) {
            console.error('Error polling system image logs:', e);
        }
    }, 2000);
}

async function stopSystemImageBackup() {
    if (!confirm('진행 중인 윈도우 시스템 이미지 백업을 중단하시겠습니까?')) return;
    try {
        await fetchAPI('/api/system-image/stop', { method: 'POST' });
        alert('백업 중단 명령이 전송되었습니다.');
    } catch (e) {
        alert('중단 실패: ' + e.message);
    }
}

async function verifySnapshot(snapshotId) {
    if (!confirm(`스냅샷 [${snapshotId}]의 zstandard 압축 블롭 및 SHA-256 해시 무결성을 정밀 검증하시겠습니까?`)) return;
    try {
        const res = await fetchAPI('/api/verify/run', {
            method: 'POST',
            body: JSON.stringify({ snapshot_id: snapshotId })
        });
        if (res.success) {
            alert(`✅ 무결성 검증 완료: 100% 정상!\n- 검사된 블롭: ${res.verified_count}개\n- 오류: 0개\n모든 백업 데이터가 완벽하게 보존되어 있습니다.`);
        } else {
            alert(`⚠️ 무결성 검증 실패: 손상 블롭 ${res.error_count}개 감지됨!`);
        }
        await loadSnapshots();
    } catch (e) {
        alert('무결성 검증 중 오류 발생: ' + e.message);
    }
}

// Modal Helpers
