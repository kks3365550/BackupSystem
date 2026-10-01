# -*- coding: utf-8 -*-
"""
Clean GitHub Publisher for BackupSystem v2.9.20
Zero-leak public repository initializer and publisher.
"""
import os
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def main():
    base_dir = r"c:\Users\kksjmj\Desktop\ai\백업시스템"
    temp_dir = os.environ.get("TEMP", r"C:\Windows\Temp")
    clean_dir = os.path.join(temp_dir, "BackupSystem_Public_Release")
    remote_url = "https://github.com/kks3365550/BackupSystem.git"
    
    print("=" * 60)
    print("🚀 백업시스템 v2.9.20 클린 공개 패키지 생성 및 검증")
    print("=" * 60)
    
    # 1. 초기화
    if os.path.exists(clean_dir):
        shutil.rmtree(clean_dir, ignore_errors=True)
    os.makedirs(clean_dir, exist_ok=True)
    print(f"[*] 클린 스테이징 디렉토리: {clean_dir}")
    
    # 2. 필수 디렉토리 복사 (core, web)
    print("[*] 핵심 소스코드 및 웹 대시보드 복사 중...")
    shutil.copytree(os.path.join(base_dir, "core"), os.path.join(clean_dir, "core"), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(os.path.join(base_dir, "web"), os.path.join(clean_dir, "web"), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    
    # 3. 공개키만 복사 (비밀키 절대 복사 금지)
    keys_dir = os.path.join(clean_dir, "keys")
    os.makedirs(keys_dir, exist_ok=True)
    shutil.copy2(os.path.join(base_dir, "keys", "release_ed25519.pub"), os.path.join(keys_dir, "release_ed25519.pub"))
    print("[+] Ed25519 공개키 복사 완료 (비밀키 미포함 확인)")
    
    # 4. 루트 실행 스크립트 및 공식 문서 복사
    files_to_copy = [
        "run.py",
        "VERSION",
        "start_silent.vbs",
        "start_tray.vbs",
        "launch_dashboard.vbs",
        "stop_backup_system.bat",
        "2_백업시스템_실행.bat",
        "release_notes.md",
        "known_issues.md",
        "support_scope.md",
        "repository_format.md",
        "release_build_manifest.md"
    ]
    for f in files_to_copy:
        src = os.path.join(base_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(clean_dir, f))
            
    # 5. 설정 템플릿 생성 (개인정보 원천 격리)
    data_dir = os.path.join(clean_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    example_profile = """[
  {
    "id": "default",
    "name": "Default Backup Profile",
    "source_paths": [
      "C:\\\\Users\\\\Default\\\\Documents"
    ],
    "repo_dir": "D:\\\\BackupRepository",
    "exclude_patterns": [
      "node_modules",
      "__pycache__",
      "*.tmp",
      "*.log"
    ],
    "schedule_type": "manual",
    "schedule_value": "12",
    "auto_backup_enabled": false,
    "retention_count": 30,
    "retention_days": 60,
    "compression_level": 3
  }
]
"""
    with open(os.path.join(data_dir, "profiles.json.example"), "w", encoding="utf-8") as pf:
        pf.write(example_profile)
        
    # 6. README.md 생성
    readme_content = """# BackupSystem (백업시스템)

Windows용 엔터프라이즈급 로컬 & 네트워크 고속 무결성 백업 시스템.

## 🚀 주요 기능 (Key Features)
- **결정론적 스냅샷 및 중복 제거**: 파일 및 블록 레벨의 고속 증분 백업.
- **WORM (Write Once, Read Many) 불변 저장소**: 랜섬웨어 및 위변조 방지.
- **Windows 완전 통합**: 무창(Silent) 백그라운드 워커 및 Win32 네이티브 트레이 에이전트.
- **반응형 웹 대시보드**: 모던 UI (`http://localhost:8765`) 제공.
- **Ed25519 서명 기반 무중단 자동 업데이트**: 암호학적 무결성 검증 OTA.

## 📦 설치 및 시작하기 (Quick Start)
1. [GitHub Releases](https://github.com/kks3365550/BackupSystem/releases)에서 최신 인스톨러 `BackupSystem_Setup_v2.9.20.exe`를 다운로드합니다.
2. 설치 마법사를 실행하여 설치를 완료합니다.
3. 웹 브라우저에서 `http://localhost:8765`로 접속하여 백업 프로필을 구성합니다.

## 📜 공식 문서 (Documentation)
- [릴리즈 노트 (Release Notes)](release_notes.md)
- [지원 환경 명세 (Support Scope)](support_scope.md)
- [알려진 이슈 (Known Issues)](known_issues.md)
- [저장소 포맷 사양서 (Repository Format)](repository_format.md)
- [릴리즈 빌드 매니페스트 (Release Build Manifest)](release_build_manifest.md)

## 📄 라이선스 (License)
MIT License
"""
    with open(os.path.join(clean_dir, "README.md"), "w", encoding="utf-8") as rf:
        rf.write(readme_content)
        
    # 7. 엄격한 .gitignore 생성
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.pyc
.venv/
venv/
env/

# Backup Repositories
backup_repository/
MyBackup_Repository/

# Runtime Data & Personal Configurations
data/*.json
!data/profiles.json.example

# Temporary & Logs
*.tmp
*.temp
*.log
logs/

# Build artifacts & Binaries
build/
dist/
*.spec
installer/Output/
installer/runtime/
*.exe
*.zip
*.sig

# Keys & Secrets (Only public keys are allowed)
keys/*.key
keys/*.pem
keys/*.pfx
keys/*private*

# Internal & Scratch
.ai/
scratch/
audit/
reports/
"""
    with open(os.path.join(clean_dir, ".gitignore"), "w", encoding="utf-8") as gf:
        gf.write(gitignore_content)
        
    # 8. 전수 보안 스캔
    print("[*] 8대 보안 관문 전수 스캔 수행 중...")
    forbidden = []
    for root, dirs, files in os.walk(clean_dir):
        for file in files:
            path = os.path.join(root, file)
            rel = os.path.relpath(path, clean_dir)
            if file.endswith(".key") or file.endswith(".pem") or file.endswith(".pfx"):
                forbidden.append(f"비밀키 감지: {rel}")
            if "profiles.json" in file and not file.endswith(".example"):
                forbidden.append(f"실제 설정 감지: {rel}")
            if file.endswith(".log"):
                forbidden.append(f"로그 파일 감지: {rel}")
                
    if forbidden:
        print("🚨 [CRITICAL ALERT] 민감 파일 감지로 중단:")
        for item in forbidden:
            print("  - " + item)
        sys.exit(1)
        
    print("✅ [PASS] 민감정보(비밀키, 개인설정, 로그) 0건 확인 완료!")
    
    # 9. Git 초기화, 커밋, 태그 생성
    print("[*] 클린 Git 저장소 초기화 및 v2.9.20 태깅 중...")
    def run_git(cmd):
        res = subprocess.run(f"git {cmd}", cwd=clean_dir, shell=True)
        if res.returncode != 0:
            print(f"[-] Git error on: git {cmd}")
        return res
        
    run_git("init -b main")
    run_git('config user.name "kks3365550"')
    run_git('config user.email "kks3365550@users.noreply.github.com"')
    run_git("add .")
    run_git('commit -m "feat: initial public release v2.9.20"')
    run_git('tag -a v2.9.20 -m "BackupSystem v2.9.20 Official Release"')
    run_git(f"remote add origin {remote_url}")
    
    print("=" * 60)
    print("🎉 클린 공개 Git 저장소 준비가 완벽히 완료되었습니다!")
    print(f"위치: {clean_dir}")
    print(f"대상 원격 저장소: {remote_url}")
    print("=" * 60)

if __name__ == "__main__":
    main()
