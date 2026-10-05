// =========================================================================
// [백업시스템] 메인 오케스트레이터 & 대시보드 뷰 / 프로필 관리
// 서브 모듈: /static/js/backup_utils.js, backup_snapshots.js, backup_custom.js, backup_sysimage.js
// =========================================================================

// Tab Switching
function switchTab(tabId) {
    state.activeTab = tabId;
    document.querySelectorAll('.tab-btn').forEach(btn => {
        if (btn.dataset.tab === tabId) {
            btn.classList.add('bg-blue-600', 'text-white');
            btn.classList.remove('text-slate-400', 'hover:bg-slate-800');
        } else {
            btn.classList.remove('bg-blue-600', 'text-white');
            btn.classList.add('text-slate-400', 'hover:bg-slate-800');
        }
    });

    document.querySelectorAll('.tab-content').forEach(view => {
        view.classList.toggle('hidden', view.id !== `tab-${tabId}`);
    });

    if (tabId === 'snapshots') loadSnapshots();
    if (tabId === 'profiles') loadProfiles();
    if (tabId === 'dashboard') loadDashboard();
    if (tabId === 'custom') loadCustomSelectionData();
    if (tabId === 'system-image') loadSystemImageStatus();
}

// API Calls

async function loadDashboard() {
    try {
        const [sys, stats, profiles, snaps] = await Promise.all([
            fetchAPI('/api/system-info'),
            fetchAPI('/api/storage-stats'),
            fetchAPI('/api/profiles'),
            fetchAPI('/api/snapshots')
        ]);

        state.systemInfo = sys;
        state.storageStats = stats;
        state.profiles = profiles;
        state.snapshots = snaps;

        renderDashboardStats();
        renderRecentSnapshots();
        renderSystemDrives();
    } catch (err) {
        console.error('Failed to load dashboard:', err);
    }
}

function renderDashboardStats() {
    const stats = state.storageStats || {};
    document.getElementById('stat-total-snaps').innerText = stats.total_snapshots || '0';
    document.getElementById('stat-stored-bytes').innerText = formatBytes(stats.stored_bytes);
    document.getElementById('stat-logical-bytes').innerText = formatBytes(stats.logical_bytes);
    document.getElementById('stat-dedup-saved').innerText = `${formatBytes(stats.dedup_saved_bytes)} (${stats.savings_percentage || 0}%)`;

    // Active profiles count
    const activeProfCount = (state.profiles || []).filter(p => p.auto_backup_enabled).length;
    document.getElementById('stat-active-profiles').innerText = `${activeProfCount} / ${state.profiles.length}`;

    // Track 2-15: Chunking Telemetry
    const badgeEl = document.getElementById('stat-chunk-files-badge');
    const chunksEl = document.getElementById('stat-total-chunks');
    const stratEl = document.getElementById('stat-chunk-strategies');
    if (badgeEl) badgeEl.innerText = `청킹 파일: ${(stats.chunked_files_count || 0).toLocaleString()}개`;
    if (chunksEl) chunksEl.innerText = `${(stats.total_chunks || 0).toLocaleString()}개`;
    if (stratEl) {
        const strats = stats.chunk_strategies || {};
        const fastcdcCount = strats.fastcdc || strats.fastcdc_v1 || 0;
        const fixedCount = strats.fixed || strats.fixed_block || 0;
        stratEl.innerHTML = `
            <span class="px-1.5 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800/60 font-mono">FastCDC: ${fastcdcCount.toLocaleString()}</span>
            <span class="px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60 font-mono">Fixed: ${fixedCount.toLocaleString()}</span>
        `;
    }
}

function renderSystemDrives() {
    const container = document.getElementById('system-drives-list');
    if (!container || !state.systemInfo) return;

    container.innerHTML = state.systemInfo.drives.map(d => `
        <div class="p-3 bg-slate-800/80 rounded-xl border border-slate-700/60 flex flex-col gap-2">
            <div class="flex justify-between items-center text-xs">
                <span class="font-bold text-slate-200">${d.device} (${d.mountpoint})</span>
                <span class="text-slate-400">${d.percent}% 사용 중</span>
            </div>
            <div class="w-full bg-slate-900 rounded-full h-2 overflow-hidden">
                <div class="bg-gradient-to-r from-blue-500 to-indigo-500 h-2 rounded-full" style="width: ${Math.min(100, d.percent)}%"></div>
            </div>
            <div class="flex justify-between text-[11px] text-slate-400">
                <span>사용: ${formatBytes(d.used)}</span>
                <span>여유: ${formatBytes(d.free)}</span>
            </div>
        </div>
    `).join('');
}

function renderRecentSnapshots() {
    const container = document.getElementById('recent-snapshots-list');
    if (!container) return;

    if (!state.snapshots || state.snapshots.length === 0) {
        container.innerHTML = `
            <div class="text-center py-8 text-slate-500 text-sm">
                생성된 백업 스냅샷이 없습니다. 상단의 '지금 백업 시작' 버튼을 눌러 첫 백업을 생성하세요.
            </div>
        `;
        return;
    }

    const recents = state.snapshots.slice(0, 5);
    container.innerHTML = recents.map(s => {
        const isFull = s.backup_type === 'full';
        const sum = s.summary || {};
        return `
            <div class="p-4 bg-slate-800/60 hover:bg-slate-800 rounded-xl border border-slate-700/60 flex items-center justify-between transition-all">
                <div class="flex items-center gap-3">
                    <div class="p-2.5 rounded-lg ${isFull ? 'bg-blue-500/20 text-blue-400' : 'bg-emerald-500/20 text-emerald-400'}">
                        <i data-lucide="${isFull ? 'database' : 'layers'}" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="font-semibold text-sm text-slate-200">${s.profile_name || '백업'}</span>
                            <span class="text-[10px] px-2 py-0.5 rounded-full font-medium ${isFull ? 'bg-blue-900/60 text-blue-300 border border-blue-700' : 'bg-emerald-900/60 text-emerald-300 border border-emerald-700'}">
                                ${isFull ? 'FULL' : 'INCREMENTAL'}
                            </span>
                            ${s.vss_enabled ? '<span class="text-[10px] px-1.5 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800 font-semibold" title="Windows Volume Shadow Copy(VSS) 일관성 백업">VSS</span>' : ''}
                        </div>
                        <div class="text-xs text-slate-400 mt-0.5">
                            ${formatDate(s.iso_time)} · 파일 ${sum.total_files || 0}개 (${formatBytes(sum.total_bytes)})
                        </div>
                    </div>
                </div>
                <div class="flex items-center gap-2">
                    <button onclick="openRestoreModal('${s.id}')" class="px-3 py-1.5 bg-slate-700 hover:bg-blue-600 text-slate-200 hover:text-white rounded-lg text-xs font-medium transition flex items-center gap-1.5">
                        <i data-lucide="rotate-ccw" class="w-3.5 h-3.5"></i> 복원
                    </button>
                    <button onclick="inspectSnapshot('${s.id}')" class="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-xs font-medium transition">
                        탐색
                    </button>
                </div>
            </div>
        `;
    }).join('');

    lucide.createIcons();
}

// Snapshots Tab

// =========================================================================
// 백업 프로필 관리 & Windows 작업 스케줄러 & 디렉토리 브라우저
// =========================================================================

async function loadProfiles() {
    try {
        state.profiles = await fetchAPI('/api/profiles');
        renderProfilesList();
        await loadWindowsTaskStatus();
    } catch (e) {
        console.error('Failed to load profiles:', e);
    }
}

function renderProfilesList() {
    const container = document.getElementById('profiles-list-container');
    if (!container) return;

    if (!state.profiles || state.profiles.length === 0) {
        container.innerHTML = `<div class="text-slate-500 text-sm">등록된 프로필이 없습니다.</div>`;
        return;
    }

    container.innerHTML = state.profiles.map(p => {
        let nextRunText = '수동 실행';
        if (p.auto_backup_enabled) {
            if (p.last_run) {
                if (p.schedule_type === 'daily') {
                    nextRunText = `매일 ${p.schedule_value}`;
                } else {
                    const nextTs = p.last_run + (parseFloat(p.schedule_value || 24) * 3600);
                    nextRunText = formatDate(new Date(nextTs * 1000).toISOString());
                }
            } else {
                nextRunText = '대기 중 (즉시 실행)';
            }
        }

        return `
        <div class="p-5 bg-slate-800/70 rounded-2xl border border-slate-700/80 flex flex-col gap-4">
            <div class="flex justify-between items-start">
                <div>
                    <h3 class="text-base font-bold text-slate-100">${p.name}</h3>
                    <p class="text-xs text-slate-400 mt-1">저장소: <code class="text-blue-400 font-mono">${p.repo_dir}</code></p>
                </div>
                <div class="flex items-center gap-2">
                    <button onclick="editProfile('${p.id}')" class="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-xs font-medium">수정</button>
                    <button onclick="triggerProfileBackup('${p.id}')" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium">백업 실행</button>
                    <button onclick="deleteProfile('${p.id}', '${p.name.replace(/'/g, "\\'")}')" class="px-3 py-1.5 bg-red-900/60 hover:bg-red-600 text-red-300 hover:text-white rounded-lg text-xs font-medium transition">삭제</button>
                </div>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 bg-slate-900/60 p-3 rounded-xl text-xs">
                <div>
                    <span class="text-slate-500 block text-[11px]">스케줄 / 다음 예정</span>
                    <span class="font-medium text-slate-300">${p.auto_backup_enabled ? (p.schedule_type === 'daily' ? `매일 ${p.schedule_value}` : `${p.schedule_value}시간 주기`) : '수동 실행'}</span>
                    ${p.auto_backup_enabled ? `<span class="text-[10px] text-blue-400 font-mono block mt-0.5">다음: ${nextRunText}</span>` : ''}
                </div>
                <div>
                    <span class="text-slate-500 block text-[11px]">보관 개수</span>
                    <span class="font-medium text-slate-300">최근 ${p.retention_count}개 유지</span>
                </div>
                <div>
                    <span class="text-slate-500 block text-[11px]">압축 레벨</span>
                    <span class="font-medium text-slate-300">초고속 압축 (Level ${p.compression_level || 3})</span>
                </div>
                <div>
                    <span class="text-slate-500 block text-[11px]">최근 백업</span>
                    <span class="font-medium ${p.last_status === 'success' ? 'text-emerald-400' : p.last_status === 'failed' ? 'text-red-400' : 'text-slate-400'}">
                        ${p.last_run ? formatDate(new Date(p.last_run * 1000).toISOString()) : '기록 없음'}
                    </span>
                </div>
            </div>

            <details class="text-xs text-slate-400 bg-slate-900/40 p-3 rounded-xl border border-slate-800/80">
                <summary class="font-semibold text-slate-300 cursor-pointer flex items-center justify-between hover:text-white transition">
                    <span><i data-lucide="layers" class="w-3.5 h-3.5 inline text-blue-400 mr-1.5"></i> 백업 대상 경로 (${(p.sources || []).length}개 항목)</span>
                    <span class="text-[11px] text-slate-500 font-mono">클릭하여 경로 목록 보기</span>
                </summary>
                <ul class="list-disc list-inside mt-2.5 text-slate-400 font-mono text-[11px] max-h-36 overflow-y-auto space-y-1 pl-1">
                    ${(p.sources || []).map(s => `<li class="truncate hover:text-slate-200" title="${s}">${s}</li>`).join('')}
                </ul>
            </details>
        </div>
        `;
    }).join('');
    lucide.createIcons();
}

function onScheduleTypeChange() {
    const type = document.getElementById('prof-schedule-type').value;
    const intervalInput = document.getElementById('prof-interval');
    const dailyInput = document.getElementById('prof-daily-time');
    const label = document.getElementById('prof-schedule-label');

    if (type === 'daily') {
        label.innerText = '매일 백업할 시각 (HH:MM)';
        intervalInput.classList.add('hidden');
        dailyInput.classList.remove('hidden');
    } else {
        label.innerText = '반복 간격 (시간 단위)';
        dailyInput.classList.add('hidden');
        intervalInput.classList.remove('hidden');
    }
}

function openCreateProfileModal() {
    document.getElementById('profile-modal-title').innerText = '새 백업 프로필 생성';
    document.getElementById('prof-id').value = '';
    document.getElementById('prof-name').value = '새 백업 프로필';
    document.getElementById('prof-sources').value = '';
    document.getElementById('prof-repo').value = 'D:\\MyBackup_Repository';
    document.getElementById('prof-excludes').value = '*.tmp, *.log, .git, __pycache__, node_modules';
    document.getElementById('prof-schedule-type').value = 'interval_hours';
    document.getElementById('prof-interval').value = '24';
    document.getElementById('prof-daily-time').value = '03:00';
    document.getElementById('prof-auto-enable').checked = true;
    document.getElementById('prof-retention').value = '30';
    document.getElementById('prof-compression').value = '3';
    onScheduleTypeChange();
    openModal('profile-modal');
}

function editProfile(profileId) {
    const prof = state.profiles.find(p => p.id === profileId);
    if (!prof) return;

    document.getElementById('profile-modal-title').innerText = '백업 프로필 수정';
    document.getElementById('prof-id').value = prof.id;
    document.getElementById('prof-name').value = prof.name;
    document.getElementById('prof-sources').value = (prof.sources || []).join('\n');
    document.getElementById('prof-repo').value = prof.repo_dir || 'D:\\MyBackup_Repository';
    document.getElementById('prof-excludes').value = (prof.exclude_patterns || []).join(', ');
    
    const schedType = prof.schedule_type || 'interval_hours';
    document.getElementById('prof-schedule-type').value = schedType;
    if (schedType === 'daily') {
        document.getElementById('prof-daily-time').value = prof.schedule_value || '03:00';
    } else {
        document.getElementById('prof-interval').value = prof.schedule_value || '24';
    }
    document.getElementById('prof-auto-enable').checked = prof.auto_backup_enabled !== false;
    document.getElementById('prof-retention').value = prof.retention_count || 30;
    document.getElementById('prof-compression').value = prof.compression_level || 6;
    onScheduleTypeChange();
    openModal('profile-modal');
}

async function saveProfileFromModal() {
    const id = document.getElementById('prof-id').value.trim();
    const name = document.getElementById('prof-name').value.trim();
    const sourcesStr = document.getElementById('prof-sources').value.trim();
    const repo = document.getElementById('prof-repo').value.trim();
    const excludesStr = document.getElementById('prof-excludes').value.trim();
    const schedType = document.getElementById('prof-schedule-type').value;
    const schedValue = schedType === 'daily' 
        ? document.getElementById('prof-daily-time').value.trim() || '03:00' 
        : document.getElementById('prof-interval').value.trim() || '24';
    const autoEnable = document.getElementById('prof-auto-enable').checked;
    const retention = parseInt(document.getElementById('prof-retention').value.trim(), 10) || 30;
    const compression = parseInt(document.getElementById('prof-compression').value.trim(), 10) || 6;

    if (!name || !sourcesStr || !repo) {
        alert('프로필 이름, 백업 대상 경로, 저장소 경로를 모두 입력하세요.');
        return;
    }

    const sources = sourcesStr.split('\n').map(s => s.trim()).filter(s => s.length > 0);
    const excludes = excludesStr.split(',').map(s => s.trim()).filter(s => s.length > 0);

    const profileData = {
        id: id || undefined,
        name: name,
        sources: sources,
        repo_dir: repo,
        exclude_patterns: excludes,
        schedule_type: schedType,
        schedule_value: schedValue,
        auto_backup_enabled: autoEnable,
        retention_count: retention,
        compression_level: compression
    };

    try {
        await fetchAPI('/api/profiles', {
            method: 'POST',
            body: JSON.stringify(profileData)
        });
        closeModal('profile-modal');
        await loadProfiles();
        await loadDashboard();
    } catch (e) {
        alert('프로필 저장 실패: ' + e.message);
    }
}

async function triggerProfileBackup(profileId) {
    switchTab('runner');
    try {
        await fetchAPI('/api/backup/run', {
            method: 'POST',
            body: JSON.stringify({ profile_id: profileId })
        });
    } catch (e) {
        alert('백업 실행 실패: ' + e.message);
    }
}

async function deleteProfile(profileId, profileName) {
    if (!confirm(`'${profileName || profileId}' 백업 프로필을 정말 삭제하시겠습니까?`)) return;

    try {
        await fetchAPI(`/api/profiles/${profileId}`, { method: 'DELETE' });
        await loadProfiles();
        await loadDashboard();
    } catch (e) {
        alert('프로필 삭제 실패: ' + e.message);
    }
}

// Windows Task Scheduler Smart On/Off Handlers
async function loadWindowsTaskStatus() {
    try {
        const res = await fetchAPI('/api/windows-task/status');
        const badge = document.getElementById('windows-task-status-badge');
        const nextEl = document.getElementById('windows-task-next-run');
        if (!badge) return;

        if (res.registered) {
            badge.className = 'text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-700/60 flex items-center gap-1';
            badge.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> Windows OS 등록됨 (스마트 On/Off 활성)';
            if (nextEl) nextEl.innerText = `다음 자동 실행 예정: ${res.next_run || '-'}`;
        } else {
            badge.className = 'text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-slate-800 text-slate-400 border border-slate-700';
            badge.innerText = '미등록 (상시 데몬 모드)';
            if (nextEl) nextEl.innerText = '';
        }
    } catch (e) {
        console.error('Failed to load windows task status:', e);
    }
}

async function registerWindowsTaskFromUI() {
    const profiles = state.profiles || [];
    const activeProf = profiles.find(p => p.auto_backup_enabled) || (profiles.length > 0 ? profiles[0] : null);
    const profId = activeProf ? activeProf.id : 'prof_custom_selected';
    const schedType = activeProf ? activeProf.schedule_type || 'daily' : 'daily';
    const schedVal = activeProf ? activeProf.schedule_value || '03:00' : '03:00';

    try {
        const res = await fetchAPI('/api/windows-task/register', {
            method: 'POST',
            body: JSON.stringify({
                profile_id: profId,
                schedule_type: schedType,
                schedule_value: schedVal
            })
        });
        if (res.success) {
            alert(`🎉 Windows OS 작업 스케줄러에 등록 완료!\n\n- 스케줄: ${schedType === 'daily' ? '매일 ' + schedVal : schedVal + '시간 주기'}\n\n이제 파이썬 대시보드를 완전히 종료해 두셔도, 지정된 시간에 윈도우 OS가 백그라운드에서 1초 켜서 백업 후 즉시 자동 종료합니다.`);
            await loadWindowsTaskStatus();
        } else {
            alert('등록 실패: ' + res.error);
        }
    } catch (e) {
        alert('스케줄러 등록 오류: ' + e.message);
    }
}

async function unregisterWindowsTaskFromUI() {
    if (!confirm('Windows 작업 스케줄러 등록을 해제하시겠습니까?')) return;
    try {
        const res = await fetchAPI('/api/windows-task/unregister', { method: 'POST' });
        alert(res.message || '등록 해제되었습니다.');
        await loadWindowsTaskStatus();
    } catch (e) {
        alert('해제 오류: ' + e.message);
    }
}

// Maintenance
async function runGarbageCollection() {
    if (!confirm('저장소에서 참조되지 않는 고아 블롭을 정리하고 디스크 공간을 회수하시겠습니까?')) return;
    try {
        const res = await fetchAPI('/api/maintenance/prune', { method: 'POST' });
        alert(`🧹 정리 완료!\n삭제된 고아 블롭: ${res.deleted_blobs}개\n회수된 용량: ${formatBytes(res.freed_bytes)}`);
        await loadDashboard();
    } catch (e) {
        alert('정리 실패: ' + e.message);
    }
}

// Directory Browser Modal
function openDirectoryPicker(targetInputId) {
    state.browseModalCallback = (selectedPath) => {
        const input = document.getElementById(targetInputId);
        if (input) {
            if (input.tagName === 'TEXTAREA') {
                input.value = input.value ? `${input.value}\n${selectedPath}` : selectedPath;
            } else {
                input.value = selectedPath;
            }
        }
    };
    browseToDirectory("");
    openModal('browse-modal');
}

async function browseToDirectory(path) {
    try {
        const res = await fetchAPI('/api/browse-dir', {
            method: 'POST',
            body: JSON.stringify({ current_path: path })
        });

        state.currentBrowsePath = res.current_path;
        document.getElementById('browse-current-path').innerText = res.current_path || "시스템 드라이브 선택";

        const listContainer = document.getElementById('browse-items-list');
        let html = '';

        if (res.parent_path !== null && res.parent_path !== undefined) {
            html += `
                <div onclick="browseToDirectory('${res.parent_path.replace(/\\/g, '\\\\')}')" class="flex items-center gap-2 p-2 hover:bg-slate-800 rounded-lg cursor-pointer text-xs text-amber-400 font-semibold">
                    <i data-lucide="corner-left-up" class="w-4 h-4"></i> [상위 폴더로 이동]
                </div>
            `;
        }

        html += res.items.map(item => `
            <div class="flex items-center justify-between p-2 hover:bg-slate-800 rounded-lg text-xs transition">
                <div onclick="browseToDirectory('${item.path.replace(/\\/g, '\\\\')}')" class="flex items-center gap-2 cursor-pointer flex-1 overflow-hidden">
                    <i data-lucide="${item.name.includes(':') ? 'hard-drive' : 'folder'}" class="w-4 h-4 text-amber-400 shrink-0"></i>
                    <span class="truncate text-slate-200">${item.name}</span>
                </div>
                <button onclick="selectBrowsePath('${item.path.replace(/\\/g, '\\\\')}')" class="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[11px] font-medium shrink-0 ml-2">
                    선택
                </button>
            </div>
        `).join('');

        listContainer.innerHTML = html;
        lucide.createIcons();
    } catch (e) {
        console.error('Browse error:', e);
    }
}

function selectBrowsePath(path) {
    if (state.browseModalCallback) {
        state.browseModalCallback(path);
    }
    closeModal('browse-modal');
}

function selectCurrentBrowsePath() {
    if (state.currentBrowsePath && state.browseModalCallback) {
        state.browseModalCallback(state.currentBrowsePath);
    }
    closeModal('browse-modal');
}

// Custom Selection Tab Logic

// =========================================================================
// 시스템 종료 & 앱 초기화 진입점
// =========================================================================

async function shutdownServer() {
    if (!confirm('백업 대시보드 및 백그라운드 서비스를 완전히 종료하시겠습니까?\n(종료 후에는 start_backup_system.bat으로 언제든 다시 켤 수 있습니다)')) return;

    try {
        await fetchAPI('/api/system/shutdown', { method: 'POST' });
        alert('백업 서비스가 완전히 종료되었습니다. 이 브라우저 창을 닫으셔도 됩니다.');
        window.close();
    } catch (e) {
        alert('종료 완료: 브라우저 창을 닫아주세요.');
    }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    loadDashboard();

    const driveSelect = document.getElementById('sysimg-drive-select');
    if (driveSelect) {
        driveSelect.addEventListener('change', () => {
            loadSystemImageStatus();
        });
    }

    // Start polling every 1 second
    state.pollInterval = setInterval(() => {
        pollTaskStatus();
    }, 1000);
});
