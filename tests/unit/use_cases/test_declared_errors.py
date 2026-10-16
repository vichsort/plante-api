"""
Cada use case declara em `raises` os erros de domínio que pode lançar; as rotas documentam
exatamente essa lista no OpenAPI (`error_responses(*UseCase.raises)`).

Aqui só dá para conferir os `raise` escritos no próprio módulo do use case. Erros vindos de
policies, entidades e ports (ex.: `SubscriptionPolicy`, `UserPlant.water()`, `IPlantIdentifier`)
continuam sendo listados à mão.
"""
import ast
import importlib
import inspect
import pkgutil
from pathlib import Path
from types import ModuleType

import pytest

import src.domain.use_cases as legacy_use_cases
from src.shared.domain import PlantEError

_MODULES = Path(__file__).parents[3] / "src" / "modules"


def _use_case_packages() -> list[str]:
    """Os use cases do código antigo e os de cada módulo (`domain/use_cases/`)."""
    modules = sorted(p.parent.parent.name for p in _MODULES.glob("*/domain/use_cases"))
    return [legacy_use_cases.__name__, *(f"src.modules.{name}.domain.use_cases" for name in modules)]


def _use_case_modules() -> list[ModuleType]:
    found = []
    for package_name in _use_case_packages():
        package = importlib.import_module(package_name)
        found += [
            importlib.import_module(f"{package_name}.{info.name}")
            for info in pkgutil.iter_modules(package.__path__)
        ]
    return found


def _raised_domain_errors(module: ModuleType) -> set[str]:
    """Os erros de domínio de cada `raise` do arquivo, resolvidos pelos nomes que ele importa."""
    names = set()
    for node in ast.walk(ast.parse(inspect.getsource(module))):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        if isinstance(target, ast.Name):
            error = getattr(module, target.id, None)
            if isinstance(error, type) and issubclass(error, PlantEError):
                names.add(target.id)
    return names


@pytest.mark.parametrize("module", _use_case_modules(), ids=lambda m: m.__name__.removeprefix("src."))
def test_use_case_declares_every_error_it_raises(module: ModuleType) -> None:
    use_cases = [
        cls for name, cls in vars(module).items()
        if name.endswith("UseCase") and inspect.isclass(cls) and cls.__module__ == module.__name__
    ]
    assert len(use_cases) == 1
    declared = {error.__name__ for error in use_cases[0].raises}
    assert _raised_domain_errors(module) <= declared
