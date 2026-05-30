# 🤖 Explainable AI (XAI) & Smart Analysis System (SAS)

CARINA is not a black box. It actively explains its neural decisions and provides continuous traffic engineering consulting. Both systems run in entirely separate OS processes due to their massive computational footprint.

## 1. Explainable AI (`XAI_Worker`)

Located in `src/xai/`, this subsystem translates raw neural tensors into human-readable text.

### 1.1 Captum Tensor Extraction
- **File**: `captum_analyzer.py`
- **Function**: Uses PyTorch's `Captum` library to calculate Integrated Gradients. It mathematically traces back which specific input node (e.g., *Occupancy on Edge A at t-3*) caused the TCN to output a specific Q-Value.

### 1.2 The Semantic Transducer (Qwen3 LLM)
- **File**: `semantic_transducer.py`
- **Function**: A raw matrix of integrated gradients means nothing to a city mayor. The transducer takes these numerical arrays and injects them into a highly optimized prompt.
- **Inference**: The `Qwen3 1.7B` LLM (loaded directly into VRAM) reads this prompt and generates a "Laudo Técnico" (Technical Report) in natural language, explaining exactly *why* the AI took a specific action.

---

## 2. Smart Analysis System (`AnalysisService`)

Located in `src/sas/`, this is the infrastructure consulting engine.

### 2.1 The Analyzer Engine
- **File**: `analyzer_engine.py`
- **Function**: While the `EpisodeRunner` optimizes green lights, the SAS looks at the macro picture. It periodically scans the `PostgreSQL` database, analyzing weeks of historical throughput.
- **Traffic Warrants**: It cross-references this historical data against established Global Traffic Engineering Warrants. If an intersection's volume is consistently too low, SAS generates a formal recommendation to remove the physical traffic light and replace it with a Stop Sign or Roundabout.
