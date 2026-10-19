# Mapa do domínio (transitório)

Regras de negócio de cada subdomínio enquanto o código ainda está nas camadas antigas
(`src/domain`, `src/adapters`, `src/api`, `src/workers`). **Este arquivo encolhe a cada módulo
migrado**: a seção do subdomínio vai para o `README.md` do módulo (Propósito, Decisões, Erros) e
sai daqui. Quando o último módulo migrar, o arquivo é apagado.

Já migrados: `training`, `catalog`, `subscription`, `identity`, `identification`, `garden` e `health` (README de cada um em `src/modules/`).

As regras de arquitetura estão no `ARCHITECTURE.md`; o kernel comum, em `src/shared/README.md`.

| Seção | Vai para o módulo |
| :--- | :--- |
| Gamificação | `achievements` |

---

## Gamificação (`Gamification Context`)
* **Propósito**: Concessão e listagem de conquistas (`Badges`). Conta e perfil: `src/modules/identity/README.md`; plano e cota de tokens: `src/modules/subscription/README.md`.
* **Entidades Principais**: `Achievement`.
* **Entradas (Use Cases)**: `ListUserAchievementsUseCase`.
* **Ports Requeridos**: `IAchievementRepository`.

---
