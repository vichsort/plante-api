"""
Kernel e infraestrutura comuns a todos os módulos. Importa-se pelas camadas (`src.shared.domain`,
`src.shared.adapters`, `src.shared.api`, `src.shared.workers`), nunca pela raiz: o domínio de um
módulo só pode puxar a camada pura (`src.shared.domain`).
"""
