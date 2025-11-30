# game_logic/expression_parser.py

import ast

class ExpressionNormalizer(ast.NodeTransformer):
    """
    수학적 표현식을 정규화하여 덧셈과 곱셈의 교환 법칙을 강력하게 처리합니다.
    - 덧셈과 곱셈의 모든 항목들을 정렬
    - 중첩된 같은 연산자들을 평탄화
    - 교환법칙과 결합법칙을 모두 적용
    """

    def visit_BinOp(self, node):
        # 자식 노드들을 재귀적으로 방문하여 먼저 정규화
        self.generic_visit(node)
        
        # 덧셈 또는 곱셈 연산자인 경우 강력한 정규화 적용
        if isinstance(node.op, (ast.Add, ast.Mult)):
            return self._normalize_commutative_op(node)
        
        return node
    
    def _normalize_commutative_op(self, node):
        """덧셈이나 곱셈 노드를 완전히 정규화"""
        op_type = type(node.op)
        
        # 같은 연산자의 모든 항목들을 수집 (결합법칙 적용)
        terms = self._collect_terms(node, op_type)
        
        # 각 항목을 문자열로 변환하여 정렬 (교환법칙 적용)
        term_strings = [(ast.dump(term), term) for term in terms]
        term_strings.sort(key=lambda x: x[0])
        
        # 정렬된 항목들로 새로운 트리 구성
        sorted_terms = [term for _, term in term_strings]
        
        if len(sorted_terms) == 1:
            return sorted_terms[0]
        elif len(sorted_terms) == 2:
            return ast.BinOp(left=sorted_terms[0], op=op_type(), right=sorted_terms[1])
        else:
            # 3개 이상의 항목들을 왼쪽 연관으로 구성
            result = sorted_terms[0]
            for term in sorted_terms[1:]:
                result = ast.BinOp(left=result, op=op_type(), right=term)
            return result
    
    def _collect_terms(self, node, op_type):
        """같은 연산자의 모든 항목들을 재귀적으로 수집"""
        terms = []
        
        if isinstance(node, ast.BinOp) and isinstance(node.op, op_type):
            # 같은 연산자면 재귀적으로 수집
            terms.extend(self._collect_terms(node.left, op_type))
            terms.extend(self._collect_terms(node.right, op_type))
        else:
            # 다른 연산자거나 리프 노드면 그대로 추가
            terms.append(node)
        
        return terms

def normalize_expression(expression: str) -> str:
    """
    주어진 수식을 파싱, 정규화, 그리고 다시 문자열로 변환합니다.
    """
    try:
        # 1. 수식을 AST로 파싱
        tree = ast.parse(expression, mode='eval')
        
        # 2. AST 정규화
        normalizer = ExpressionNormalizer()
        normalized_tree = normalizer.visit(tree)
        
        # 3. 정규화된 AST를 다시 문자열로 변환 (Python 3.9+ 필요)
        # ast.unparse는 Python 3.9 이상에서만 사용 가능합니다.
        # 호환성을 위해 직접 변환기를 구현할 수도 있습니다.
        normalized_expr = ast.unparse(normalized_tree)
        return normalized_expr
        
    except (SyntaxError, TypeError):
        # 파싱 오류가 발생하면 원본 표현식을 반환
        return expression

if __name__ == '__main__':
    print("=== 기본 테스트 케이스 ===")
    expressions = [
        "1*1+1",
        "1+1*1",
        "(1+1)*1",
        "1*(1+1)",
        "1*1+1*1",
        "1*1+(1+1)",
        "(1+1)+1*1",
    ]

    for expr in expressions:
        normalized = normalize_expression(expr)
        print(f"Original: {expr:<15} | Normalized: {normalized}")

    print("\n=== 사용자 제시 케이스 (944 문제) ===")
    user_cases = [
        "((1+1)*(1+111)+1+11)*(1+1)*(1+1)",
        "((1+1)*(1+111)+1+11)*(1+1+1+1)",
        "(1+1)*(1+1)*(11+111+111)+1+11",
        "(1+1+1+1)*(11+111+111)+1+11"
    ]
    
    normalized_results = []
    for i, expr in enumerate(user_cases, 1):
        normalized = normalize_expression(expr)
        normalized_results.append(normalized)
        print(f"#{i}: {expr}")
        print(f"    정규화: {normalized}")
        print()
    
    print("=== 중복 체크 결과 ===")
    unique_normalized = set(normalized_results)
    print(f"총 {len(user_cases)}개 케이스 중 {len(unique_normalized)}개가 고유함")
    
    if len(unique_normalized) < len(user_cases):
        print("중복이 발견되었습니다!")
        for i, norm in enumerate(normalized_results):
            duplicates = [j+1 for j, other in enumerate(normalized_results) if other == norm and j != i]
            if duplicates:
                print(f"#{i+1}과 동일한 케이스: {duplicates}")
    else:
        print("모든 케이스가 고유합니다.")
