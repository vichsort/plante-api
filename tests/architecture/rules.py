"""
Regras do monólito modular que o linter não cobre, como funções puras sobre os arquivos. Cada
regra devolve a lista de violações (texto legível); vazia = ok. `test_rules.py` prova cada regra
com módulos sintéticos; `test_codebase.py` aplica todas ao código real.
"""
import ast
import io
import re
import tokenize
from dataclasses import dataclass
from pathlib import Path

SHARED_LAYERS = ("domain", "adapters", "api", "workers")
# A composição pode montar o módulo: container, rotas e tasks, além da API pública
COMPOSITION_ENTRIES = ("container", "api", "workers")
README_SECTIONS = ("## Propósito", "## API pública", "## Decisões", "## Erros")


# --- Layout ------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Folder:
    """O que uma pasta pode conter. `dirs=None`: qualquer subpasta (ex.: adapters por tecnologia)."""
    files: frozenset[str] | None
    dirs: dict[str, "Folder"] | None


_ANY = Folder(files=None, dirs=None)
_TESTS = Folder(
    files=frozenset({"__init__.py", "fakes.py", "conftest.py"}),
    dirs={"unit": _ANY, "integration": _ANY, "contract": _ANY},
)
_DOMAIN = Folder(
    files=frozenset({"__init__.py", "events.py", "exceptions.py"}),
    dirs={name: _ANY for name in ("entities", "value_objects", "policies", "ports", "services", "use_cases")},
)
_ADAPTERS = Folder(files=None, dirs=None)  # subpastas por tecnologia; `persistence` tem regra própria
_PERSISTENCE = Folder(files=None, dirs={"models": _ANY, "mappers": _ANY, "repositories": _ANY})
MODULE_LAYOUT = Folder(
    files=frozenset({"__init__.py", "README.md", "container.py"}),
    dirs={
        "domain": _DOMAIN,
        "adapters": _ADAPTERS,
        "api": Folder(files=frozenset({"__init__.py", "router.py", "schemas.py", "deps.py"}), dirs={}),
        "workers": Folder(files=frozenset({"__init__.py", "tasks.py"}), dirs={}),
        "tests": _TESTS,
    },
)
# O shared segue o mesmo esqueleto, mas a borda HTTP dele é a do app inteiro (middlewares, envelope)
SHARED_LAYOUT = Folder(
    files=frozenset({"__init__.py", "README.md"}),
    dirs={"domain": _DOMAIN, "adapters": _ADAPTERS, "api": _ANY, "workers": _ANY, "tests": _TESTS},
)


def _children(path: Path) -> list[Path]:
    return sorted(p for p in path.iterdir() if p.name != "__pycache__")


def _is_empty(folder: Path) -> bool:
    """Pasta sem conteúdo real: nada além de `__init__.py` e subpastas igualmente vazias."""
    return all(
        (child.is_dir() and _is_empty(child)) or child.name == "__init__.py"
        for child in _children(folder)
    )


def layout_violations(root: Path, layout: Folder) -> list[str]:
    violations: list[str] = []

    def walk(folder: Path, rule: Folder) -> None:
        for child in _children(folder):
            rel = child.relative_to(root.parent)
            if child.is_dir():
                if _is_empty(child):
                    violations.append(f"{rel}: pasta vazia (só existe pasta com conteúdo)")
                elif rule.dirs is not None and child.name not in rule.dirs:
                    violations.append(f"{rel}: pasta fora do layout (permitidas: {sorted(rule.dirs)})")
                else:
                    sub = rule.dirs[child.name] if rule.dirs is not None else _ANY
                    if rule is _ADAPTERS and child.name == "persistence":
                        sub = _PERSISTENCE
                    walk(child, sub)
            elif rule.files is not None and child.name not in rule.files:
                violations.append(f"{rel}: arquivo fora do layout (permitidos: {sorted(rule.files)})")

    walk(root, layout)
    return violations


# --- README ------------------------------------------------------------------------------------

def readme_violations(module: Path) -> list[str]:
    readme = module / "README.md"
    if not readme.exists():
        return [f"{module.name}: falta o README.md"]
    text = readme.read_text()
    return [f"{module.name}/README.md: falta a seção '{section}'" for section in README_SECTIONS if section not in text]


def _section(text: str, heading: str) -> str:
    start = text.index(heading) + len(heading)
    following = text.find("\n## ", start)
    return text[start:] if following == -1 else text[start:following]


def _class_constants(node: ast.ClassDef) -> dict[str, object]:
    """Literal class attributes assigned in the class body (`code = "..."`, `status_code = 404`)."""
    constants: dict[str, object] = {}
    for stmt in node.body:
        if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Constant):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = stmt.value.value
    return constants


def _error_classes(exceptions_file: Path) -> dict[str, dict[str, object]]:
    """Class -> its literal constants, only for classes that define `code` in their own body."""
    if not exceptions_file.exists():
        return {}
    return {
        node.name: constants
        for node in ast.parse(exceptions_file.read_text()).body
        if isinstance(node, ast.ClassDef) and isinstance((constants := _class_constants(node)).get("code"), str)
    }


def defined_error_codes(exceptions_file: Path) -> dict[str, str]:
    """Classe -> código, só das classes que definem `code` no próprio corpo."""
    return {cls: str(constants["code"]) for cls, constants in _error_classes(exceptions_file).items()}


def undocumented_errors(module: Path) -> list[str]:
    """Todo erro que o módulo define aparece na seção 'Erros' do README dele."""
    readme = module / "README.md"
    if not readme.exists() or "## Erros" not in readme.read_text():
        return []  # já acusado por `readme_violations`
    errors = _section(readme.read_text(), "## Erros")
    codes = defined_error_codes(module / "domain" / "exceptions.py")
    return [f"{module.name}: {cls} ({code}) não aparece em '## Erros' do README" for cls, code in codes.items() if code not in errors]


def duplicated_error_codes(exception_files: list[Path]) -> list[str]:
    seen: dict[str, str] = {}
    violations: list[str] = []
    for path in exception_files:
        for cls, code in defined_error_codes(path).items():
            where = f"{path}:{cls}"
            if code in seen:
                violations.append(f"{code} repetido: {seen[code]} e {where}")
            else:
                seen[code] = where
    return violations


# `PLANTE_ABCD_NAME`: A = family (4 client, 5 server), B = owning module, C = kind, D = sequence
ERROR_CODE = re.compile(r"PLANTE_([45])(\d)(\d)(\d)_[A-Z0-9]+(?:_[A-Z0-9]+)*")
MODULE_DIGITS = {
    "shared": 0, "identity": 1, "quota": 2, "catalog": 3, "identification": 4,
    "garden": 5, "health": 6, "achievements": 7, "training": 8,
}
# (A, C) -> the HTTP statuses that kind of error may answer with
KIND_STATUSES: dict[tuple[int, int], frozenset[int]] = {
    (4, 0): frozenset({400, 405, 422}),  # invalid request
    (4, 1): frozenset({401}),  # authentication
    (4, 2): frozenset({403}),  # permission or plan
    (4, 3): frozenset({404}),  # not found
    (4, 4): frozenset({409}),  # conflict or state
    (4, 5): frozenset({429}),  # limit
    (5, 0): frozenset({500}),  # internal
    (5, 1): frozenset({502}),  # external provider
    (5, 3): frozenset({503}),  # unavailable
}


def error_code_violations(exceptions_file: Path, owner: str) -> list[str]:
    """Every code follows `PLANTE_ABCD_NAME` and agrees with its `status_code` and owning module."""
    violations: list[str] = []
    for cls, constants in _error_classes(exceptions_file).items():
        code, status = str(constants["code"]), constants.get("status_code")
        where = f"{owner}: {cls} ({code})"
        match = ERROR_CODE.fullmatch(code)
        if not match:
            violations.append(f"{where}: not in the PLANTE_ABCD_NAME format")
            continue
        if not isinstance(status, int):
            violations.append(f"{where}: defines no literal status_code")
            continue
        family, module, kind = int(match[1]), int(match[2]), int(match[3])
        if module != MODULE_DIGITS.get(owner):
            violations.append(f"{where}: B={module}, but the class lives in {owner} ({MODULE_DIGITS.get(owner)})")
        if status // 100 != family:
            violations.append(f"{where}: A={family}, but status_code is {status}")
        elif status not in KIND_STATUSES.get((family, kind), frozenset()):
            violations.append(f"{where}: C={kind} does not allow status_code {status}")
    return violations


def _used_names(path: Path) -> set[str]:
    """Names a file raises, instantiates or declares in a use case's `raises` tuple."""
    def name_of(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        return node.attr if isinstance(node, ast.Attribute) else None

    used: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Call):
            used.add(name_of(node.func) or "")
        elif isinstance(node, ast.Raise) and node.exc is not None:
            used.add(name_of(node.exc) or "")
        elif (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "raises" for t in node.targets)
            and isinstance(node.value, ast.Tuple)
        ):
            used.update(name_of(element) or "" for element in node.value.elts)
    return used


def unused_errors(src_root: Path, exception_files: list[Path], allowed: frozenset[str] = frozenset()) -> list[str]:
    """
    Every error with a code is raised or built somewhere outside tests, or declared in a use case's
    `raises`. Being documented in `error_responses(...)` or caught in an `except` does not count.
    """
    used = {
        name
        for path in src_root.rglob("*.py")
        if "tests" not in path.relative_to(src_root).parts
        for name in _used_names(path)
    }
    return [
        f"{path.relative_to(src_root.parent)}: {cls} ({code}) is never raised"
        for path in exception_files
        for cls, code in defined_error_codes(path).items()
        if cls not in used and cls not in allowed
    ]


# --- Imports pelos barrels ---------------------------------------------------------------------

def module_name(path: Path, src_root: Path) -> str:
    parts = list(path.relative_to(src_root.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _imports(path: Path) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.lineno, node.module))
    return found


def barrel_violations(src_root: Path) -> list[str]:
    """
    - Outro módulo: só a raiz (`src.modules.<x>`); a composição também pode `container`, `api` e `workers`,
      e os testes de um módulo, os dublês publicados por outro (`src.modules.<x>.tests.fakes`).
    - Shared, de fora dele: só as camadas, ou os dublês dele nos testes (`src.shared.tests.fakes`).
    - Ninguém importa o barrel de um pacote que o contém (import circular, tudo carregado antes da hora).
    """
    violations: list[str] = []
    for path in sorted(src_root.rglob("*.py")):
        importer = module_name(path, src_root)
        is_composition = importer == "src.main" or importer.startswith("src.bootstrap")
        is_module_test = importer.startswith("src.modules.") and ".tests." in importer
        for line, target in _imports(path):
            where = f"{path.relative_to(src_root.parent)}:{line}"
            if importer != target and importer.startswith(target + "."):
                violations.append(f"{where}: importa o barrel do próprio pacote ({target})")
                continue
            parts = target.split(".")
            if parts[:2] == ["src", "modules"] and len(parts) > 3:
                owner = ".".join(parts[:3])
                inside = importer == owner or importer.startswith(owner + ".")
                composition_entry = is_composition and len(parts) == 4 and parts[3] in COMPOSITION_ENTRIES
                # Os dublês de uma porta moram no módulo dono dela, para os testes de quem a usa
                published_fakes = is_module_test and parts[3:] == ["tests", "fakes"]
                if not inside and not composition_entry and not published_fakes:
                    violations.append(f"{where}: {target} é interno de {owner}; importe {owner}")
            elif parts[:2] == ["src", "shared"] and len(parts) != 3:
                shared_fakes = is_module_test and parts[2:] == ["tests", "fakes"]
                if not importer.startswith("src.shared") and not shared_fakes:
                    allowed = ", ".join(f"src.shared.{layer}" for layer in SHARED_LAYERS)
                    violations.append(f"{where}: {target}: de fora do shared, importe uma camada ({allowed})")
    return violations


# --- AAA ---------------------------------------------------------------------------------------

_MARKER = re.compile(r"#\s*(Arrange|Act & Assert|Act|Assert)\b")


def aaa_violations(test_file: Path) -> list[str]:
    """
    Todo teste marca as fases com comentários: `# Arrange` (opcional), `# Act` e `# Assert`, nessa
    ordem; `# Act & Assert` vale pelos dois (ex.: `pytest.raises`).
    """
    source = test_file.read_text()
    comments: list[tuple[int, str]] = [
        (tok.start[0], match.group(1))
        for tok in tokenize.generate_tokens(io.StringIO(source).readline)
        if tok.type == tokenize.COMMENT and (match := _MARKER.match(tok.string))
    ]
    violations: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
            continue
        end = node.end_lineno or node.lineno
        markers = [name for line, name in comments if node.lineno <= line <= end]
        where = f"{test_file.name}::{node.name}"
        has_act = "Act" in markers or "Act & Assert" in markers
        has_assert = "Assert" in markers or "Act & Assert" in markers
        if not (has_act and has_assert):
            violations.append(f"{where}: faltam marcadores (# Act e # Assert, ou # Act & Assert)")
            continue
        order = {"Arrange": 0, "Act": 1, "Act & Assert": 1, "Assert": 2}
        ranks = [order[m] for m in markers]
        if ranks != sorted(ranks):
            violations.append(f"{where}: marcadores fora de ordem ({', '.join(markers)})")
    return violations
