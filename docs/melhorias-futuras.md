# Melhorias futuras

Ideias levantadas durante o desenvolvimento, para avaliar depois. Não são bugs:
o sistema funciona sem elas.

## Machine learning

### Convergência do SARIMA no treino mensal
- **Sintoma:** durante o treino aparecem no log avisos
  `ConvergenceWarning: Maximum Likelihood optimization failed to converge`
  (statsmodels), um por item cujo ajuste não estabilizou.
- **Causa:** séries curtas, intermitentes (muitos meses zerados) ou quase
  constantes; o `SARIMAX.fit` roda com o limite padrão de iterações
  (`Backend/app/services/ml/estimadores.py`, classe `_EstimadorSARIMA`).
- **Impacto hoje:** baixo. A seleção do algoritmo é por item e pelo menor MAE
  na validação, então um SARIMA mal ajustado tende a perder para outro método.
- **Proposta:**
  1. Subir `maxiter` (ex.: 200) no `fit`.
  2. Se `mle_retvals["converged"]` for falso, usar a média histórica (fallback)
     em vez do ajuste não convergido.
  3. Suprimir o aviso repetido e registrar um resumo no fim do treino
     (ex.: "SARIMA não convergiu em 37 de 412 itens").
- **Custo:** treino um pouco mais lento.

## Dashboard

### Drilldown nos gráficos
- Permitir clicar num gráfico e abrir o detalhe por grupo → subgrupo → classe →
  item, e por setor.
