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
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'API request failed');
        }
        return await res.json();
    } catch (e) {
        console.error(`API Error (${url}):`, e);
        throw e;
    }
}

// Load Dashboard Data

// --- 공통 모달 제어 함수 ---
function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('hidden');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('hidden');
}

