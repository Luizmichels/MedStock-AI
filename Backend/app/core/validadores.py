import re


def cnpj_valido(cnpj: str) -> bool:
    numeros = re.sub(r"\D", "", cnpj)

    if len(numeros) != 14:
        return False

    # CNPJs com todos os dígitos iguais são sempre inválidos (ex: 00.000.000/0000-00)
    if numeros == numeros[0] * 14:
        return False

    def calcular_digito_verificador(base: str) -> int:
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos_usados = pesos[-len(base):]
        soma = sum(int(digito) * peso for digito, peso in zip(base, pesos_usados))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    primeiro_digito = calcular_digito_verificador(numeros[:12])
    segundo_digito = calcular_digito_verificador(numeros[:12] + str(primeiro_digito))

    return numeros[-2:] == f"{primeiro_digito}{segundo_digito}"