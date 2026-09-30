// =========================================================================
// [백업시스템] 공통 상태 저장소 & 포맷팅 유틸리티 & API 통신 & 모달 제어
// =========================================================================

// State Management
const state = {
    activeTab: 'dashboard',
    systemInfo: null,
    storageStats: null,
    profiles: [],
    selectedProfileId: null,
    snapshots: [],
    selectedSnapshot: null,
    selectedSnapshotTree: null,
    taskStatus: { running: false, type: null, progress: {} },
    pollInterval: null,
    browseModalCallback: null,
    currentBrowsePath: "",
    installedApps: [],
    selectedAppPaths: new Set(),
    aiProjects: [],
    selectedProjectPaths: new Set(),
    customFolders: []
};

// Utilities
function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(isoStr) {
    if (!isoStr) return '-';
    const d = new Date(isoStr);
    return d.toLocaleString('ko-KR', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
}

async function fetchAPI(url, options = {}) {
    try {
        const res = await fetch(url, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        if (res.status === 401) {
            if (typeof openAuthLoginModal === 'function' && !url.includes('/api/auth/status')) {
                openAuthLoginModal();
            }
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || '인증이 필요합니다.');
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || err.error || 'API request failed');
        }
        return await res.json();
    } catch (e) {
        console.error(`API Error (${url}):`, e);
        throw e;
    }
}

// --- 공통 모달 제어 함수 ---
function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('hidden');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('hidden');
}

// --- 글로벌 경보 배너 시스템 (Red Alert System) ---
let _bannerDismissedUntil = 0;

async function checkGlobalAlerts() {
    if (Date.now() < _bannerDismissedUntil) return;

    try {
        const res = await fetchAPI('/api/alerts/summary');
        const banner = document.getElementById('global-alert-banner');
        if (!banner || !res || !res.success) return;

        const data = res.data || {};
        const status = data.status || 'ok';
        const alerts = data.alerts || [];

        const badge = document.getElementById('alert-banner-badge');
        const statusText = document.getElementById('alert-banner-status');
        const msgText = document.getElementById('alert-banner-message');

        if (status === 'critical' && alerts.length > 0) {
            banner.className = 'shrink-0 border-b border-red-700/80 bg-red-950/90 px-6 py-2.5 flex items-center justify-between text-xs z-30 transition-all duration-300';
            if (badge) badge.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-sm bg-red-600 text-white animate-pulse';
            if (statusText) statusText.innerText = '심각 경보 (CRITICAL)';
            const topAlert = alerts[0];
            const extraCount = alerts.length > 1 ? ` (외 ${alerts.length - 1}건)` : '';
            if (msgText) msgText.innerText = `[${topAlert.title || '경보'}] ${topAlert.message}${extraCount}`;
            banner.classList.remove('hidden');
        } else if (status === 'warning' && alerts.length > 0) {
            banner.className = 'shrink-0 border-b border-amber-700/80 bg-amber-950/90 px-6 py-2.5 flex items-center justify-between text-xs z-30 transition-all duration-300';
            if (badge) badge.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-sm bg-amber-500 text-slate-950 font-bold';
            if (statusText) statusText.innerText = '주의 경보 (WARNING)';
            const topAlert = alerts[0];
            const extraCount = alerts.length > 1 ? ` (외 ${alerts.length - 1}건)` : '';
            if (msgText) msgText.innerText = `[${topAlert.title || '주의'}] ${topAlert.message}${extraCount}`;
            banner.classList.remove('hidden');
        } else {
            banner.classList.add('hidden');
        }
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        // 알림 조회 실패 시 무시
    }
}

function dismissAlertBanner() {
    const banner = document.getElementById('global-alert-banner');
    if (banner) banner.classList.add('hidden');
    _bannerDismissedUntil = Date.now() + 5 * 60 * 1000;
}

// --- 원격 마스터 릴리즈 동기화 (One-Click Remote Sync) ---
let _remoteReleaseDismissed = false;

async function checkRemoteRelease() {
    try {
        const res = await fetchAPI('/api/system/check-remote-release');
        const banner = document.getElementById('remote-release-banner');
        const statusBadge = document.getElementById('header-release-status');
        const statusText = document.getElementById('header-release-text');
        const statusIcon = document.getElementById('header-release-icon');

        if (!res || !res.success) return;
        const data = res.data || {};

        if (data.current_version) {
            const versionBadge = document.getElementById('header-version-badge');
            if (versionBadge) {
                const versionStr = data.current_version.startsWith('v') ? data.current_version : 'v' + data.current_version;
                versionBadge.innerText = versionStr;
            }
        }

        if (data.is_self) {
            // 마스터 서버 자신 (K12)
            if (statusBadge && statusText && statusIcon) {
                statusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium flex items-center gap-1 border bg-blue-500/10 text-blue-400 border-blue-500/30';
                statusIcon.setAttribute('data-lucide', 'server');
                statusText.innerText = '마스터 오리진';
                statusBadge.title = '현재 PC가 릴리즈 마스터 서버(K12)입니다.';
                statusBadge.classList.remove('hidden');
            }
            if (banner) banner.classList.add('hidden');
        } else if (data.update_available) {
            // 새 릴리즈 있음
            if (statusBadge && statusText && statusIcon) {
                statusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium flex items-center gap-1 border bg-indigo-500/20 text-indigo-300 border-indigo-500/40 animate-pulse';
                statusIcon.setAttribute('data-lucide', 'sparkles');
                statusText.innerText = `새 버전 ${data.remote_version}`;
                statusBadge.title = `마스터 서버(K12)에 새로운 릴리즈 ${data.remote_version}이 있습니다.`;
                statusBadge.classList.remove('hidden');
            }
            if (banner && !_remoteReleaseDismissed) {
                const textElem = document.getElementById('remote-release-text');
                if (textElem) {
                    textElem.innerText = `마스터 서버(K12)에 최신 릴리즈 ${data.remote_version}이 감지되었습니다. (현재 버전: v${data.current_version})`;
                }
                banner.classList.remove('hidden');
            }
        } else {
            // 버전 동일 (최신 버전 상태!)
            if (statusBadge && statusText && statusIcon) {
                statusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium flex items-center gap-1 border bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
                statusIcon.setAttribute('data-lucide', 'check-check');
                statusText.innerText = '최신 버전';
                statusBadge.title = '마스터 서버(K12)와 버전이 일치하는 최신 상태입니다.';
                statusBadge.classList.remove('hidden');
            }
            if (banner) banner.classList.add('hidden');
        }
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        // 원격 조회 실패 시 조용히 스킵
    }
}

function dismissRemoteReleaseBanner() {
    const banner = document.getElementById('remote-release-banner');
    if (banner) banner.classList.add('hidden');
    _remoteReleaseDismissed = true;
}

async function triggerRemoteReleaseSync() {
    const btn = document.getElementById('btn-sync-remote-release');
    const btnText = document.getElementById('sync-btn-text');
    const btnIcon = document.getElementById('sync-btn-icon');

    if (!confirm('마스터 서버(K12)로부터 최신 릴리즈를 다운로드하여 동기화하시겠습니까?\n\n서명 무결성 검증 후 1~2초 내에 백그라운드 엔진이 안전하게 재시작됩니다.')) {
        return;
    }

    if (btn) btn.disabled = true;
    if (btnText) btnText.innerText = '동기화 중...';
    if (btnIcon) btnIcon.classList.add('animate-spin');

    try {
        const res = await fetchAPI('/api/system/sync-remote-release', {
            method: 'POST',
            body: JSON.stringify({ master_url: 'http://100.72.224.71:8765' })
        });

        alert(res.message || '최신 릴리즈 동기화가 성공적으로 완료되었습니다! 3초 후 대시보드가 새로고침됩니다.');
        setTimeout(() => {
            window.location.reload();
        }, 3000);
    } catch (err) {
        alert('동기화 실패: ' + (err.message || '알 수 없는 오류가 발생했습니다.'));
        if (btn) btn.disabled = false;
        if (btnText) btnText.innerText = '최신 릴리즈 동기화';
        if (btnIcon) btnIcon.classList.remove('animate-spin');
    }
}

// 10초마다 자동 경보 점검 및 60초마다 원격 릴리즈 점검
document.addEventListener('DOMContentLoaded', () => {
    checkGlobalAlerts();
    setInterval(checkGlobalAlerts, 10000);

    checkRemoteRelease();
    setInterval(checkRemoteRelease, 60000);
});
