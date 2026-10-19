"""Cada regra de `rules.py` contra módulos sintéticos: o caso bom passa, cada desvio é apontado."""
from pathlib import Path

from tests.architecture import rules

GOOD_README = """# Garden

## Propósito
Plantas do usuário.

## API pública
`GardenPlant`.

## Decisões
Nenhuma ainda.

## Erros
- `PLANTE_4530_PLANT_NOT_FOUND`
"""


def _write(root: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return root


def _module(tmp_path: Path, extra: dict[str, str] | None = None) -> Path:
    return _write(tmp_path / "src" / "modules" / "garden", {
        "__init__.py": "",
        "README.md": GOOD_README,
        "container.py": "",
        "domain/__init__.py": "",
        "domain/exceptions.py": 'class PlantNotFoundError(PlantEError):\n    code = "PLANTE_4530_PLANT_NOT_FOUND"\n',
        "domain/entities/__init__.py": "",
        "domain/entities/user_plant.py": "",
        "adapters/__init__.py": "",
        "adapters/persistence/__init__.py": "",
        "adapters/persistence/models/__init__.py": "",
        "adapters/persistence/models/user_plant.py": "",
        "api/__init__.py": "",
        "api/router.py": "",
        "tests/__init__.py": "",
        "tests/unit/__init__.py": "",
        "tests/unit/test_x.py": "",
        **(extra or {}),
    })


def test_good_module_has_no_layout_violation(tmp_path: Path) -> None:
    # Arrange
    module = _module(tmp_path)

    # Act
    violations = rules.layout_violations(module, rules.MODULE_LAYOUT)

    # Assert
    assert violations == []


def test_layout_flags_unknown_names_and_empty_folders(tmp_path: Path) -> None:
    # Arrange
    module = _module(tmp_path, {
        "helpers.py": "",
        "domain/utils/__init__.py": "",
        "domain/utils/x.py": "",
        "domain/services/__init__.py": "",
        "api/routes/__init__.py": "",
        "adapters/persistence/queries/__init__.py": "",
        "adapters/persistence/queries/q.py": "",
    })

    # Act
    violations = "\n".join(rules.layout_violations(module, rules.MODULE_LAYOUT))

    # Assert
    assert "garden/helpers.py: arquivo fora do layout" in violations
    assert "garden/domain/utils: pasta fora do layout" in violations
    assert "garden/domain/services: pasta vazia" in violations
    assert "garden/api/routes: pasta vazia" in violations
    assert "garden/adapters/persistence/queries: pasta fora do layout" in violations


def test_readme_needs_every_section(tmp_path: Path) -> None:
    # Arrange
    module = _module(tmp_path, {"README.md": "# Garden\n\n## Propósito\nx\n"})

    # Act
    violations = rules.readme_violations(module)

    # Assert
    assert violations == [
        "garden/README.md: falta a seção '## API pública'",
        "garden/README.md: falta a seção '## Decisões'",
        "garden/README.md: falta a seção '## Erros'",
    ]


def test_every_error_of_the_module_is_documented(tmp_path: Path) -> None:
    # Arrange
    module = _module(tmp_path, {
        "domain/exceptions.py": (
            'class PlantNotFoundError(PlantEError):\n    code = "PLANTE_4530_PLANT_NOT_FOUND"\n'
            'class PlantLimitExceededError(PlantEError):\n    code = "PLANTE_4220_PLANT_LIMIT_REACHED"\n'
        ),
    })

    # Act
    violations = rules.undocumented_errors(module)

    # Assert
    assert violations == ["garden: PlantLimitExceededError (PLANTE_4220_PLANT_LIMIT_REACHED) não aparece em '## Erros' do README"]


def test_error_codes_are_unique_but_inheriting_a_code_is_fine(tmp_path: Path) -> None:
    # Arrange: a subclasse que não redefine `code` herda o da base (ex.: NotAPlantError)
    first = _write(tmp_path / "a", {"exceptions.py": (
        'class InvalidImageError(PlantEError):\n    code = "PLANTE_4001_INVALID_IMAGE"\n'
        "class NotAPlantError(InvalidImageError):\n    pass\n"
    )}) / "exceptions.py"
    second = _write(tmp_path / "b", {"exceptions.py": 'class Other(PlantEError):\n    code = "PLANTE_4001_INVALID_IMAGE"\n'}) / "exceptions.py"

    # Act
    alone = rules.duplicated_error_codes([first])
    together = rules.duplicated_error_codes([first, second])

    # Assert
    assert alone == []
    assert len(together) == 1 and together[0].startswith("PLANTE_4001_INVALID_IMAGE repetido")


def test_error_codes_follow_the_scheme(tmp_path: Path) -> None:
    # Arrange
    exceptions = _write(tmp_path, {"exceptions.py": (
        'class PlantNotFoundError(PlantEError):\n    code = "PLANTE_4530_PLANT_NOT_FOUND"\n    status_code = 404\n'
        'class WrongModule(PlantEError):\n    code = "PLANTE_4130_WRONG_MODULE"\n    status_code = 404\n'
        'class WrongFamily(PlantEError):\n    code = "PLANTE_4531_WRONG_FAMILY"\n    status_code = 500\n'
        'class WrongKind(PlantEError):\n    code = "PLANTE_4532_WRONG_KIND"\n    status_code = 409\n'
        'class BadFormat(PlantEError):\n    code = "PLANTE_453_BAD"\n    status_code = 404\n'
        'class NoStatus(PlantEError):\n    code = "PLANTE_4533_NO_STATUS"\n'
        'class MethodNotAllowed(PlantEError):\n    code = "PLANTE_4500_METHOD"\n    status_code = 405\n'
    )}) / "exceptions.py"

    # Act
    violations = rules.error_code_violations(exceptions, "garden")

    # Assert
    assert violations == [
        "garden: WrongModule (PLANTE_4130_WRONG_MODULE): B=1, but the class lives in garden (5)",
        "garden: WrongFamily (PLANTE_4531_WRONG_FAMILY): A=4, but status_code is 500",
        "garden: WrongKind (PLANTE_4532_WRONG_KIND): C=3 does not allow status_code 409",
        "garden: BadFormat (PLANTE_453_BAD): not in the PLANTE_ABCD_NAME format",
        "garden: NoStatus (PLANTE_4533_NO_STATUS): defines no literal status_code",
    ]


def test_an_error_counts_as_used_only_when_raised_built_or_declared(tmp_path: Path) -> None:
    # Arrange
    src = tmp_path / "src"
    exceptions = _write(src / "garden", {"exceptions.py": "".join(
        f'class {name}(PlantEError):\n    code = "PLANTE_45{i}0_X"\n'
        for i, name in enumerate(["Raised", "Built", "Declared", "OnlyDocumented", "OnlyCaught", "OnlyInTests", "Pending"])
    )}) / "exceptions.py"
    _write(src, {
        "adapter.py": "def f():\n    raise Raised()\n\ndef g():\n    return Built()\n",
        "use_case.py": "class UseCase:\n    raises = (Declared,)\n",
        "router.py": "responses = error_responses(OnlyDocumented)\ntry:\n    pass\nexcept OnlyCaught:\n    pass\n",
        "garden/tests/test_x.py": "raise OnlyInTests()\n",
    })

    # Act
    violations = rules.unused_errors(src, [exceptions], allowed=frozenset({"Pending"}))

    # Assert
    assert [v.split(": ")[1].split(" ")[0] for v in violations] == ["OnlyDocumented", "OnlyCaught", "OnlyInTests"]


def test_barrels(tmp_path: Path) -> None:
    # Arrange
    src = _write(tmp_path / "src", {
        "__init__.py": "",
        "modules/__init__.py": "",
        "modules/garden/__init__.py": "from src.modules.garden.domain.entities import UserPlant\n",
        "modules/garden/domain/__init__.py": "",
        "modules/garden/domain/entities.py": "from src.modules.garden import x\n",  # o próprio barrel
        "modules/health/__init__.py": "",
        "modules/health/domain/use_case.py": (
            "from src.modules.garden import GardenPlant\n"                  # ok: raiz
            "from src.modules.garden.domain.entities import UserPlant\n"   # interno de outro módulo
            "from src.shared.domain import UserId\n"                        # ok: camada do shared
            "from src.shared.domain.exceptions import PlantEError\n"       # fura a camada do shared
        ),
        "modules/health/tests/unit/test_x.py": (
            "from src.modules.garden.tests.fakes import FakeLookup\n"     # ok: dublê publicado pelo dono
            "from src.modules.garden.tests.unit.helpers import make\n"    # o resto dos testes de outro módulo, não
            "from src.shared.tests.fakes import MarkingSanitizer\n"       # ok: dublê publicado pelo shared
        ),
        "modules/health/domain/fakes_user.py": "from src.modules.garden.tests.fakes import FakeLookup\n",  # só testes
        "bootstrap/container.py": (
            "from src.modules.garden.container import GardenContainer\n"   # ok: composição
            "from src.modules.garden.adapters import Repo\n"               # nem a composição
        ),
        "shared/domain/events.py": "from src.shared.domain.exceptions import PlantEError\n",  # ok: dentro do shared
    })

    # Act
    violations = rules.barrel_violations(src)

    # Assert
    assert [v.split(": ", 1)[0] for v in violations] == [
        "src/bootstrap/container.py:2",
        "src/modules/garden/domain/entities.py:1",
        "src/modules/health/domain/fakes_user.py:1",
        "src/modules/health/domain/use_case.py:2",
        "src/modules/health/domain/use_case.py:4",
        "src/modules/health/tests/unit/test_x.py:2",
    ]


def test_aaa_markers(tmp_path: Path) -> None:
    # Arrange
    test_file = _write(tmp_path, {"test_x.py": (
        "def test_full():\n    # Arrange\n    x = 1\n    # Act\n    y = x\n    # Assert\n    assert y\n\n"
        "def test_raises():\n    # Act & Assert\n    assert True\n\n"
        "def test_without_markers():\n    assert True\n\n"
        "def test_out_of_order():\n    # Assert\n    assert True\n    # Act\n    pass\n\n"
        "def helper():\n    pass\n"
    )}) / "test_x.py"

    # Act
    violations = rules.aaa_violations(test_file)

    # Assert
    assert violations == [
        "test_x.py::test_without_markers: faltam marcadores (# Act e # Assert, ou # Act & Assert)",
        "test_x.py::test_out_of_order: marcadores fora de ordem (Assert, Act)",
    ]
