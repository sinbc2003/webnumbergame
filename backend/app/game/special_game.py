import ast
import re

ALLOWED_PATTERN = re.compile(r"^[1\+\-\*\(\)]+$")
ALLOWED_SINGLE_TOKENS = {"1", "+", "-", "*", "(", ")"}
MAX_EXPRESSION_LENGTH = 512
MAX_EXPONENT = 8
MAX_ABS_VALUE = 10**9
MAX_BASE_MAGNITUDE = 10**6


class SpecialExpressionError(ValueError):
    """Raised when the player input violates special game constraints."""


def normalize_expression(expression: str) -> str:
    stripped = "".join(expression.split())
    if not stripped:
        raise SpecialExpressionError("수식을 입력해 주세요.")
    if len(stripped) > MAX_EXPRESSION_LENGTH:
        raise SpecialExpressionError("수식은 최대 512자까지 입력할 수 있습니다.")
    if not ALLOWED_PATTERN.fullmatch(stripped):
        raise SpecialExpressionError("허용되지 않은 기호가 포함되어 있습니다.")
    return stripped


def count_symbol_usage(expression: str) -> int:
    count = 0
    idx = 0
    length = len(expression)
    while idx < length:
        if expression.startswith("**", idx):
            count += 1
            idx += 2
            continue
        token = expression[idx]
        if token not in ALLOWED_SINGLE_TOKENS:
            raise SpecialExpressionError("허용되지 않은 기호가 포함되어 있습니다.")
        count += 1
        idx += 1
    return count


def evaluate_special_expression(expression: str) -> int:
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as exc:  # pragma: no cover - defensive branch
        raise SpecialExpressionError("식이 불완전하여 계산할 수 없습니다.") from exc
    value = _evaluate_node(parsed.body)
    if abs(value) > MAX_ABS_VALUE:
        raise SpecialExpressionError("결과가 허용 범위를 벗어났습니다.")
    return value


def _evaluate_node(node: ast.AST) -> int:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            raise SpecialExpressionError("불리언은 사용할 수 없습니다.")
        if isinstance(node.value, int):
            return int(node.value)
        raise SpecialExpressionError("정수만 사용할 수 있습니다.")
    if isinstance(node, ast.UnaryOp):
        operand = _evaluate_node(node.operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise SpecialExpressionError("허용되지 않은 단항 연산입니다.")
    if isinstance(node, ast.BinOp):
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Pow):
            if right < 0:
                raise SpecialExpressionError("거듭제곱 지수는 음수일 수 없습니다.")
            if right > MAX_EXPONENT:
                raise SpecialExpressionError(f"거듭제곱 지수는 최대 {MAX_EXPONENT}까지 허용됩니다.")
            if abs(left) > MAX_BASE_MAGNITUDE:
                raise SpecialExpressionError("거듭제곱의 밑이 너무 큽니다.")
            return left**right
        raise SpecialExpressionError("허용되지 않은 연산입니다.")
    raise SpecialExpressionError("허용되지 않은 식입니다.")


