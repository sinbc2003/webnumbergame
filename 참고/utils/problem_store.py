import json
from pathlib import Path
import sys
import os

# PyInstaller로 빌드된 exe 파일인지 확인
if getattr(sys, 'frozen', False):
    # exe 파일이 실행되는 디렉토리 사용
    BASE_DIR = Path(sys.executable).parent
else:
    # 개발 환경에서는 프로젝트 루트 사용
    BASE_DIR = Path(__file__).resolve().parent.parent

# 설정 파일들을 저장할 디렉토리 생성
SETTINGS_DIR = BASE_DIR / "game_settings"
SETTINGS_DIR.mkdir(exist_ok=True)

PROBLEM_FILE = SETTINGS_DIR / "custom_problems.json"
# default fallback cost map
DEFAULT_COSTS = {'(': 1, ')': 1, '1': 1, '+': 2, '*': 3}

# cost settings file
COST_FILE = SETTINGS_DIR / "custom_costs.json"

# team mode settings file
TEAM_MODE_FILE = SETTINGS_DIR / "team_mode_settings.json"

# team mode problems file (목표 숫자 목록)
TEAM_PROBLEMS_FILE = SETTINGS_DIR / "team_problems.json"

# team mode costs file (팀전용 기호별 코스트)
TEAM_COSTS_FILE = SETTINGS_DIR / "team_costs.json"

# timer settings file (라운드별 시간 설정)
TIMER_SETTINGS_FILE = SETTINGS_DIR / "timer_settings.json"

# team cost range file (팀전 학생당 코스트 범위)
TEAM_COST_RANGE_FILE = SETTINGS_DIR / "team_cost_range.json"

# strategy meeting time file (작전회의 시간)
STRATEGY_TIME_FILE = SETTINGS_DIR / "strategy_time.json"

# reset limit file (초기화 횟수 제한)
RESET_LIMIT_FILE = SETTINGS_DIR / "reset_limit.json"

# 1라운드 모드 I, II 문제 파일
MODE1_PROBLEMS_FILE = SETTINGS_DIR / "mode1_problems.json"
MODE2_PROBLEMS_FILE = SETTINGS_DIR / "mode2_problems.json"

# 네트워크 대전 전용 문제 파일
NETWORK_MODE1_PROBLEMS_FILE = SETTINGS_DIR / "network_mode1_problems.json"
NETWORK_MODE2_PROBLEMS_FILE = SETTINGS_DIR / "network_mode2_problems.json"
NETWORK_TEAM_PROBLEMS_FILE = SETTINGS_DIR / "network_team_problems.json"

# 1라운드 모드 I, II 기호별 코스트 파일
MODE1_COSTS_FILE = SETTINGS_DIR / "mode1_costs.json"
MODE2_COSTS_FILE = SETTINGS_DIR / "mode2_costs.json"



def load_problems() -> list:
    """Load problems list from JSON file. Returns list of dictionaries or integers."""
    if PROBLEM_FILE.exists():
        try:
            data = json.loads(PROBLEM_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                result = []
                for item in data:
                    if isinstance(item, dict) and 'target' in item:
                        # 딕셔너리 형식 그대로 유지
                        result.append(item)
                    elif isinstance(item, (int, float, str)):
                        # 단순 정수는 딕셔너리로 변환
                        result.append({'target': int(item)})
                return result
        except Exception:
            pass
    return []

def save_problems(problems: list):
    """Save list of problems to JSON file. Each problem can be a dict or int."""
    # 정수로만 된 리스트를 딕셔너리 리스트로 변환
    formatted_problems = []
    for p in problems:
        if isinstance(p, dict):
            formatted_problems.append(p)
        else:
            formatted_problems.append({'target': int(p)})
    PROBLEM_FILE.write_text(json.dumps(formatted_problems, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------- Cost settings ----------------

def load_costs() -> dict:
    if COST_FILE.exists():
        try:
            data = json.loads(COST_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {k: int(v) for k, v in data.items()}
        except Exception:
            pass
    return DEFAULT_COSTS.copy()


def save_costs(costs: dict):
    COST_FILE.write_text(json.dumps(costs, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------- Team mode settings ----------------

def load_team_mode_settings() -> dict:
    """팀전모드 설정 로드: total_cost, target_number"""
    if TEAM_MODE_FILE.exists():
        try:
            data = json.loads(TEAM_MODE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    'total_cost': int(data.get('total_cost', 100)),
                    'target_number': int(data.get('target_number', 25))
                }
        except Exception:
            pass
    return {'total_cost': 100, 'target_number': 25}

def save_team_mode_settings(total_cost: int, target_number: int):
    """팀전모드 설정 저장"""
    data = {
        'total_cost': total_cost,
        'target_number': target_number
    }
    TEAM_MODE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------- Team mode problems (목표 숫자 목록) ----------------

def load_team_problems() -> list[int]:
    """팀전모드 목표 숫자 목록 로드"""
    if TEAM_PROBLEMS_FILE.exists():
        try:
            data = json.loads(TEAM_PROBLEMS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [int(x) for x in data if isinstance(x, (int, float, str))]
        except Exception:
            pass
    return [25, 50, 75, 100]  # 기본값

def save_team_problems(problems: list[int]):
    """팀전모드 목표 숫자 목록 저장"""
    TEAM_PROBLEMS_FILE.write_text(json.dumps(problems, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------- Team mode costs (팀전용 기호별 코스트) ----------------

def load_team_costs() -> dict:
    """팀전용 기호별 코스트 로드"""
    if TEAM_COSTS_FILE.exists():
        try:
            data = json.loads(TEAM_COSTS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {k: int(v) for k, v in data.items()}
        except Exception:
            pass
    return DEFAULT_COSTS.copy()  # 기본값

def save_team_costs(costs: dict):
    """팀전용 기호별 코스트 저장"""
    TEAM_COSTS_FILE.write_text(json.dumps(costs, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------- Timer settings ----------------

def load_timer_settings() -> dict:
    """라운드별 타이머 설정 로드"""
    if TIMER_SETTINGS_FILE.exists():
        try:
            data = json.loads(TIMER_SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    'round1_minutes': int(data.get('round1_minutes', 3)),
                    'round2_minutes': int(data.get('round2_minutes', 8)),
                    'coin_distribution_minutes': int(data.get('coin_distribution_minutes', 10)),
                    'mode1_minutes': int(data.get('mode1_minutes', data.get('round1_minutes', 3))),
                    'mode2_minutes': int(data.get('mode2_minutes', 5))
                }
        except Exception:
            pass
    return {'round1_minutes': 3, 'round2_minutes': 8, 'coin_distribution_minutes': 10, 'mode1_minutes': 3, 'mode2_minutes': 5}  # 기본값

def save_timer_settings(round1_minutes: int = None, round2_minutes: int = None, coin_distribution_minutes: int = None, mode1_minutes: int = None, mode2_minutes: int = None):
    """라운드별 타이머 설정 저장"""
    # 기존 설정 로드
    current = load_timer_settings()
    
    # 새로운 값만 업데이트
    data = {
        'round1_minutes': round1_minutes if round1_minutes is not None else current['round1_minutes'],
        'round2_minutes': round2_minutes if round2_minutes is not None else current['round2_minutes'],
        'coin_distribution_minutes': coin_distribution_minutes if coin_distribution_minutes is not None else current['coin_distribution_minutes'],
        'mode1_minutes': mode1_minutes if mode1_minutes is not None else current['mode1_minutes'],
        'mode2_minutes': mode2_minutes if mode2_minutes is not None else current['mode2_minutes']
    }
    TIMER_SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------- Team cost range settings ----------------

def load_team_cost_range() -> dict:
    """팀전 학생당 코스트 범위 설정 로드"""
    if TEAM_COST_RANGE_FILE.exists():
        try:
            data = json.loads(TEAM_COST_RANGE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    'min_cost': int(data.get('min_cost', 10)),
                    'max_cost': int(data.get('max_cost', 50))
                }
        except Exception:
            pass
    return {'min_cost': 10, 'max_cost': 50}  # 기본값

def save_team_cost_range(min_cost: int, max_cost: int):
    """팀전 학생당 코스트 범위 설정 저장"""
    data = {
        'min_cost': min_cost,
        'max_cost': max_cost
    }
    TEAM_COST_RANGE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_strategy_time() -> int:
    """작전회의 시간 설정 로드 (분 단위)"""
    if STRATEGY_TIME_FILE.exists():
        try:
            data = json.loads(STRATEGY_TIME_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return int(data.get('minutes', 1))
            elif isinstance(data, int):
                return data
        except Exception:
            pass
    return 1  # 기본값: 1분

def save_strategy_time(minutes: int):
    """작전회의 시간 설정 저장 (분 단위)"""
    data = {'minutes': minutes}
    STRATEGY_TIME_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_reset_limit() -> int:
    """전체 초기화 횟수 제한 로드"""
    if RESET_LIMIT_FILE.exists():
        try:
            data = json.loads(RESET_LIMIT_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return int(data.get('limit', 3))
            elif isinstance(data, int):
                return data
        except Exception:
            pass
    return 3  # 기본값: 3회

def save_reset_limit(limit: int):
    """전체 초기화 횟수 제한 저장"""
    data = {'limit': limit}
    RESET_LIMIT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------- Mode I, II problems ----------------

def load_mode1_problems() -> list:
    """모드 I 문제 목록 로드"""
    if MODE1_PROBLEMS_FILE.exists():
        try:
            data = json.loads(MODE1_PROBLEMS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                result = []
                for item in data:
                    if isinstance(item, dict) and 'target' in item:
                        result.append(item)
                    elif isinstance(item, (int, float, str)):
                        result.append({'target': int(item)})
                return result
        except Exception:
            pass
    # 기존 문제 파일이 있으면 그것을 기본값으로 사용
    return load_problems() or []

def save_mode1_problems(problems: list):
    """모드 I 문제 목록 저장"""
    formatted_problems = []
    for p in problems:
        if isinstance(p, dict):
            formatted_problems.append(p)
        else:
            formatted_problems.append({'target': int(p)})
    MODE1_PROBLEMS_FILE.write_text(json.dumps(formatted_problems, ensure_ascii=False, indent=2), encoding="utf-8")

def load_mode2_problems() -> list:
    """모드 II 문제 목록 로드"""
    if MODE2_PROBLEMS_FILE.exists():
        try:
            data = json.loads(MODE2_PROBLEMS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                result = []
                for item in data:
                    if isinstance(item, dict) and 'target' in item:
                        result.append(item)
                    elif isinstance(item, (int, float, str)):
                        result.append({'target': int(item)})
                return result
        except Exception:
            pass
    # 기본값은 빈 리스트
    return []

def save_mode2_problems(problems: list):
    """모드 II 문제 목록 저장"""
    formatted_problems = []
    for p in problems:
        if isinstance(p, dict):
            formatted_problems.append(p)
        else:
            formatted_problems.append({'target': int(p)})
    MODE2_PROBLEMS_FILE.write_text(json.dumps(formatted_problems, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------- Network multiplayer problems ----------------

def load_network_mode1_problems() -> list:
    """네트워크 1라운드 모드 I 문제 목록 로드. 없으면 일반 설정을 사용."""
    if NETWORK_MODE1_PROBLEMS_FILE.exists():
        try:
            data = json.loads(NETWORK_MODE1_PROBLEMS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                result = []
                for item in data:
                    if isinstance(item, dict) and 'target' in item:
                        result.append(item)
                    elif isinstance(item, (int, float, str)):
                        result.append({'target': int(item)})
                if result:
                    return result
        except Exception:
            pass
    return load_mode1_problems()

def save_network_mode1_problems(problems: list):
    """네트워크 1라운드 모드 I 문제 저장. 비워두면 기본값 사용."""
    formatted = []
    for p in problems:
        if isinstance(p, dict):
            formatted.append(p)
        elif str(p).strip():
            formatted.append({'target': int(p)})
    if formatted:
        NETWORK_MODE1_PROBLEMS_FILE.write_text(json.dumps(formatted, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        try:
            NETWORK_MODE1_PROBLEMS_FILE.unlink()
        except FileNotFoundError:
            pass

def load_network_mode2_problems() -> list:
    """네트워크 1라운드 모드 II 문제 목록 로드. 없으면 일반 설정을 사용."""
    if NETWORK_MODE2_PROBLEMS_FILE.exists():
        try:
            data = json.loads(NETWORK_MODE2_PROBLEMS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                result = []
                for item in data:
                    if isinstance(item, dict) and 'target' in item:
                        result.append(item)
                    elif isinstance(item, (int, float, str)):
                        result.append({'target': int(item)})
                if result:
                    return result
        except Exception:
            pass
    return load_mode2_problems()

def save_network_mode2_problems(problems: list):
    """네트워크 1라운드 모드 II 문제 저장. 비워두면 기본값 사용."""
    formatted = []
    for p in problems:
        if isinstance(p, dict):
            formatted.append(p)
        elif str(p).strip():
            formatted.append({'target': int(p)})
    if formatted:
        NETWORK_MODE2_PROBLEMS_FILE.write_text(json.dumps(formatted, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        try:
            NETWORK_MODE2_PROBLEMS_FILE.unlink()
        except FileNotFoundError:
            pass

def load_network_team_problems() -> list[int]:
    """네트워크 2라운드 팀전 문제 목록 로드. 없으면 일반 설정 사용."""
    if NETWORK_TEAM_PROBLEMS_FILE.exists():
        try:
            data = json.loads(NETWORK_TEAM_PROBLEMS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                cleaned = []
                for item in data:
                    if isinstance(item, (int, float, str)):
                        cleaned.append(int(item))
                if cleaned:
                    return cleaned
        except Exception:
            pass
    return load_team_problems()

def save_network_team_problems(problems: list[int]):
    """네트워크 2라운드 팀전 문제 저장. 비우면 기본값 사용."""
    cleaned = []
    for p in problems:
        if isinstance(p, (int, float, str)):
            value = str(p).strip()
            if value:
                cleaned.append(int(value))
    if cleaned:
        NETWORK_TEAM_PROBLEMS_FILE.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        try:
            NETWORK_TEAM_PROBLEMS_FILE.unlink()
        except FileNotFoundError:
            pass

# ---------------- Mode I, II costs ----------------

def load_mode1_costs() -> dict:
    """모드 I 기호별 코스트 로드"""
    if MODE1_COSTS_FILE.exists():
        try:
            data = json.loads(MODE1_COSTS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {k: int(v) for k, v in data.items()}
        except Exception:
            pass
    # 기존 코스트 파일이 있으면 그것을 기본값으로 사용
    return load_costs()

def save_mode1_costs(costs: dict):
    """모드 I 기호별 코스트 저장"""
    MODE1_COSTS_FILE.write_text(json.dumps(costs, ensure_ascii=False, indent=2), encoding="utf-8")

def load_mode2_costs() -> dict:
    """모드 II 기호별 코스트 로드"""
    if MODE2_COSTS_FILE.exists():
        try:
            data = json.loads(MODE2_COSTS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {k: int(v) for k, v in data.items()}
        except Exception:
            pass
    # 기본값은 모드 I과 동일
    return load_mode1_costs()

def save_mode2_costs(costs: dict):
    """모드 II 기호별 코스트 저장"""
    MODE2_COSTS_FILE.write_text(json.dumps(costs, ensure_ascii=False, indent=2), encoding="utf-8") 