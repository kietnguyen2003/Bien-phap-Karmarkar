"""Validated browser input and in-memory reports using the existing solver."""
from dataclasses import dataclass
from fractions import Fraction
import math
from threading import RLock

from .general_lp import (
    GeneralLP, GeneralSolverConfig, classify_general_lp,
    classify_preparation_failure, make_problem, prepare_simplex_embedding,
    solve_general_karmarkar, solve_reference,
)
from .html_report import build_classification_html, build_solution_html


# pyplot has global state; serialize rendering across Streamlit sessions.
_REPORT_LOCK = RLock()


@dataclass(frozen=True)
class WebResult:
    """Session-local result; no shared output file is overwritten."""

    status: str
    message: str
    objective: float | None
    x: tuple[float, ...] | None
    iterations: int
    html: str


def parse_number(text: str) -> float:
    """Accept decimal/scientific notation and fractions, but no infinities."""
    try:
        value = float(Fraction(text.strip()))
        if not math.isfinite(value):
            raise ValueError("nonfinite number")
        return value
    except (ValueError, ZeroDivisionError, OverflowError) as error:
        raise ValueError(f'Không đọc được số hữu hạn "{text}".') from error


def parse_vector(text: str, n: int, label: str) -> list[float]:
    """Read exactly one coefficient per variable with a field-specific error."""
    parts = text.split()
    if len(parts) != n:
        raise ValueError(f"{label}: cần đúng {n} hệ số, cách nhau bằng khoảng trắng.")
    try:
        return [parse_number(part) for part in parts]
    except ValueError as error:
        raise ValueError(f"{label}: {error}") from error


def build_problem(
    objective_text: str,
    constant_text: str,
    constraints: list[tuple[str, str, str]],
    variable_signs: list[str],
    sense: str,
) -> GeneralLP:
    """Translate form values into the solver's validated LP data model."""
    n = len(variable_signs)
    objective = parse_vector(objective_text, n, "Hàm mục tiêu")
    rows = [parse_vector(row, n, f"Ràng buộc {i + 1}")
            for i, (row, _, _) in enumerate(constraints)]
    rhs = []
    for i, (_, _, value) in enumerate(constraints):
        try:
            rhs.append(parse_number(value))
        except ValueError as error:
            raise ValueError(f"Vế phải ràng buộc {i + 1}: {error}") from error
    return make_problem(
        objective, rows, rhs, [sign for _, sign, _ in constraints], variable_signs,
        sense=sense, objective_constant=parse_number(constant_text),
        name="Bài toán nhập từ Streamlit",
    )


def run_problem(
    problem: GeneralLP,
    config: GeneralSolverConfig,
    compare: bool = True,
    details: bool = True,
) -> WebResult:
    """Mirror the notebook's classify/prepare/solve/report pipeline in memory."""
    classification = classify_general_lp(problem)
    if not classification.terminal:
        try:
            embedding = prepare_simplex_embedding(problem, config)
        except ValueError as error:
            classification = classify_preparation_failure(classification, error)
    if classification.terminal:
        with _REPORT_LOCK:
            html = build_classification_html(problem, classification)
        x = None if classification.x is None else tuple(map(float, classification.x))
        return WebResult(classification.status, classification.message,
                         classification.objective_value, x, 0, html)
    result = solve_general_karmarkar(embedding, config)
    reference = solve_reference(problem) if compare else None
    with _REPORT_LOCK:
        html = build_solution_html(result, reference, details=details)
    return WebResult(result.status, result.message, result.objective,
                     tuple(map(float, result.x)), result.iterations, html)
