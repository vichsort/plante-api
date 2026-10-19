"""As regras do monólito modular aplicadas ao código real (`ARCHITECTURE.md`, seção 3)."""
from pathlib import Path

from tests.architecture import rules

_ROOT = Path(__file__).parents[2]
_SRC = _ROOT / "src"
_SHARED = _SRC / "shared"
_MODULES = sorted(p for p in (_SRC / "modules").iterdir() if p.is_dir() and p.name != "__pycache__")


def test_module_layout() -> None:
    # Act
    violations = [v for module in _MODULES for v in rules.layout_violations(module, rules.MODULE_LAYOUT)]
    violations += rules.layout_violations(_SHARED, rules.SHARED_LAYOUT)

    # Assert
    assert violations == []


def test_every_module_has_a_complete_readme() -> None:
    # Act
    violations = [v for module in [*_MODULES, _SHARED] for v in rules.readme_violations(module)]

    # Assert
    assert violations == []


def test_every_error_is_documented_in_its_module() -> None:
    # Act
    violations = [v for module in [*_MODULES, _SHARED] for v in rules.undocumented_errors(module)]

    # Assert
    assert violations == []


def test_error_codes_are_unique() -> None:
    # Arrange
    files = sorted(_SRC.glob("**/exceptions.py"))

    # Act
    violations = rules.duplicated_error_codes(files)

    # Assert
    assert violations == []


def test_imports_go_through_barrels() -> None:
    # Act
    violations = rules.barrel_violations(_SRC)

    # Assert
    assert violations == []


def test_tests_follow_arrange_act_assert() -> None:
    # Arrange: testes dos módulos e os ponta a ponta (os da composição, em `tests/`, ficam de fora)
    files = sorted(_SRC.glob("**/tests/**/test_*.py")) + sorted((_ROOT / "tests" / "e2e").glob("test_*.py"))

    # Act
    violations = [v for path in files for v in rules.aaa_violations(path)]

    # Assert
    assert violations == []
