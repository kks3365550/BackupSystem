# 📋 백업시스템 v2.9.20 릴리즈 빌드 매니페스트 (Release Build Manifest)

> **빌드 일자**: 2026-09-30  
> **공식 버전**: `2.9.20`  
> **Git 태그**: `v2.9.20`  
> **컴파일러**: Inno Setup 6.7.3 (Modern Wizard, LZMA2/Ultra64, 64-bit Native)

---

## 1. 공식 배포 바이너리 정보

### 1) 통합 인스톨러 (Full Setup Installer)
- **파일명**: `BackupSystem_Setup_v2.9.20.exe`
- **파일 크기**: `35,034,280 bytes` (약 33.4 MB)
- **SHA-256 Checksum**:
  ```text
  482CB080806EAAFC02D46EBE0D67021878656C2D6A76B9C1739DF12B7B958E3E
  ```
- **포함 런타임**:
  - Embedded Python 3.11 x64 Self-Contained 런타임
  - FastAPI / Uvicorn 백엔드 서버
  - Win32 ctypes 네이티브 트레이 에이전트
  - VBScript 무창(Silent) 실행기

### 2) 독립 자동 업데이트 패키지 (Auto-Update Package)
- **파일명**: `release_v2.9.20.zip`
- **파일 크기**: `439,912 bytes`
- **디지털 서명 파일**: `release_v2.9.20.zip.sig` (Ed25519)
- **공개키 위치**: `keys/release_ed25519.pub`
- **Zero-Leak 감사**: 통과 (개인키 및 인증서 파일 0건 포함)

---

## 2. 무결성 및 출시 합격 판정 (Go/No-Go Gate)

- [x] **Release Blocking 결함**: `0건` (RELEASE FIX = 0)
- [x] **SHA-256 체크섬**: 일치 및 고정 완료
- [x] **Ed25519 디지털 서명**: 정상 검증 완료
- [x] **Windows Sandbox QA 도구**: `tools/sandbox_test.wsb` 준비 완료
- [x] **격리 Dry-Run**: 백업 ➔ 자동 검증 ➔ 복원 ➔ SHA-256 100% 일치 통과
- [x] **기존 운영 저장소 보호**: 완전 분리 및 오염 0건 보장

**최종 판정**: **GO (Commercial Release Approved)**
