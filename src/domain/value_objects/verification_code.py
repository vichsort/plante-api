import re
from dataclasses import dataclass

@dataclass(frozen=True)
class VerificationCode:
    """
    Formato esperado: PLA-123-V-456 (ou PLA123V456).
    Onde V é o dígito verificador.
    """
    raw_code: str

    def __post_init__(self):
        # Removemos hífens e espaços para padronizar
        clean_code = self.raw_code.replace("-", "").strip().upper()
        
        # Validamos o formato via Regex (PLA + 3 num + 1 num + 3 num = 10 chars)
        if not re.match(r"^PLA\d{7}$", clean_code):
            raise ValueError("O código de verificação está em um formato inválido.")
            
        # Extraímos as partes
        prefix = clean_code[0:3] # PLA
        first_part = clean_code[3:6] # 3 dígitos
        v_digit = int(clean_code[6]) # O dígito V
        second_part = clean_code[7:10] # 3 dígitos

        # REGRA DE NEGÓCIO: O dígito V é válido? 
        # Exemplo de regra: A soma dos 6 dígitos módulo 10 deve ser igual a V.
        all_digits = [int(d) for d in first_part + second_part]
        expected_v = sum(all_digits) % 10
        
        if v_digit != expected_v:
            raise ValueError("Código de verificação corrompido ou inválido (Falha de Checksum).")

        # Se passou por tudo, podemos salvar a versão limpa.
        # Contornando o frozen=True do dataclass:
        object.__setattr__(self, 'raw_code', clean_code)

    def __str__(self):
        return self.raw_code