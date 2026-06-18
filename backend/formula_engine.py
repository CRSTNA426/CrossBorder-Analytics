"""
Formula Engine — parses and evaluates custom metric formulas.

Uses asteval for safe expression evaluation. Supports:
  - Basic arithmetic: + - * / ( )
  - Variable references to built-in metric keys
  - Cycle detection via dependency graph
  - Division-by-zero handling
"""
import re
from typing import Any
from asteval import Interpreter


# Reserved variable names that users cannot use as metric keys (safety net)
_RESERVED = {
    "abs", "all", "any", "bool", "bytes", "callable", "chr", "complex",
    "dict", "dir", "divmod", "enumerate", "eval", "exec", "exit", "filter",
    "float", "format", "frozenset", "getattr", "globals", "hasattr", "hash",
    "hex", "id", "import", "input", "int", "isinstance", "issubclass", "iter",
    "len", "list", "locals", "map", "max", "memoryview", "min", "next",
    "object", "oct", "open", "ord", "pow", "print", "property", "quit",
    "range", "repr", "reversed", "round", "set", "setattr", "slice", "sorted",
    "staticmethod", "str", "sum", "super", "tuple", "type", "vars", "zip",
    "__import__", "compile", "delattr", "execfile", "file", "help",
    "license", "raw_input", "reduce", "reload", "unichr", "unicode",
    "xrange", "copyright", "credits",
}


def extract_variables(formula: str) -> list[str]:
    """Extract metric key variable names from a formula string."""
    # Match words that start with a letter and may contain underscores
    tokens = re.findall(r'[a-zA-Z_]\w*', formula)
    # Filter out numbers and reserved keywords
    variables = []
    for t in tokens:
        if t not in _RESERVED and not t.isdigit() and not re.match(r'^\d', t):
            variables.append(t)
    return sorted(set(variables))


def validate_formula(formula: str, available_keys: set[str]) -> tuple[bool, str | None, list[str]]:
    """
    Validate a formula:
    - Check syntax
    - Check all variables exist in available_keys
    - Returns (is_valid, error_message, variable_list)
    """
    # Basic syntax: must contain at least one operator
    if not re.search(r'[+\-*/()]', formula):
        return False, "公式必须包含至少一个运算符（+ - * /）", []

    # Parentheses balance
    if formula.count('(') != formula.count(')'):
        return False, "括号不匹配", []

    # Extract referenced variables
    variables = extract_variables(formula)
    if not variables:
        return False, "公式中未检测到有效的指标变量引用", []

    # Check all variables exist
    missing = [v for v in variables if v not in available_keys]
    if missing:
        return False, f"指标不存在: {', '.join(missing)}", variables

    # Try parsing with asteval to detect syntax errors
    interpreter = Interpreter(usersym={v: 1.0 for v in variables}, minimal=True)
    try:
        interpreter.parse(formula)
    except Exception as e:
        return False, f"公式语法错误: {str(e)}", variables

    return True, None, variables


def evaluate_formula(formula: str, variable_values: dict[str, float]) -> float | None:
    """
    Evaluate a formula with given variable values.
    Returns None on division by zero or other runtime errors.
    """
    if not formula or not variable_values:
        return None

    interpreter = Interpreter(usersym=variable_values, minimal=True)
    # Disallow any built-in functions
    interpreter.symtable.clear()
    for k, v in variable_values.items():
        interpreter.symtable[k] = v if v is not None else 0.0

    try:
        result = interpreter.eval(formula)
        if result is None:
            return None
        # Check for NaN or Inf
        if isinstance(result, float):
            import math
            if math.isnan(result) or math.isinf(result):
                return None
        return float(result)
    except ZeroDivisionError:
        return None
    except Exception:
        return None


def detect_cycle(
    custom_metric_key: str,
    formula_variables: list[str],
    existing_dependencies: dict[str, set[str]],
) -> list[str] | None:
    """
    Detect circular dependencies.
    existing_dependencies: {metric_key: {depends_on_key, ...}}
    Returns a cycle path if found, otherwise None.

    Uses DFS to detect cycles in the dependency graph.
    """
    # Build the full graph snapshot including the proposed new metric
    graph: dict[str, set[str]] = {}
    for k, deps in existing_dependencies.items():
        graph[k] = set(deps)
    graph[custom_metric_key] = set(formula_variables)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {k: WHITE for k in graph}
    parent: dict[str, str | None] = {k: None for k in graph}

    def dfs(u: str) -> list[str] | None:
        color[u] = GRAY
        for v in graph.get(u, set()):
            if v not in color:
                continue  # built-in key, no outgoing edges
            if color.get(v) == GRAY:
                # Found cycle — trace back
                cycle = [v, u]
                cur = u
                while parent.get(cur) and parent[cur] != v:
                    cur = parent[cur]
                    cycle.append(cur)
                cycle.append(v)
                cycle.reverse()
                return cycle
            if color.get(v) == WHITE:
                parent[v] = u
                result = dfs(v)
                if result:
                    return result
        color[u] = BLACK
        return None

    for node in graph:
        if color.get(node) == WHITE:
            result = dfs(node)
            if result:
                return result
    return None
