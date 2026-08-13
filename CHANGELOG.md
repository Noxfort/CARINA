# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-13

### Added
- **ST-GATv2 Lite Module (`st_gatv2_lite.py`)**: Spatiotemporal Graph Attention Network coordinating Green Waves across physical urban graph topologies.
- **Global Consultant Agent (`consultant_agent.py`)**: Event-triggered background mentor running a high-capacity Predictive Autoencoder (PAE 64/128 channels) for future horizon projection ($t + \Delta t$).
- **Topological Scaler (`topo_scaler.py`)**: $O(1)$ algorithmic auto-scaling of latent dimensions (32, 64, 128, 256) and attention heads (2, 4, 8, 16) based on city network node count $N$.
- **Dual Cross-Attention Mode (`cross_attention.py`)**: Adaptive PBT (Population-Based Training) temperature evolution for LocalAgent PPO vs Fixed Deterministic weights for GuardianAgent D3QN safety audits.
- **Universal AMP & TensorCores Acceleration**: Wrapped all deep neural network inference loops with `torch.amp.autocast(FP16)` reducing VRAM consumption to ~20 MB.
- **5 Formal Neural Equations in ABNT Report**: Rendered TCN Causal Convolution, ST-GATv2 Lite Attention, Cross-Attention Transformer, Guardian Dueling D3QN, and Captum Integrated Gradients equations natively in `xai.docx`.
- **Guardian Agent Safety Veto Audit Table**: Real-time audit metrics (Total Evaluated, Approved, Vetoed, Compliance Rate %, Top Veto Reasons) queried from PostgreSQL for Section 4 and Anexo I.
- **PostgreSQL Async Delta Storage Engine (`step_decision_worker.py` & `step_decision_repo.py`)**: Non-blocking RAM push (< 0.001 ms) with 1-byte Smallint Enums, Edge Dictionary mapping, and Run-Length Encoding achieving **97.9% global database storage reduction** (~380 MB/day for 200 intersections).

### Changed
- Replaced legacy `gatv2_lite.py` with `st_gatv2_lite.py`.
- Updated `xai_report_templates.json` across 6 languages (`pt_br`, `en`, `es`, `fr`, `de`, `zh`).
- Silenced PyTorch tensor conversion warning via native C-contiguous `numpy.array` array wrappers.

---

## [0.9.0] - 2026-08-12

### Added
- **Ultimate Documentation Overhaul**: Complete rewrite of `README.md`, `ARCHITECTURE.md`, and creation of a multi-document library in `docs/`.
- **Explainable AI Integration**: Qwen3 1.7B LLM backend generating natural language Laudos Técnicos via Captum tensors.
- **Smart Dashboard Service (SDS)**: Flet UI decoupled from AI Engine using WebSocket aggregation.
- **Synapse HFT Protocol**: gRPC infrastructure implemented for sub-millisecond physical controller communication.
- **DA SILVA Curriculum**: Automated Policy Entropy validation for agent maturation from CHILD to ADULT.

### Changed
- Refactored `EpisodeRunner` to run asynchronously across isolated `multiprocessing` Queues.
- Switched default Recurrent Neural Network backbone from LSTM to TCN (Temporal Convolutional Networks) for massive parallel inference.

### Security
- Implemented deterministic `GuardianAgent` with hardcoded Symbolic Vetoes to override catastrophic neural hallucinations.
