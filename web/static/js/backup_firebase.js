/**
 * web/static/js/backup_firebase.js
 * 
 * 사내 Firebase(sunhang-772e5) Firestore 실시간 리스너 및 백업 전용 대시보드 인식 모듈.
 * 미니PC(100.72.224.71)와 데스크탑(100.90.20.59)의 백업 상태를 실시간 감지하여 시각화합니다.
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
let lastKnownSnapshots = {};

function initFirebaseBackupSync() {
    try {
        if (typeof firebase === 'undefined') {
            console.warn('[Firebase] Firebase SDK가 로드되지 않아 오프라인 모드로 동작합니다.');
            updateFirebaseBadge(false, 'SDK 미로드 (로컬 모드)');
            return;
        }

        if (!firebase.apps.length) {
            firebase.initializeApp(FIREBASE_BACKUP_CONFIG);
        }
        fbDb = firebase.firestore();
        updateFirebaseBadge(true, '클라우드 실시간 연결 중...');

        // Firestore 실시간 리스너 구독 (backup_devices)
        fbUnsubscribe = fbDb.collection("backup_devices").onSnapshot((snapshot) => {
            const devices = {};
            snapshot.forEach((doc) => {
                devices[doc.id] = doc.data();
            });

            updateFirebaseBadge(true, '클라우드 LIVE');
            renderFirebaseDevicesStatus(devices);

            // 신규 스냅샷 감지 및 토스트 알림
            checkNewSnapshotAlert(devices);
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

function checkNewSnapshotAlert(devices) {
    for (const [devId, data] of Object.entries(devices)) {
        const snapId = data.last_snapshot_id;
        if (!snapId) continue;

        if (lastKnownSnapshots[devId] && lastKnownSnapshots[devId] !== snapId) {
            // 새 백업 감지
            const devName = data.device_name || devId;
            if (typeof showToast === 'function') {
                showToast(`[${devName}] 새 백업 완료: ${snapId}`, 'success');
            }
            // 스냅샷 목록 자동 갱신
            if (typeof loadSnapshots === 'function') {
                loadSnapshots();
            }
            if (typeof loadDashboardStats === 'function') {
                loadDashboardStats();
            }
        }
        lastKnownSnapshots[devId] = snapId;
    }
}

function renderFirebaseDevicesStatus(devices) {
    const container = document.getElementById('firebase-devices-container');
    if (!container) return;

    const devKeys = ['minipc', 'desktop'];
    let html = '';

    for (const devId of devKeys) {
        const dev = devices[devId] || {
            device_id: devId,
            device_name: devId === 'minipc' ? '내 미니피씨 (100.72.224.71)' : '내 데스크탑 (100.90.20.59)',
            role: devId === 'minipc' ? '원래 주기 유지 (매일 09:00 자동 백업)' : '수동 백업 전용 (자동 백업 비활성화)',
            auto_backup_enabled: devId === 'minipc',
            last_status: '대기',
            last_updated: '동기화 대기 중',
            free_disk_gb: 0,
            last_snapshot_id: '-'
        };

        const isSuccess = dev.last_status === 'success';
        const isRunning = dev.last_status === 'running';
        const statusBadgeClass = isSuccess 
            ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
            : (isRunning ? 'bg-blue-950/60 text-blue-400 border-blue-800/60 animate-pulse' : 'bg-slate-800 text-slate-400 border-slate-700');
        const statusLabel = isSuccess ? '정상 백업' : (isRunning ? '백업 진행 중' : (dev.last_status || '상태 없음'));

        const bytesFormatted = dev.total_bytes ? formatBytes(dev.total_bytes) : '-';
        const diskFreeFormatted = dev.free_disk_gb ? `${dev.free_disk_gb} GB 여유` : '-';
        const lastBackupFormatted = dev.last_backup_time || dev.last_updated || '-';

        html += `
            <div class="p-4 rounded-2xl glass-card border border-slate-700/60 hover:border-slate-600 transition space-y-3 bg-slate-900/50">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2.5">
                        <div class="w-8 h-8 rounded-lg ${devId === 'minipc' ? 'bg-blue-600/20 text-blue-400' : 'bg-purple-600/20 text-purple-400'} flex items-center justify-center font-bold">
                            <i data-lucide="${devId === 'minipc' ? 'cpu' : 'monitor'}" class="w-4 h-4"></i>
                        </div>
                        <div>
                            <h3 class="text-xs font-bold text-white">${dev.device_name}</h3>
                            <p class="text-[10px] text-slate-400">${dev.role || ''}</p>
                        </div>
                    </div>
                    <span class="text-[11px] px-2 py-0.5 rounded-full font-medium border ${statusBadgeClass}">
                        ${statusLabel}
                    </span>
                </div>

                <div class="grid grid-cols-2 gap-2 text-xs pt-1 border-t border-slate-800">
                    <div>
                        <div class="text-[10px] text-slate-400">최근 스냅샷</div>
                        <div class="text-[11px] font-mono font-medium text-slate-200 truncate" title="${dev.last_snapshot_id || '-'}">
                            ${dev.last_snapshot_id || '-'}
                        </div>
                    </div>
                    <div>
                        <div class="text-[10px] text-slate-400">백업 일시</div>
                        <div class="text-[11px] text-slate-300 truncate" title="${lastBackupFormatted}">
                            ${lastBackupFormatted}
                        </div>
                    </div>
                    <div>
                        <div class="text-[10px] text-slate-400">보관 용량</div>
                        <div class="text-[11px] font-mono text-emerald-400">
                            ${bytesFormatted} ${dev.total_files ? `(${dev.total_files.toLocaleString()}개)` : ''}
                        </div>
                    </div>
                    <div>
                        <div class="text-[10px] text-slate-400">저장소 디스크</div>
                        <div class="text-[11px] font-mono text-cyan-300">
                            ${diskFreeFormatted}
                        </div>
                    </div>
                </div>

                <div class="flex items-center justify-between text-[10px] text-slate-400 pt-1">
                    <span>자동 백업: <strong class="${dev.auto_backup_enabled ? 'text-emerald-400' : 'text-slate-400'}">${dev.auto_backup_enabled ? 'ON (09:00)' : '수동 백업 전용'}</strong></span>
                    <span class="text-[9px] text-slate-500">동기화: ${dev.last_updated || '-'}</span>
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
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

// 페이지 로드 시 Firebase 동기화 리스너 자동 기동
document.addEventListener('DOMContentLoaded', () => {
    // 0.5초 후 초기화하여 다른 코어 스크립트 로드 보장
    setTimeout(initFirebaseBackupSync, 500);
});
