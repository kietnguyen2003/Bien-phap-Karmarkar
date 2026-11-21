"""Input and end-to-end report contracts for the browser adapter."""
import pytest

from karmarkar.general_lp import GeneralSolverConfig
from karmarkar.web_service import build_problem, parse_number, parse_vector, run_problem


@pytest.mark.parametrize("text, expected", [(" 1/3 ", 1/3), ("-2.5", -2.5), ("1e-3", .001)])
def test_numbers(text, expected):
    assert parse_number(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "1/0", "nan", "inf", "1e999"])
def test_invalid_numbers(text):
    with pytest.raises(ValueError):
        parse_number(text)


def test_vector_validation():
    assert parse_vector("1/2 -3", 2, "Mục tiêu") == [.5, -3]
    with pytest.raises(ValueError, match="Mục tiêu"):
        parse_vector("1", 2, "Mục tiêu")
    with pytest.raises(ValueError, match="Mục tiêu"):
        parse_vector("1 abc", 2, "Mục tiêu")


def test_build_validates_signs():
    with pytest.raises(ValueError):
        build_problem("1", "0", [], ["bad"], "min")
    with pytest.raises(ValueError):
        build_problem("1", "0", [("1", "bad", "2")], [">=0"], "min")


def test_rhs_error_identifies_constraint():
    with pytest.raises(ValueError, match="Vế phải ràng buộc 1"):
        build_problem("1", "0", [("1", "<=", "abc")], [">=0"], "min")


def test_free_and_nonpositive_variables_are_preserved():
    problem = build_problem("1/2 2", "-1/3", [], ["free", "<=0"], "max")
    assert problem.variable_signs == ("free", "<=0")
    assert problem.objective_constant == pytest.approx(-1/3)
    assert problem.constraints.shape == (0, 2)


@pytest.mark.parametrize("objective, rows, signs, sense, status", [
    ("1", [], [">=0"], "max", "UNBOUNDED"),
    ("1", [("1", "<=", "0"), ("1", ">=", "1")], [">=0"], "min", "INFEASIBLE"),
    ("1 1", [("1 1", "=", "1")], [">=0", ">=0"], "min", "MULTIPLE_OPTIMA"),
    ("1", [("1", "=", "0")], [">=0"], "min", "KARMARKAR_PRECONDITION_FAILED"),
])
def test_terminal_reports(objective, rows, signs, sense, status):
    problem = build_problem(objective, "0", rows, signs, sense)
    result = run_problem(problem, GeneralSolverConfig())
    assert result.status == status
    assert result.iterations == 0
    assert "<!doctype html>" in result.html.lower()
    assert result.message


@pytest.mark.parametrize("compare,details", [(True, True), (False, False)])
def test_bounded_report(compare, details):
    problem = build_problem("-1 0", "2", [("1 1", "<=", "2")], [">=0", ">=0"], "min")
    result = run_problem(problem, GeneralSolverConfig(), compare=compare, details=details)
    assert result.status == "APPROX_TOL_REACHED"
    assert abs(result.objective) < 1e-8
    assert result.x[0] == pytest.approx(2, abs=1e-7)
    assert result.iterations > 0
    assert "data:image/png;base64" in result.html
    assert "Kết quả đầu ra" in result.html


def test_iteration_limit_is_not_reported_as_success():
    problem = build_problem("-1 0", "2", [("1 1", "<=", "2")], [">=0", ">=0"], "min")
    result = run_problem(problem, GeneralSolverConfig(max_iter=1), compare=False, details=False)
    assert result.status == "MAX_ITERATIONS"
    assert result.iterations == 1
