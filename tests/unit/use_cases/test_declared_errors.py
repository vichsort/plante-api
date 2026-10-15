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
from types import ModuleType

import pytest

import src.domain.exceptions as domain_exceptions
import src.domain.use_cases as use_cases_package
from src.domain.exceptions import PlantEError


def _use_case_modules() -> list[ModuleType]:
    return [
        importlib.import_module(f"{use_cases_package.__name__}.{info.name}")
        for info in pkgutil.iter_modules(use_cases_package.__path__)
        if info.name.endswith("_use_case")
    ]


def _raised_domain_errors(module: ModuleType) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(inspect.getsource(module))):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        if isinstance(target, ast.Name):
            error = getattr(domain_exceptions, target.id, None)
            if isinstance(error, type) and issubclass(error, PlantEError):
                names.add(target.id)
    return names


@pytest.mark.parametrize("module", _use_case_modules(), ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_use_case_declares_every_error_it_raises(module: ModuleType) -> None:
    use_cases = [
        cls for name, cls in vars(module).items()
        if name.endswith("UseCase") and inspect.isclass(cls) and cls.__module__ == module.__name__
    ]
    assert len(use_cases) == 1
    declared = {error.__name__ for error in use_cases[0].raises}
    assert _raised_domain_errors(module) <= declared
