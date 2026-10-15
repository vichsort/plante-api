from pathlib import Path

_SRC = Path(__file__).parents[1] / "src"


def test_every_source_directory_is_a_regular_package() -> None:
    # O import-linter não enxerga namespace packages: sem `__init__.py`, os módulos ficam fora
    # dos contratos de camada sem nenhum aviso
    missing = [
        str(directory.relative_to(_SRC.parent))
        for directory in [_SRC, *_SRC.rglob("*")]
        if directory.is_dir()
        and directory.name != "__pycache__"
        and any(directory.glob("*.py"))
        and not (directory / "__init__.py").exists()
    ]
    assert missing == []
