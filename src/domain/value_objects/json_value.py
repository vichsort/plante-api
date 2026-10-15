"""
Valor JSON arbitrário, para payloads que o domínio guarda sem interpretar (ex.: `raw_response`
dos provedores, mantido para o dataset de treino). Quem precisa ler um campo usa um modelo
próprio na borda, não navega neste tipo.

`TypeAliasType` (e não a sintaxe `type X = ...`) porque o Pydantic 2.9 só entende o alias
recursivo nessa forma.
"""

from typing_extensions import TypeAliasType  # noqa: UP035

# noqa UP035/UP040: o ruff trocaria pelo `typing.TypeAliasType` / `type X = ...`, que o
# Pydantic 2.9 não entende (só a versão do typing_extensions)
JsonValue = TypeAliasType(  # noqa: UP040
    "JsonValue",
    "str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]",
)
JsonObject = TypeAliasType("JsonObject", "dict[str, JsonValue]")  # noqa: UP040
