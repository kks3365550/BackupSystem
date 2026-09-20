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

// 10초마다 자동 경보 점검
document.addEventListener('DOMContentLoaded', () => {
    checkGlobalAlerts();
    setInterval(checkGlobalAlerts, 10000);
});
