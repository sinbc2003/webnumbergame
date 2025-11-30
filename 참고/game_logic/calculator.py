# game_logic/calculator.py
import re
from utils.problem_store import load_costs

def preprocess_expression(expr: str, mode: str = 'normal') -> str:
    """
    Cleans and prepares the mathematical expression for evaluation based on the mode.
    """
    allowed_chars = set("() +*1")
    # Check for disallowed characters first (excluding whitespace)
    for ch in expr:
        if ch not in allowed_chars and ch.strip() != "":
            raise ValueError("허용되지 않은 기호가 포함되었습니다.")

    cleaned_expr = "".join(filter(lambda char: char in allowed_chars, expr))

    if mode in ['normal', 'cost']:
        stripped = cleaned_expr.replace(" ", "")
        # 코스트 모드에서는 11, 111 등을 허용함

        # Detect implicit multiplication (e.g., ")(" or "1(" or ")1")
        if re.search(r"\)\(|1\(|\)1", stripped):
            raise ValueError("식이 불완전하여 계산할 수 없음.")

        processed_expr = stripped  # explicit '*' only
    elif mode == 'combo':
        processed_expr = cleaned_expr
    else:
        raise ValueError(f"Unknown mode: {mode}")

    return processed_expr.replace(" ", "")

def calculate_expression(expr: str, mode: str = 'normal'):
    """
    Calculates the result of a single processed mathematical expression.
    """
    if not expr:
        return None
    
    # 맨 앞에 +가 있는 경우 불완전한 식으로 처리
    if expr.strip().startswith('+'):
        return "식이 불완전하여 계산할 수 없음."
    
    # 맨 뒤에 연산자가 있는 경우 불완전한 식으로 처리
    if expr.strip().endswith(('+', '*')):
        return "식이 불완전하여 계산할 수 없음."
    
    # 연속된 연산자 검증 (++, +*, *+, ** 등)
    if re.search(r'[\+\*]{2,}', expr.strip()):
        return "식이 불완전하여 계산할 수 없음."
    
    # 괄호 뒤에 바로 연산자가 오는 경우 검증 (예: (+1, (*1)
    if re.search(r'\([\+\*]', expr.strip()):
        return "식이 불완전하여 계산할 수 없음."
    
    # 연산자 뒤에 바로 괄호가 닫히는 경우 검증 (예: 1+), 1*)
    if re.search(r'[\+\*]\)', expr.strip()):
        return "식이 불완전하여 계산할 수 없음."
    
    # 빈 괄호 검증 (예: (), (()), (()))
    if re.search(r'\(\s*\)', expr.strip()):
        return "식이 불완전하여 계산할 수 없음."
    
    # 중첩된 빈 괄호 검증 (예: (()), ((())), 등)
    temp_expr = expr.strip()
    while '()' in temp_expr:
        temp_expr = temp_expr.replace('()', '')
    if re.search(r'\(\s*\)', temp_expr):
        return "식이 불완전하여 계산할 수 없음."
    
    try:
        processed_expr = preprocess_expression(expr, mode)
        if not re.match(r"^[0-9\+\-\*\/\(\)\.]*$", processed_expr):
            return "Error: Invalid characters"
        result = eval(processed_expr, {"__builtins__": {}}, {})
        return result
    except SyntaxError:
        return "식이 불완전하여 계산할 수 없음."
    except TypeError as e:
        # TypeError는 보통 불완전한 식에서 발생 (예: 1+(), 1+(()))
        if "unsupported operand type" in str(e):
            return "식이 불완전하여 계산할 수 없음."
        return "식이 불완전하여 계산할 수 없음."
    except ZeroDivisionError:
        return "0으로 나눌 수 없습니다."
    except ValueError as e:
        return str(e)
    except Exception as e:
        return "식이 불완전하여 계산할 수 없음."

def analyze_input(text: str, mode: str = 'normal', costs: dict = None):
    """
    Analyzes a multi-line input text based on the mode.
    """
    expressions = text.split('\n')
    results = []
    char_count = 0
    total_cost = 0

    valid_chars_for_count = "()+*1"
    
    # 코스트 설정을 동적으로 로드 (설정 변경 시 즉시 반영)
    if costs is not None:
        cost_map = costs
    else:
        cost_map = load_costs()

    for line in expressions:
        stripped_line = line.strip()
        if not stripped_line:
            continue

        if mode == 'cost':
            # 코스트 모드에서는 연속된 1의 개수를 세어서 코스트 계산
            i = 0
            while i < len(stripped_line):
                if stripped_line[i] == '1':
                    # 연속된 1의 개수 세기
                    ones_count = 0
                    j = i
                    while j < len(stripped_line) and stripped_line[j] == '1':
                        ones_count += 1
                        j += 1
                    # 연속된 1의 개수에 설정된 코스트 곱하기
                    total_cost += ones_count * cost_map.get('1', 1)
                    i = j
                elif stripped_line[i] in cost_map:
                    total_cost += cost_map[stripped_line[i]]
                    i += 1
                else:
                    i += 1
        else:
            for char in stripped_line:
                if char in valid_chars_for_count:
                    char_count += 1
        
        result = calculate_expression(stripped_line, mode)
        if result is not None:
            results.append({"expr": stripped_line, "result": result})

    if mode == 'cost':
        return {"results": results, "total_cost": total_cost}
    else:
        return {"results": results, "char_count": char_count}
