import re
from typing import Dict, Any

DEFAULT_COSTS: Dict[str, int] = {"1": 1, "+": 1, "*": 2, "(": 1, ")": 1}


def preprocess_expression(expr: str, mode: str = "normal") -> str:
    allowed_chars = set("() +*1")
    for ch in expr:
        if ch not in allowed_chars and ch.strip() != "":
            raise ValueError("허용되지 않은 기호가 포함되었습니다.")

    cleaned_expr = "".join(filter(lambda char: char in allowed_chars, expr))

    if mode in ["normal", "cost"]:
        stripped = cleaned_expr.replace(" ", "")
        if re.search(r"\)\(|1\(|\)1", stripped):
            raise ValueError("식이 불완전하여 계산할 수 없음.")
        processed_expr = stripped
    elif mode == "combo":
        processed_expr = cleaned_expr
    else:
        raise ValueError(f"Unknown mode: {mode}")

    return processed_expr.replace(" ", "")


def calculate_expression(expr: str, mode: str = "normal"):
    if not expr:
        return None

    stripped = expr.strip()
    if stripped.startswith("+"):
        return "식이 불완전하여 계산할 수 없음."
    if stripped.endswith(("+", "*")):
        return "식이 불완전하여 계산할 수 없음."
    if re.search(r"[\+\*]{2,}", stripped):
        return "식이 불완전하여 계산할 수 없음."
    if re.search(r"\([\+\*]", stripped):
        return "식이 불완전하여 계산할 수 없음."
    if re.search(r"[\+\*]\)", stripped):
        return "식이 불완전하여 계산할 수 없음."
    if re.search(r"\(\s*\)", stripped):
        return "식이 불완전하여 계산할 수 없음."

    temp_expr = stripped
    while "()" in temp_expr:
        temp_expr = temp_expr.replace("()", "")
    if re.search(r"\(\s*\)", temp_expr):
        return "식이 불완전하여 계산할 수 없음."

    try:
        processed_expr = preprocess_expression(expr, mode)
        if not re.match(r"^[0-9\+\-\*\/\(\)\.]*$", processed_expr):
            return "허용되지 않은 기호가 포함되었습니다."
        result = eval(processed_expr, {"__builtins__": {}}, {})
        return result
    except Exception:
        return "식이 불완전하여 계산할 수 없음."


def analyze_input(text: str, mode: str = "normal", costs: Dict[str, int] | None = None) -> Dict[str, Any]:
    expressions = text.split("\n")
    results = []
    char_count = 0
    total_cost = 0

    valid_chars_for_count = "()+*1"
    cost_map = costs or DEFAULT_COSTS

    for line in expressions:
        stripped_line = line.strip()
        if not stripped_line:
            continue

        if mode == "cost":
            i = 0
            while i < len(stripped_line):
                if stripped_line[i] == "1":
                    ones_count = 0
                    j = i
                    while j < len(stripped_line) and stripped_line[j] == "1":
                        ones_count += 1
                        j += 1
                    total_cost += ones_count * cost_map.get("1", 1)
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

    if mode == "cost":
        return {"results": results, "total_cost": total_cost}
    return {"results": results, "char_count": char_count}

