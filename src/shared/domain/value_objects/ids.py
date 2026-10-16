"""
Identificador comum a todos os módulos. Os demais IDs moram no módulo dono da entidade.

Todo ID é um UUID gerado pelo domínio no momento da criação (nunca pelo banco), com um tipo
próprio para o mypy impedir que o ID de uma entidade seja passado no lugar do de outra.
"""
from typing import NewType
from uuid import UUID

UserId = NewType("UserId", UUID)
