from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def test_default_example_and_persisted_report():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not app.exception
    app.button(key="solve").click().run()
    assert not app.exception
    assert app.session_state["report"].status == "APPROX_TOL_REACHED"
    assert abs(app.session_state["report"].objective) < 1e-7
    assert "<!doctype html>" in app.session_state["report"].html.lower()
    app.run()
    assert app.session_state["report"].status == "APPROX_TOL_REACHED"


def test_invalid_input_clears_previous_result():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.button(key="solve").click().run()
    app.text_input(key="objective").set_value("1/0 0")
    app.button(key="solve").click().run()
    assert not app.exception
    assert app.error
    assert app.session_state["report"] is None


def test_zero_constraints_unbounded():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.number_input(key="n").set_value(1).run()
    app.number_input(key="m").set_value(0).run()
    app.text_input(key="objective").set_value("-1")
    app.button(key="solve").click().run()
    assert not app.exception
    assert app.session_state["report"].status == "UNBOUNDED"
    assert app.warning
