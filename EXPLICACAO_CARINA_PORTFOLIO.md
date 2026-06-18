# CARINA - Explicação para Portfólio (Versão Leiga)

## 🚦 O Que é a CARINA?

Imagine que o trânsito da sua cidade é como uma orquestra. Sem um maestro, cada músico toca no seu próprio ritmo, resultando em caos e barulho. A **CARINA** é exatamente esse maestro, mas para o trânsito urbano.

**CARINA** significa *Controlled Artificial Road-traffic Intelligence Network Architecture* (Arquitetura de Rede de Inteligência Artificial Controlada para Tráfego Viário). Em termos simples: é um **sistema de Inteligência Artificial que controla semáforos de forma inteligente** para fazer o trânsito fluir melhor.

### Como funciona? (Explicação Simplificada)

1. **Os "Olhos" do Sistema (Synapse)**: Câmeras e sensores nas ruas observam quantos carros estão passando, onde há filas e qual a velocidade do tráfego. Essas informações são capturadas pelo **Synapse**, um sistema de visão computacional que "enxerga" o trânsito e envia todos os dados para a CARINA.

2. **O "Cérebro" (CARINA)**: A IA da CARINA recebe as informações do Synapse em tempo real e toma decisões inteligentes. Diferente dos semáforos tradicionais (que ficam verde por 30 segundos mesmo se a rua estiver vazia), a CARINA ajusta os tempos **dinamicamente**.

3. **A "Ação"**: A própria CARINA envia comandos diretos para os semáforos físicos nas ruas, mudando as luzes no momento certo para evitar congestionamentos.

### Por que isso é importante?

- ✅ **Menos tempo parado no sinal vermelho** quando não há carros na outra via
- ✅ **Economia de combustível** e redução da poluição
- ✅ **Mais fluidez** no trânsito da cidade
- ✅ **Segurança**: Se o sistema falhar, os semáforos voltam automaticamente para um modo seguro de emergência

---

## 🖥️ As Abas do Sistema (Interface do Usuário)

A CARINA possui uma interface visual moderna que permite aos operadores monitorar e controlar o trânsito da cidade. Veja o que cada aba faz:

---

### 1️⃣ **Dashboard (Centro de Operações)**
**Ícone**: 📊 *Painel de Controle*

**O que é**: É a tela principal de monitoramento em tempo real. Pense nela como o "painel de controle" de todo o sistema de trânsito.

**O que você vê aqui**:
- 🗺️ **Mapa Interativo da Cidade**: Mostra todos os cruzamentos e semáforos em tempo real
- 🚦 **Status dos Semáforos**: Cada semáforo aparece colorido indicando se está funcionando normalmente, se há algum problema ou se está sob controle manual
- 🚗 **Fluxo de Tráfego**: Visualização das vias com cores que indicam se o trânsito está fluido (verde), moderado (amarelo) ou congestionado (vermelho)
- ⚙️ **Painel de Controle Lateral**: Ao clicar em um semáforo específico, você pode ver detalhes como:
  - Qual fase do semáforo está ativa (ex: "verde para avenida principal")
  - Tempo restante para mudar a luz
  - Opção de assumir controle manual se necessário
  - Histórico recente de operação

**Para quem é útil**: Operadores de trânsito que precisam tomar decisões rápidas e monitorar a cidade inteira de um só lugar.

---

### 2️⃣ **Planning (Planejamento de Infraestrutura)**
**Ícone**: 🛠️ *Ferramentas de Planejamento*

**O que é**: Uma aba focada em **análise e planejamento futuro**. Enquanto o Dashboard mostra o "agora", esta aba ajuda a pensar no "amanhã".

**O que você vê aqui**:
- 🗺️ **Mapa de Recomendações**: A IA analisa dados históricos e sugere melhorias na infraestrutura
- 💡 **Sugestões Inteligentes**: O sistema identifica cruzamentos que poderiam se beneficiar de:
  - Adição de novos semáforos
  - Remoção de semáforos desnecessários
  - Ajustes na sincronização entre cruzamentos
- 📊 **Legenda Visual**:
  - 🔵 **Azul**: Semáforos que devem ser mantidos como estão
  - 🔴 **Vermelho**: Semáforos que poderiam ser removidos (não são essenciais)
  - 🟢 **Verde**: Locais onde novos semáforos deveriam ser instalados
  - 🟠 **Laranja**: Cruzamentos importantes
  - ⬛ **Linhas Pretas**: Vias e ruas da cidade

**Funcionalidades Especiais**:
- 📄 **Gerar Relatório**: Cria um documento detalhado com todas as recomendações da IA para apresentar a engenheiros de trânsito ou gestores públicos
- 🔄 **Análise de Impacto**: Mostra se as mudanças recomendadas trarão benefícios significativos

**Para quem é útil**: Planejadores urbanos, engenheiros de tráfego e gestores públicos que precisam tomar decisões sobre investimentos em infraestrutura.

---

### 3️⃣ **Diagnostics (Diagnósticos do Sistema)**
**Ícone**: 🔧 *Ferramentas de Diagnóstico*

**O que é**: A aba técnica para **monitorar a saúde do sistema** e entender como a IA está tomando suas decisões.

**O que você vê aqui** (dividido em 3 sub-abas):

#### 📋 **Logs do Sistema**
- Registro detalhado de tudo que acontece no sistema
- Mensagens de erro, avisos e informações operacionais
- Útil para identificar problemas técnicos rapidamente

#### 🧠 **Análise Neural (XAI - Inteligência Artificial Explicável)**
- **O que a IA está "pensando"**: Mostra quais fatores a inteligência artificial considerou para tomar cada decisão
- **Transparência**: Explica por que um semáforo ficou verde por mais tempo em determinado momento
- **Agentes de IA**: Lista os diferentes "cérebros" da IA responsáveis por cada região da cidade
- **Gráficos e Métricas**: Visualizações que mostram o processo de aprendizado da máquina

#### 📜 **Auditoria (Audit Logs)**
- **Registro de Ações Humanas**: Quem fez o quê e quando
- **Controle Manual**: Todas as vezes que um operador assumiu o controle de um semáforo
- **Conformidade**: Garante que todas as operações estejam documentadas para fins de auditoria e segurança

**Para quem é útil**: Técnicos de TI, administradores do sistema e auditores que precisam garantir que tudo esteja funcionando corretamente e de forma transparente.

---

### 4️⃣ **Configurações (Settings)**
**Ícone**: ⚙️ *Engrenagem de Configuração*

**O que é**: Onde os administradores podem **personalizar o comportamento do sistema**.

**O que você pode configurar**:
- 🌐 **Idioma**: Escolha entre diferentes idiomas para a interface
- 🔒 **Segurança**: Gerenciamento de usuários, senhas e permissões de acesso
- 🎛️ **Parâmetros da IA**: Ajustes finos de como a inteligência artificial toma decisões
- 🔌 **Hardware**: Configuração de como a CARINA se comunica com os semáforos físicos
- 📊 **Preferências de Exibição**: Personalização de cores, alertas e notificações

**Recursos de Segurança**:
- ✋ **Botão de Emergência**: Permite encerrar o aplicativo de forma segura
- 💾 **Salvar/Restaurar**: Salva configurações personalizadas ou restaura para o padrão de fábrica
- 🔐 **Autenticação**: Solicita senha antes de permitir alterações críticas

**Para quem é útil**: Administradores do sistema e operadores autorizados.

---

## 🎯 Resumo Visual

| Aba | Ícone | Função Principal | Público-Alvo |
|-----|-------|------------------|--------------|
| **Dashboard** | 📊 | Monitoramento em Tempo Real | Operadores de Trânsito |
| **Planning** | 🛠️ | Análise e Planejamento Futuro | Planejadores Urbanos |
| **Diagnostics** | 🔧 | Saúde do Sistema e Transparência | Técnicos e Auditores |
| **Settings** | ⚙️ | Configuração e Personalização | Administradores |

---

## 💡 Tecnologias Utilizadas (Para Curiosos)

Se você tem interesse técnico, a CARINA foi construída com:

- **Frontend**: Flet (Python) - Interface moderna e responsiva
- **Backend**: Python com Redes Neurais para tomada de decisão
- **Comunicação**: gRPC para transmissão ultrarrápida de dados
- **Visão Computacional**: Synapse - Sistema irmão que captura imagens do trânsito e envia os dados processados para a CARINA
- **Protocolos Industriais**: NTCIP e UTMC2 para comunicação com semáforos físicos
- **Banco de Dados**: Armazenamento de dados históricos e logs

---

## 🌟 Diferenciais da CARINA

1. **Não é apenas um "timer inteligente"**: A IA realmente *aprende* com os padrões de tráfego
2. **Funciona com qualquer marca de semáforo**: Sistema "agnóstico" que se adapta ao hardware existente
3. **Segurança em primeiro lugar**: Múltiplos sistemas de fallback garantem que o trânsito nunca fique sem controle
4. **Transparente**: Você pode ver e entender *por que* a IA tomou cada decisão
5. **Código Aberto**: Disponível para cidades e desenvolvedores ao redor do mundo

---

## 📞 Casos de Uso Reais

- **Horário de Pico**: A CARINA prioriza avenidas principais durante rush matinal e vespertino
- **Eventos Especiais**: Durante jogos ou shows, o sistema se adapta ao fluxo incomum
- **Emergências**: Pode dar prioridade para veículos de emergência (ambulâncias, bombeiros)
- **Chuva ou Acidentes**: Reage automaticamente a condições adversas, redistribuindo o tráfego

---

**CARINA** - Tornando as cidades mais inteligentes, uma interseção de cada vez. 🚦🏙️
