/**
 * web/static/js/backup_firebase.js (v2.9.0)
 * 
 * 사내 Firebase(sunhang-772e5) 실시간 동기화 & 클라우드 타임라인 뷰어.
 * - 마지막 성공 백업(last_backup_success)과 마지막 백업 시도(last_backup_attempt) 명확 분리
 * - 기기별(미니PC vs 데스크탑) 차등 다단계 Stale 상태 감지 (정상 / 백업준비 / 백업권장 / 장기미백업)
 * - 성공/실패(FAILED) 전체 타임라인 모달 뷰어 제공
 */

const FIREBASE_BACKUP_CONFIG = {
    apiKey: "AIzaSyCe21skNfRno3PPo-xRYCqfwh3jtboo7Ls",
    authDomain: "sunhang-772e5.firebaseapp.com",
    projectId: "sunhang-772e5",
    storageBucket: "sunhang-772e5.firebasestorage.app",
    appId: "1:261167432797:android:5ec981486de9cf320ab9b4"
};

let fbDb = null;
let fbUnsubscribe = null;
let cachedDevicesData = {};
let cachedHistoryData = [];
let currentHistoryFilter = 'all';

function initFirebaseBackupSync() {
    try {
        if (typeof firebase === 'undefined') {
            console.warn('[Firebase] Firebase SDK 미로드 (로컬 오프라인 모드)');
            updateFirebaseBadge(false, 'SDK 미로드');
            return;
        }

        if (!firebase.apps.length) {
            firebase.initializeApp(FIREBASE_BACKUP_CONFIG);
        }
        fbDb = firebase.firestore();
        updateFirebaseBadge(true, '클라우드 LIVE');

        // 1. backup_devices 실시간 구독
        fbUnsubscribe = fbDb.collection("backup_devices").onSnapshot((snapshot) => {
            const devices = {};
            snapshot.forEach((doc) => {
                devices[doc.id] = doc.data();
            });
            cachedDevicesData = devices;
            updateFirebaseBadge(true, '클라우드 LIVE');
            renderFirebaseDevicesStatus(devices);
        }, (err) => {
            console.warn('[Firebase] Firestore 수신 오류:', err);
            updateFirebaseBadge(false, '연결 대기 중');
        });

    } catch (e) {
        console.error('[Firebase] 초기화 예외:', e);
        updateFirebaseBadge(false, '연결 오류');
    }
}

function updateFirebaseBadge(isOnline, text) {
    const textEl = document.getElementById('firebase-cloud-text');
    const pulseEl = document.getElementById('firebase-ping-pulse');
    const dotEl = document.getElementById('firebase-ping-dot');

    if (textEl) textEl.textContent = text;
    if (pulseEl && dotEl) {
        if (isOnline) {
            pulseEl.className = 'animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75';
            dotEl.className = 'relative inline-flex rounded-full h-2 w-2 bg-emerald-500';
        } else {
            pulseEl.className = 'hidden';
            dotEl.className = 'relative inline-flex rounded-full h-2 w-2 bg-amber-500';
        }
    }
}

function renderFirebaseDevicesStatus(devices) {
    const container = document.getElementById('firebase-devices-container');
    if (!container) return;

    const devKeys = ['minipc', 'desktop'];
    let html = '';

    for (const devId of devKeys) {
        const dev = devices[devId] || {};
        const devName = dev.device_name || (devId === 'minipc' ? '내 미니피씨 (100.72.224.71)' : '내 데스크탑 (100.90.20.59)');
        const roleDesc = dev.role || (devId === 'minipc' ? '원래 주기 유지 (매일 09:00 자동 백업)' : '수동 백업 전용 (자동 백업 비활성화)');
        const isAuto = dev.auto_backup_enabled !== undefined ? dev.auto_backup_enabled : (devId === 'minipc');

        // 1. Stale 상태 판정
        const stale = dev.stale_status || { level: 'unknown', badge_color: 'slate', label: '상태 대기' };
        let staleBadgeClass = 'bg-slate-800 text-slate-300 border-slate-700';
        if (stale.badge_color === 'emerald') staleBadgeClass = 'bg-emerald-950/80 text-emerald-400 border-emerald-800/80';
        else if (stale.badge_color === 'blue') staleBadgeClass = 'bg-blue-950/80 text-blue-300 border-blue-800/80';
        else if (stale.badge_color === 'amber') staleBadgeClass = 'bg-amber-950/80 text-amber-300 border-amber-800/80 animate-pulse';
        else if (stale.badge_color === 'red') staleBadgeClass = 'bg-red-950/80 text-red-300 border-red-800/80 animate-pulse';

        // 2. 마지막 성공(Success) 정보
        const success = dev.last_success || {};
        const successTime = success.time || dev.last_backup_time || '-';
        const snapshotId = success.snapshot_id || dev.last_snapshot_id || '-';
        const totalBytesFormatted = (success.total_bytes || dev.total_bytes) ? formatBytes(success.total_bytes || dev.total_bytes) : '-';
        const totalFiles = (success.total_files || dev.total_files) ? `${(success.total_files || dev.total_files).toLocaleString()}개` : '';

        // 3. 마지막 시도(Attempt) 정보
        const attempt = dev.last_attempt || {};
        const attemptTime = attempt.time || dev.last_updated || '-';
        const attemptStatus = attempt.status || dev.last_status || '대기';
        const isAttemptSuccess = attemptStatus === 'success';
        const isAttemptRunning = attemptStatus === 'running';
        const attemptError = attempt.error_message || dev.last_error || '';

        const attemptBadge = isAttemptSuccess
            ? '<span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">성공 (SUCCESS)</span>'
            : (isAttemptRunning
                ? '<span class="text-[10px] px-2 py-0.5 rounded-full bg-blue-950 text-blue-300 border border-blue-800 font-bold animate-pulse">진행 중</span>'
                : '<span class="text-[10px] px-2 py-0.5 rounded-full bg-red-950 text-red-400 border border-red-800 font-bold">실패 (FAILED)</span>');

        const freeDisk = dev.free_disk_gb ? `${dev.free_disk_gb} GB 여유` : '-';

        html += `
            <div class="p-5 rounded-2xl glass-card border border-slate-700/60 hover:border-slate-600 transition space-y-4 bg-slate-900/60 shadow-lg">
                <!-- Header -->
                <div class="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 rounded-xl ${devId === 'minipc' ? 'bg-blue-600/20 text-blue-400' : 'bg-purple-600/20 text-purple-400'} flex items-center justify-center font-bold">
                            <i data-lucide="${devId === 'minipc' ? 'cpu' : 'monitor'}" class="w-5 h-5"></i>
                        </div>
                        <div>
                            <h3 class="text-sm font-bold text-white flex items-center gap-2">
                                ${devName}
                                <span class="text-[10px] px-2 py-0.5 rounded-full border ${staleBadgeClass} font-semibold">
                                    ${stale.label}
                                </span>
                            </h3>
                            <p class="text-[11px] text-slate-400">${roleDesc}</p>
                        </div>
                    </div>
                    <button onclick="openCloudHistoryModal('${devId}')" class="px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium transition border border-slate-700 flex items-center gap-1.5" title="클라우드 백업 이력 조회">
                        <i data-lucide="history" class="w-3.5 h-3.5 text-blue-400"></i> 이력
                    </button>
                </div>

                <!-- 2-Column Split: 마지막 성공 백업 vs 마지막 백업 시도 -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <!-- Left: 마지막 성공 백업 -->
                    <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1.5">
                        <div class="text-[10px] font-bold text-emerald-400 flex items-center gap-1">
                            <i data-lucide="check-circle-2" class="w-3.5 h-3.5"></i> 마지막 성공 백업
                        </div>
                        <div class="text-xs font-mono font-medium text-slate-200">
                            ${successTime}
                        </div>
                        <div class="text-[11px] font-mono text-slate-400 truncate" title="${snapshotId}">
                            ID: <span class="text-slate-300">${snapshotId}</span>
                        </div>
                        <div class="text-[11px] text-slate-400">
                            용량: <span class="text-emerald-400 font-mono font-medium">${totalBytesFormatted}</span> ${totalFiles ? `(${totalFiles})` : ''}
                        </div>
                    </div>

                    <!-- Right: 마지막 백업 시도 -->
                    <div class="p-3 rounded-xl bg-slate-950/60 border ${!isAttemptSuccess ? 'border-red-800/80 bg-red-950/20' : 'border-slate-800'} space-y-1.5">
                        <div class="flex items-center justify-between">
                            <span class="text-[10px] font-bold ${isAttemptSuccess ? 'text-blue-400' : 'text-red-400'} flex items-center gap-1">
                                <i data-lucide="${isAttemptSuccess ? 'clock' : 'alert-triangle'}" class="w-3.5 h-3.5"></i> 마지막 시도
                            </span>
                            ${attemptBadge}
                        </div>
                        <div class="text-xs font-mono font-medium text-slate-200">
                            ${attemptTime}
                        </div>
                        ${!isAttemptSuccess && attemptError ? `
                            <div class="text-[10px] text-red-300 bg-red-950/50 p-1.5 rounded border border-red-900/60 truncate" title="${attemptError}">
                                원인: ${attemptError}
                            </div>
                        ` : `
                            <div class="text-[11px] text-slate-400">
                                결과: <span class="text-emerald-400 font-medium">정상 완료</span>
                            </div>
                        `}
                    </div>
                </div>

                <!-- Footer Status -->
                <div class="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-800/60">
                    <span>저장소 디스크: <strong class="text-cyan-300 font-mono">${freeDisk}</strong></span>
                    <span>동기화: <span class="text-slate-500 font-mono">${dev.last_updated || '-'}</span></span>
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
    if (window.lucide && typeof lucide.createIcons === 'function') {
        lucide.createIcons();
    }
}

// ==================== 클라우드 백업 이력 타임라인 모달 ====================

async function openCloudHistoryModal(filterDevId = null) {
    currentHistoryFilter = filterDevId || 'all';
    const modal = document.getElementById('modal-cloud-history');
    if (!modal) return;

    modal.classList.remove('hidden');
    modal.classList.add('flex');

    // 탭 활성화 상태 갱신
    updateHistoryFilterTabs(currentHistoryFilter);

    // 데이터 로드
    await loadCloudHistoryTimeline();
}

function closeCloudHistoryModal() {
    const modal = document.getElementById('modal-cloud-history');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

function filterCloudHistory(devId) {
    currentHistoryFilter = devId;
    updateHistoryFilterTabs(devId);
    renderCloudHistoryItems(cachedHistoryData, currentHistoryFilter);
}

function updateHistoryFilterTabs(selected) {
    const tabs = ['all', 'minipc', 'desktop'];
    for (const t of tabs) {
        const btn = document.getElementById(`history-tab-${t}`);
        if (!btn) continue;
        if (t === selected) {
            btn.className = 'px-3 py-1.5 rounded-xl text-xs font-bold bg-blue-600 text-white shadow-sm';
        } else {
            btn.className = 'px-3 py-1.5 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition';
        }
    }
}

async function loadCloudHistoryTimeline() {
    const listEl = document.getElementById('cloud-history-list');
    if (listEl) {
        listEl.innerHTML = '<div class="py-8 text-center text-xs text-slate-400 flex items-center justify-center gap-2"><i data-lucide="loader-2" class="w-4 h-4 animate-spin text-blue-400"></i> 클라우드 백업 이력을 불러오는 중...</div>';
        if (window.lucide) lucide.createIcons();
    }

    try {
        const resp = await fetch('/api/firebase/history?limit=50');
        const data = await resp.json();
        cachedHistoryData = data.history || [];
        renderCloudHistoryItems(cachedHistoryData, currentHistoryFilter);
    } catch (e) {
        console.error('[Firebase] 이력 로드 실패:', e);
        if (listEl) {
            listEl.innerHTML = `<div class="py-8 text-center text-xs text-red-400">이력 로드 실패: ${e.message}</div>`;
        }
    }
}

function renderCloudHistoryItems(history, filterDevId) {
    const listEl = document.getElementById('cloud-history-list');
    if (!listEl) return;

    let items = history;
    if (filterDevId && filterDevId !== 'all') {
        items = history.filter(item => item.device_id === filterDevId);
    }

    if (!items.length) {
        listEl.innerHTML = '<div class="py-12 text-center text-xs text-slate-500">조회된 클라우드 백업 이력이 없습니다.</div>';
        return;
    }

    let html = '<div class="space-y-3 relative before:absolute before:inset-0 before:left-4 before:w-0.5 before:bg-slate-800">';

    for (const item of items) {
        const isSuccess = item.status === 'success';
        const isFailed = item.status === 'failed';
        const isMinipc = item.device_id === 'minipc';

        const dotClass = isSuccess 
            ? 'bg-emerald-500 ring-4 ring-slate-900' 
            : 'bg-red-500 ring-4 ring-slate-900 animate-pulse';

        const statusTag = isSuccess
            ? '<span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 font-bold">백업 완료</span>'
            : '<span class="text-[10px] px-2 py-0.5 rounded-full bg-red-950/80 text-red-400 border border-red-800/80 font-bold">백업 실패 (FAILED)</span>';

        const devBadge = isMinipc
            ? '<span class="text-[10px] px-2 py-0.5 rounded bg-blue-900/40 text-blue-300 font-medium">내 미니피씨</span>'
            : '<span class="text-[10px] px-2 py-0.5 rounded bg-purple-900/40 text-purple-300 font-medium">내 데스크탑</span>';

        const sizeStr = item.total_bytes ? formatBytes(item.total_bytes) : '-';
        const filesStr = item.total_files ? `${item.total_files.toLocaleString()}개 파일` : '';
        const durStr = item.duration_seconds ? `${item.duration_seconds}초` : '';

        html += `
            <div class="relative pl-9 text-xs">
                <!-- Timeline Dot -->
                <div class="absolute left-2.5 top-2 -translate-x-1/2 w-3 h-3 rounded-full ${dotClass}"></div>

                <!-- Card Content -->
                <div class="p-3.5 rounded-xl bg-slate-900/80 border ${isSuccess ? 'border-slate-800' : 'border-red-900/60 bg-red-950/10'} hover:border-slate-700 transition space-y-2">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            ${devBadge}
                            <span class="font-mono text-slate-200 font-medium">${item.timestamp || '-'}</span>
                        </div>
                        ${statusTag}
                    </div>

                    ${isSuccess ? `
                        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px] text-slate-300 pt-1 border-t border-slate-800/60 font-mono">
                            <div>스냅샷: <span class="text-blue-400">${item.snapshot_id || '-'}</span></div>
                            <div>용량: <span class="text-emerald-400 font-semibold">${sizeStr}</span> ${filesStr ? `(${filesStr})` : ''}</div>
                            <div>소요: <span class="text-amber-400">${durStr || '-'}</span></div>
                        </div>
                        ${item.profile_name ? `<div class="text-[10px] text-slate-400">프로필: ${item.profile_name}</div>` : ''}
                    ` : `
                        <div class="text-[11px] text-red-300 bg-red-950/40 p-2.5 rounded-lg border border-red-900/60">
                            <strong>실패 원인:</strong> ${item.error_message || '원인 미상 에러'}
                        </div>
                    `}
                </div>
            </div>
        `;
    }

    html += '</div>';
    listEl.innerHTML = html;
    if (window.lucide && typeof lucide.createIcons === 'function') {
        lucide.createIcons();
    }
}

async function triggerManualFirebaseSync() {
    updateFirebaseBadge(true, '동기화 전송 중...');
    try {
        const resp = await fetch('/api/firebase/sync', { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            if (typeof showToast === 'function') {
                showToast('클라우드에 백업 상태가 동기화되었습니다.', 'success');
            }
            updateFirebaseBadge(true, '클라우드 LIVE');
        } else {
            throw new Error(data.error || '동기화 실패');
        }
    } catch (e) {
        console.error('[Firebase] 수동 동기화 실패:', e);
        if (typeof showToast === 'function') {
            showToast('클라우드 동기화 실패: ' + e.message, 'error');
        }
        updateFirebaseBadge(false, '동기화 실패');
    }
}

// ==================== Software Auto-Update UI ====================
async function checkSoftwareUpdateStatus() {
    try {
        const resp = await fetch('/api/update/status');
        const data = await resp.json();
        if (data.success && data.update_available) {
            renderSoftwareUpdateBadge(data);
        }
    } catch (e) {
        console.warn('[Update] 업데이트 확인 건너뜀:', e);
    }
}

function renderSoftwareUpdateBadge(updateInfo) {
    let barEl = document.getElementById('software-update-banner');
    if (!barEl) {
        barEl = document.createElement('div');
        barEl.id = 'software-update-banner';
        barEl.className = 'bg-gradient-to-r from-blue-900/90 to-indigo-900/90 border-b border-blue-500/40 text-blue-100 px-4 py-2 flex items-center justify-between shadow-lg text-xs transition-all sticky top-0 z-50';
        document.body.insertBefore(barEl, document.body.firstChild);
    }

    barEl.innerHTML = `
        <div class="flex items-center space-x-2">
            <span class="flex h-2 w-2 relative">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            <span class="font-semibold text-white">🚀 새 소프트웨어 버전 <strong>v${updateInfo.latest_version}</strong> 배포 감지</span>
            <span class="text-blue-300 hidden md:inline">(${updateInfo.changelog || '시스템 개선 및 보안 패치'})</span>
            ${updateInfo.mandatory ? '<span class="bg-red-600/80 text-white text-[10px] px-1.5 py-0.5 rounded font-bold">필수</span>' : ''}
        </div>
        <div class="flex items-center space-x-2">
            <button onclick="applySoftwareUpdate('${updateInfo.latest_version}')" class="bg-blue-600 hover:bg-blue-500 text-white font-medium px-3 py-1 rounded shadow text-xs transition flex items-center space-x-1 cursor-pointer">
                <i data-lucide="download" class="w-3.5 h-3.5 inline mr-1"></i> 지금 업데이트 적용
            </button>
            <button onclick="document.getElementById('software-update-banner').remove()" class="text-blue-300 hover:text-white px-1.5 py-1 cursor-pointer">
                ✕
            </button>
        </div>
    `;

    if (window.lucide && typeof lucide.createIcons === 'function') {
        lucide.createIcons();
    }
}

async function applySoftwareUpdate(targetVersion) {
    if (!confirm(`백업 시스템을 v${targetVersion} 버전으로 자동 업데이트하시겠습니까?\n\n- 패키지 무결성(SHA-256) 및 전자 서명(Ed25519) 검증 후 안전하게 적용됩니다.\n- 실행 중인 백업 데몬이 약 1~2초간 안전하게 재기동됩니다.`)) {
        return;
    }

    const banner = document.getElementById('software-update-banner');
    if (banner) {
        banner.innerHTML = `
            <div class="flex items-center space-x-2 py-1">
                <span class="animate-spin text-blue-400">⏳</span>
                <span class="text-white font-semibold">v${targetVersion} 다운로드, 전자 서명 검증 및 안전 설치 진행 중... (약 5초 소요)</span>
            </div>
        `;
    }

    try {
        const resp = await fetch('/api/update/apply', { method: 'POST' });
        const res = await resp.json();
        if (res.success) {
            if (typeof showToast === 'function') {
                showToast('업데이트가 시작되었습니다. 잠시 후 페이지가 새로고침됩니다.', 'info');
            }
            setTimeout(() => {
                window.location.reload();
            }, 6000);
        } else {
            throw new Error(res.error || '업데이트 적용 실패');
        }
    } catch (e) {
        alert('업데이트 시작 오류: ' + e.message);
        if (banner) banner.remove();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        initFirebaseBackupSync();
        checkSoftwareUpdateStatus();
    }, 500);
});
