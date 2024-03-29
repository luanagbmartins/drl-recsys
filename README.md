# DRL Recsys

## Algoritmos avaliados
- DRR: Agente de aprendizado por reforço baseado no trabalho de Liu et al. (2018).
- FairRec: Agente de aprendizado por reforço baseado no trabalho de Liu et al. (2020).

## Estrutura

- data                      <-- Dados brutos e processados
- model                     <-- Modelos treinados
- notebook                  <-- Jupyter notebooks
    - bandits.ipynb         <-- Treinamento dos algorimtos de bandits (egreedy, linucb)
    - movie_lens.ipynb      <-- Treinamento do modelo de PMF para o dataset movie_lens e análise dos embeddings
    - yahoo.ipynb           <-- Treinamento do modelo de PMF para o dataset yahoo e análise dos embeddings
    
- src
    - data                  <-- Código para gerar o dataset (disponíveis: movie_lens_100k, movie_lens_1m, yahoo)
    - environment           <-- Código dos ambientes OfflineEnv (DRR) e OfflineFairEnv (FairRec)
    - model                 <-- Códigos dos modelos e redes neurais (actor, critic, state_representation)
        - recommender       <-- Agentes de recomendação (DRR, FairRec)
    - train_model           <-- Código por inicializar um agente de recomendação (drr e fairrec) e começar o treinamento
    - recsys_fair_metrics   <-- [Módulo de métrica de exposição](https://github.com/marlesson/recsys-fair-metrics)

## Experimentos
    Versões disponíveis: movie_lens_100k, movie_lens_1m, yahoo

### Geração do dataset
`python -m luigi --module src.data.dataset DatasetGeneration --dataset-version movie_lens_100k --local-scheduler`

### Treinamento
- Alterar os parâmetros desejados em `model/{versão}.yaml`
- Rodar o treinamento:
    `bash ml.sh`

#### Bandits
- Código de treinamento disponível em: `notebooks/bandits.ipynb`

# Referências

Singh, A., & Joachims, T. (2018). **Fairness of Exposure in Rankings.** Proceedings of the 24th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining.

Patil, V., Ghalme, G., Nair, V.J., & Narahari, Y. (2020). **Achieving Fairness in the Stochastic Multi-armed Bandit Problem.** ArXiv, abs/1907.10516.

Liu, F., Tang, R., Li, X., Ye, Y., Chen, H., Guo, H., & Zhang, Y. (2018). **Deep Reinforcement Learning based Recommendation with Explicit User-Item Interactions Modeling.** ArXiv, abs/1810.12027.

Liu, W., Liu, F., Tang, R., Liao, B., Chen, G., & Heng, P. (2020). **Balancing Between Accuracy and Fairness for Interactive Recommendation with Reinforcement Learning.** Advances in Knowledge Discovery and Data Mining, 12084, 155 - 167.
