# -*- coding: utf-8 -*-
"""
core/logging_setup.py - 백업 프로세스 공통 로깅 설정

왜 이 모듈이 필요한가 (실측 근거)
----------------------------------
Windows 작업 스케줄러는 백업을 다음처럼 실행한다:

    "pythonw.exe" "cli_backup.py" --profile "..."

pythonw.exe 에는 콘솔이 없다. 표준출력/표준오류가 연결되어 있지 않으므로
`print()` 한 줄은 어디에도 남지 않는다. 2026-10-07 09:00 백업이
"정상 종료(Result=0)" 하면서도 로그 파일이 하나도 생기지 않은 것이
정확히 이 때문이다.

`logging.FileHandler` 는 표준출력과 무관하게 파일에 쓰이므로,
일정 실행 로그는 반드시 logging 로 남겨야 한다.

설계 결정
----------
- 파일 로그는 `logs/backup.log` 한 곳에만 쓴다.
  일정 실행과 수동 실행이 같은 파일에 시간순으로 쌓이므로,
  "어제 야간 백업이 왜 실패했나" 를 한 파일만 열어 확인할 수 있다.
- 5MB 를 넘으면 1개로 회전하고 이전 파일은 지운다(백업 디스크 보호).
- 예외는 스택 트레이스까지 남긴다. 백업 실패 원인은 대부분 예외 안쪽에 있다.

사용법
------
    import logging
    from core.logging_setup import get_logger
    log = get_logger(__name__)
    log.info("...")
"""

import os
import logging
import logging.handlers

# 로그 파일 경로 (프로젝트 루트/logs)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(BASE_DIR, "logs")
BACKUP_LOG = os.path.join(LOG_DIR, "backup.log")

# 회전 임계값
_MAX_BYTES = 5 * 1024 * 1024   # 5MB
_BACKUP_COUNT = 1              # 이전 파일 1개만 보관

_CONFIGURED = False


def setup_file_logging(name: str = "backup", level: int = logging.INFO) -> logging.Logger:
    """
    logs/backup.log 로 쓰는 로거를 구성한다.

    여러 번 호출해도 파일 핸들러가 중복 생성되지 않는다.
    (스케줄러가 같은 프로필을 연속 실행할 때 로그가 2줄씩 중복되는 것을 방지)
    """
    global _CONFIGURED

    logger = logging.getLogger(name)

    if _CONFIGURED:
        return logger

    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except OSError:
        # 로그 디스크를 만들 수 없어도 백업 자체는 계속되어야 한다.
        # 표준출력으로라도 내보내고, 파일 로깅은 포기한다.
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        _CONFIGURED = True
        return logger

    handler = logging.handlers.RotatingFileHandler(
        BACKUP_LOG,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )

    logger.addHandler(handler)
    logger.setLevel(level)
    # 다른 곳에서 루트 로거를 INFO 로 올려도 이 로거의 레벨을 바꾸지 않는다.
    logger.propagate = False

    _CONFIGURED = True
    return logger


def get_logger(name: str = "backup", level: int = logging.INFO) -> logging.Logger:
    """모듈 로거를 얻는다. 최초 호출 시 파일 핸들러가 구성된다."""
    return setup_file_logging(name, level)


def log_path() -> str:
    """현재 백업 로그 파일 경로 (UI 표시용)."""
    return BACKUP_LOG