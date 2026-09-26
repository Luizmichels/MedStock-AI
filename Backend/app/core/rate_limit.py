"""Rate limiting simples em memória, por IP (processo único — TCC).

Usado no endpoint público de solicitação de acesso para mitigar abuso.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class LimitadorDeTaxa:
    def __init__(self, limite: int = 5, janela_segundos: int = 60):
        self.limite = limite
        self.janela = janela_segundos
        self._acessos: dict[str, deque] = defaultdict(deque)

    def reset(self) -> None:
        self._acessos.clear()

    def __call__(self, request: Request) -> None:
        agora = time.monotonic()
        ip = request.client.host if request.client else "desconhecido"
        fila = self._acessos[ip]
        while fila and agora - fila[0] > self.janela:
            fila.popleft()
        if len(fila) >= self.limite:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas requisições. Tente novamente em instantes.",
            )
        fila.append(agora)


limitador_solicitacoes = LimitadorDeTaxa(limite=5, janela_segundos=60)
