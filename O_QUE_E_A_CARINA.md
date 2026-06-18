# O Que é a CARINA?

**CARINA** (do inglês *Controlled Artificial Road-traffic Intelligence Network Architecture* - Arquitetura de Rede de Inteligência Artificial Controlada para Tráfego Viário) é um sistema central de Inteligência Artificial projetado para gerenciar e otimizar o fluxo de trânsito em Cidades Inteligentes (Smart Cities).

Enquanto sistemas tradicionais de trânsito operam com tempos engessados (ex: o semáforo fica verde por 30 segundos, não importando se a via está vazia), a CARINA atua como o "cérebro digital" da cidade. O seu diferencial é reagir à realidade da rua em tempo real, calculando continuamente a melhor configuração para escoar o trânsito com máxima eficiência.

## A Arquitetura: Percepção (Synapse) e Ação (CARINA)

A operação de tráfego inteligente exige olhos nas ruas e um cérebro rápido. O ecossistema funciona dividindo de forma muito inteligente essa tarefa entre o Synapse e a CARINA:

1. **Os Olhos e a Percepção (Synapse):** O Synapse é a plataforma de visão computacional e interpretação de sensores. Ele se conecta às câmeras, radares e espiras no asfalto. O seu único e vital trabalho é gerar um **mapa digital perfeito do trânsito em tempo real**, consolidando e traduzindo o posicionamento dos veículos, as filas e velocidades, e transmitindo essa "fotografia perfeita" ininterruptamente para a CARINA através de um canal ultrarrápido (chamado gRPC).
2. **O Cérebro e o Controle Direto (CARINA):** A CARINA não possui câmeras; ela enxerga a cidade consumindo o mapa perfeito criado pelo Synapse. Ao analisar esse quadro usando Redes Neurais e matemática complexa, a IA descobre onde estão os gargalos em formação e toma a decisão estratégica. Mas a CARINA não apenas pensa: é a **própria CARINA que se conecta e "fala" diretamente com os controladores físicos de semáforos** (as caixas metálicas nos postes), emitindo as ordens operacionais (utilizando protocolos industriais como NTCIP ou UTMC2).

## Como o Sistema Trabalha na Prática?

O processo de otimização flui continuamente em frações de segundo:

1. **A Leitura Perfeita:** O Synapse extrai informações do caos das ruas através das câmeras e entrega para a CARINA um espelho digital perfeito de onde estão os carros no cruzamento.
2. **A Grande Decisão Neural:** A CARINA recebe esse espelho e processa o cenário global. Seus algoritmos decidem matematicamente se vale a pena estender o verde da avenida principal ou se é hora de liberar a rua transversal, visando o menor tempo de espera para todos.
3. **A Execução:** Imediatamente após a decisão, a CARINA se comunica diretamente com o hardware de trânsito da cidade, ajustando e impondo as novas luzes semafóricas.

## Principais Diferenciais

*   **Agnosticidade a Controladores:** A CARINA possui módulos internos de tradução chamados *Drivers*. Isso significa que ela pode comandar diretamente controladores de semáforos de diversas marcas diferentes ao mesmo tempo. Se a cidade modernizar os aparelhos das ruas, a inteligência da CARINA se adapta perfeitamente.
*   **Fim do "Parar no Sinal Vermelho à Toa":** Ao governar os cruzamentos dinamicamente, os motoristas gastam muito menos tempo parados no vermelho quando a outra via está vazia. Isso gera uma enorme economia de combustível, além de reduzir radicalmente a emissão de carbono da frota ociosa.
*   **Segurança em Primeiro Lugar (Failsafe e Watchdog):** O trânsito exige segurança impecável. Por atuar diretamente com o equipamento da rua, a CARINA possui um sistema rigoroso de *Heartbeat* (batimento cardíaco). Ela emite um pulso de controle constante para os semáforos. Caso a conexão de rede da cidade caia ou a CARINA perca a comunicação com a internet, o próprio hardware na rua e o módulo interno de *Failsafe* detectam a falha. Instantaneamente a CARINA suspende seu controle, força um tempo de "Vermelho Geral" rápido de emergência para frear todo o cruzamento e, em seguida, deixa o semáforo assumir seu modo fixo de backup local, garantindo que o trânsito nunca fique no escuro.

Em resumo, a CARINA é a Inteligência Artificial central de ponta que consome a percepção cristalina do trânsito gerada pelo Synapse e atua comandando, de forma direta e agnóstica, toda a rede física de semáforos da cidade com máxima fluidez e segurança absoluta.
