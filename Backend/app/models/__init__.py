# Importar todos os modelos garante que o SQLAlchemy os registre no metadata
# antes de Base.metadata.create_all() ser chamado.
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.solicitacoes_acesso import SolicitacaoAcesso
from app.models.itens import Item
from app.models.importacoes import Importacao
from app.models.consumo import Consumo
from app.models.consumo_tratado import ConsumoTratado
from app.models.classificacao_abc import ClassificacaoABC
from app.models.modelo_treinado import ModeloTreinado
from app.models.previsoes import Previsao
from app.models.feriados import Feriado
from app.models.feriado_sincronizacao import FeriadoSincronizacao

__all__ = [
    "Empresa",
    "Usuario",
    "SolicitacaoAcesso",
    "Item",
    "Importacao",
    "Consumo",
    "ConsumoTratado",
    "ClassificacaoABC",
    "ModeloTreinado",
    "Previsao",
    "Feriado",
    "FeriadoSincronizacao",
]
