# 🔬 Neural Research & GOMES Formulations

This document provides a technical deep-dive into the custom neural network architectures, the DA SILVA curriculum, and the mathematical formulations utilized by the **GOMES** (Graph-based Operational Multi-agent Expert System) engine.

## 1. PPO-TCN: Temporal Convolutional Networks over LSTMs

Traditional Reinforcement Learning relies heavily on Recurrent Neural Networks (RNNs or LSTMs) to handle partially observable environments (POMDPs). CARINA abandons RNNs in favor of **Temporal Convolutional Networks (TCN)** (`src/models/actor_critic_tcn.py`).

### Why TCN?
1. **No Backpropagation Through Time (BPTT)**: TCNs use causal dilated convolutions. This eliminates the vanishing/exploding gradient problems inherent to LSTMs when processing long traffic queues.
2. **Massive Parallelism**: Unlike LSTMs, which must process sequences sequentially, 1D convolutions process the entire sequence window simultaneously on the GPU.
3. **Receptive Field Control**: By increasing the dilation factor, CARINA can geometrically expand its historical look-back window without drastically increasing parameter count.

### The Objective Function
CARINA's PPO surrogate clipping objective prevents catastrophic forgetting during live traffic adaptations:
$$L^{CLIP}(\theta) = \hat{E}_t [ \min(r_t(\theta)\hat{A}_t, \text{clip}(r_t(\theta), 1-\epsilon, 1+\epsilon)\hat{A}_t) ]$$

---

## 2. Universal Predictive Autoencoder (PAE)

Defined in `src/models/pae.py`, the PAE is a self-supervised generative model trained concurrently with the RL agents.

### Latent Fluid Dynamics
The PAE receives a sequence of traffic states $S_{t-n \dots t}$ and is trained to predict the future state $S_{t+1}$. 
The mathematical magic happens in the **Latent Space ($Z$)**. The high-dimensional physical representation is compressed into a dense vector. This latent vector $Z$ is dynamically fused into the input layer of both the Tactical PPO Agent and the Guardian DQN Agent. 
By "reading" the PAE's latent space, the RL agents intuitively understand momentum, vehicle platooning, and spillback physics without having to learn it through sparse trial-and-error rewards.

---

## 3. Dueling DQN-TCN (The Guardian's Brain)

The Guardian Agent (`src/agents/guardian_agent.py`) uses a specialized `Dueling DQN-TCN` architecture (`src/models/d3qn_tcn.py`). 

### Stream Splitting
The network bifurcates into two separate streams after the TCN layers:
1. **State Value Stream ($V(s)$)**: Estimates how intrinsically safe/dangerous the current global intersection state is, regardless of the light phase.
2. **Advantage Stream ($A(s, a)$)**: Estimates the relative safety of keeping the phase vs changing the phase.

These are aggregated mathematically at the output layer:
$$ Q(s,a) = V(s) + \left( A(s,a) - \frac{1}{|\mathcal{A}|} \sum_{a'} A(s,a') \right) $$
This separation ensures that if the intersection is in a catastrophic gridlock (low $V(s)$), the Guardian recognizes the danger immediately, overriding the tactical agent's commands.

---

## 4. The DA SILVA Statistical Maturation

The `ChildhoodAnalyzer` oversees the agent's growth. It tracks the mathematical **Policy Entropy** (how "unsure" the network is) and the **Cumulative Rewards**. 

- **Entropy Stabilization**: An agent must prove its Entropy falls below $0.15$ before graduating from `TEEN` to `ADULT`. This proves the network is no longer randomly guessing.
- **Hardware Integration**: The `ActionFilter` strictly enforces these maturation stages, mathematically dropping actions requested by `CHILD` agents before they reach the physical controller.
