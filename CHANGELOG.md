# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Ultimate Documentation Overhaul**: Complete rewrite of `README.md`, `ARCHITECTURE.md`, and creation of a multi-document library in `docs/`.
- **Explainable AI Integration**: Qwen3 1.7B LLM backend now successfully generates natural language `Laudos Técnicos` via Captum tensors.
- **Smart Dashboard Service (SDS)**: Flet UI decoupled from AI Engine using WebSocket aggregation.
- **Synapse HFT Protocol**: gRPC infrastructure implemented for sub-millisecond physical controller communication.
- **DA SILVA Curriculum**: Automated Policy Entropy validation for agent maturation from CHILD to ADULT.

### Changed
- Refactored `EpisodeRunner` to run asynchronously across 7 isolated `multiprocessing` Queues.
- Switched default Recurrent Neural Network backbone from LSTM to TCN (Temporal Convolutional Networks) for massive parallel inference.

### Security
- Implemented deterministic `GuardianAgent` with hardcoded Symbolic Vetoes to override catastrophic neural hallucinations.
