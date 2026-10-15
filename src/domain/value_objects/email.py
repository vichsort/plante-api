def normalize_email(value: str) -> str:
    """
    Forma canônica do e-mail: sem espaços nas pontas e em minúsculas. A parte local é sensível
    a maiúsculas pela RFC 5321, mas na prática nenhum provedor a trata assim; normalizar evita
    duas contas para a mesma caixa de entrada e login que falha por causa da caixa.
    """
    return value.strip().lower()
