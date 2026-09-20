// =========================================================================
// [백업시스템] 마스터 비밀번호 인증 / 세션 관리 / 모달 제어 서브시스템
// =========================================================================

let _authStatus = {
    configured: false,
    authenticated: false,
    bypassed: false,
    allow_localhost_bypass: true
};

async function checkAuthStatus() {
    try {
        const res = await fetch('/api/auth/status');
        if (!res.ok) return;
        const data = await res.json();
        if (data.success) {
            _authStatus = data.data;
            updateAuthBadgeUI();
            if (!_authStatus.configured) {
                openAuthSetupModal();
            } else if (!_authStatus.authenticated && !_authStatus.bypassed) {
                openAuthLoginModal();
            }
        }
    } catch (e) {
        console.warn('Auth status check error:', e);
    }
}

function updateAuthBadgeUI() {
    const label = document.getElementById('auth-badge-label');
    const icon = document.getElementById('auth-badge-icon');
    const bypassTag = document.getElementById('auth-bypass-status-tag');
    
    if (bypassTag) {
        bypassTag.innerText = _authStatus.allow_localhost_bypass ? 'ON' : 'OFF';
        bypassTag.className = _authStatus.allow_localhost_bypass 
            ? 'text-[10px] px-1.5 py-0.5 rounded bg-blue-900/60 text-blue-300 font-mono'
            : 'text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono';
    }

    if (!label || !icon) return;

    if (!_authStatus.configured) {
        label.innerText = '미설정';
        icon.setAttribute('data-lucide', 'shield-alert');
        icon.className = 'w-3.5 h-3.5 text-amber-400';
    } else if (_authStatus.authenticated) {
        label.innerText = '보안 인증됨';
        icon.setAttribute('data-lucide', 'shield-check');
        icon.className = 'w-3.5 h-3.5 text-emerald-400';
    } else if (_authStatus.bypassed) {
        label.innerText = '로컬 자동인증';
        icon.setAttribute('data-lucide', 'laptop');
        icon.className = 'w-3.5 h-3.5 text-blue-400';
    } else {
        label.innerText = '인증 필요';
        icon.setAttribute('data-lucide', 'lock');
        icon.className = 'w-3.5 h-3.5 text-amber-400';
    }
    lucide.createIcons();
}

function toggleAuthDropdown() {
    const dd = document.getElementById('auth-dropdown');
    if (dd) dd.classList.toggle('hidden');
}

// 외부 클릭 시 드롭다운 닫기
document.addEventListener('click', (e) => {
    const wrapper = document.getElementById('auth-badge-wrapper');
    const dd = document.getElementById('auth-dropdown');
    if (wrapper && dd && !wrapper.contains(e.target)) {
        dd.classList.add('hidden');
    }
});

function openAuthSetupModal() {
    const overlay = document.getElementById('auth-modal-overlay');
    const setupModal = document.getElementById('modal-auth-setup');
    const loginModal = document.getElementById('modal-auth-login');
    const changeModal = document.getElementById('modal-auth-change');
    if (overlay) overlay.classList.remove('hidden');
    if (setupModal) setupModal.classList.remove('hidden');
    if (loginModal) loginModal.classList.add('hidden');
    if (changeModal) changeModal.classList.add('hidden');
    setTimeout(() => document.getElementById('setup-password')?.focus(), 100);
}

function openAuthLoginModal() {
    const overlay = document.getElementById('auth-modal-overlay');
    const setupModal = document.getElementById('modal-auth-setup');
    const loginModal = document.getElementById('modal-auth-login');
    const changeModal = document.getElementById('modal-auth-change');
    if (overlay) overlay.classList.remove('hidden');
    if (setupModal) setupModal.classList.add('hidden');
    if (loginModal) loginModal.classList.remove('hidden');
    if (changeModal) changeModal.classList.add('hidden');
    setTimeout(() => document.getElementById('login-password')?.focus(), 100);
}

function openAuthChangeModal() {
    toggleAuthDropdown();
    const overlay = document.getElementById('auth-modal-overlay');
    const setupModal = document.getElementById('modal-auth-setup');
    const loginModal = document.getElementById('modal-auth-login');
    const changeModal = document.getElementById('modal-auth-change');
    if (overlay) overlay.classList.remove('hidden');
    if (setupModal) setupModal.classList.add('hidden');
    if (loginModal) loginModal.classList.remove('hidden');
    if (changeModal) changeModal.classList.add('hidden');
    setTimeout(() => document.getElementById('change-current')?.focus(), 100);
}

function closeAuthModal() {
    const overlay = document.getElementById('auth-modal-overlay');
    if (overlay) overlay.classList.add('hidden');
}

async function submitAuthSetup(e) {
    e.preventDefault();
    const p1 = document.getElementById('setup-password').value;
    const p2 = document.getElementById('setup-password-confirm').value;
    const bypass = document.getElementById('setup-remember').checked;
    const errDiv = document.getElementById('setup-error');

    if (p1 !== p2) {
        errDiv.innerText = '비밀번호가 일치하지 않습니다.';
        errDiv.classList.remove('hidden');
        return;
    }

    try {
        const res = await fetch('/api/auth/setup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: p1, allow_localhost_bypass: bypass })
        });
        const data = await res.json();
        if (!res.ok) {
            errDiv.innerText = data.error || '설정 중 오류가 발생했습니다.';
            errDiv.classList.remove('hidden');
            return;
        }
        await submitAuthLoginDirect(p1);
    } catch (err) {
        errDiv.innerText = '통신 오류가 발생했습니다.';
        errDiv.classList.remove('hidden');
    }
}

async function submitAuthLogin(e) {
    e.preventDefault();
    const pw = document.getElementById('login-password').value;
    await submitAuthLoginDirect(pw);
}

async function submitAuthLoginDirect(password) {
    const errDiv = document.getElementById('login-error');
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });
        const data = await res.json();
        if (!res.ok) {
            if (errDiv) {
                errDiv.innerText = data.error || '비밀번호가 올바르지 않습니다.';
                errDiv.classList.remove('hidden');
            }
            return;
        }
        closeAuthModal();
        await checkAuthStatus();
        if (typeof loadDashboard === 'function') loadDashboard();
    } catch (err) {
        if (errDiv) {
            errDiv.innerText = '로그인 중 오류가 발생했습니다.';
            errDiv.classList.remove('hidden');
        }
    }
}

async function submitAuthLogout() {
    toggleAuthDropdown();
    if (!confirm('로그아웃 하시겠습니까?')) return;
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        await checkAuthStatus();
        openAuthLoginModal();
    } catch (e) {
        console.error('Logout error:', e);
    }
}

async function submitAuthChangePassword(e) {
    e.preventDefault();
    const oldP = document.getElementById('change-current').value;
    const newP1 = document.getElementById('change-new').value;
    const newP2 = document.getElementById('change-new-confirm').value;
    const errDiv = document.getElementById('change-error');

    if (newP1 !== newP2) {
        errDiv.innerText = '새 비밀번호가 서로 일치하지 않습니다.';
        errDiv.classList.remove('hidden');
        return;
    }

    try {
        const res = await fetch('/api/auth/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_password: oldP, new_password: newP1 })
        });
        const data = await res.json();
        if (!res.ok) {
            errDiv.innerText = data.error || '비밀번호 변경 실패';
            errDiv.classList.remove('hidden');
            return;
        }
        alert('비밀번호가 성공적으로 변경되었습니다. 다시 로그인해주세요.');
        closeAuthModal();
        openAuthLoginModal();
    } catch (err) {
        errDiv.innerText = '통신 오류가 발생했습니다.';
        errDiv.classList.remove('hidden');
    }
}

async function toggleLocalhostBypass() {
    toggleAuthDropdown();
    const newState = !_authStatus.allow_localhost_bypass;
    try {
        const res = await fetch('/api/auth/toggle-bypass', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: newState })
        });
        if (res.ok) {
            await checkAuthStatus();
        }
    } catch (e) {
        console.error('Toggle bypass error:', e);
    }
}

// 자동 초기화: DOM 로드 시 인증 상태 점검
document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
});
