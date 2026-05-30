# 🧪 Testing Guidelines

CARINA controls critical traffic infrastructure. Code coverage and deterministic test validations are strictly enforced.

## Running the Test Suite

The project uses `pytest`. The test suite is located in the `tests/` directory.

### Requirements
Ensure you have the testing requirements installed:
```bash
pip install pytest pytest-cov
```

### Executing Tests
To run the entire suite and generate a coverage report:
```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

## Writing Tests

### Unit Tests
- Files should be named `test_<module_name>.py`.
- Mock external dependencies heavily, especially the `SumoEnvironment` and the `Qwen3` LLM backend.
- Avoid spinning up actual `multiprocessing` processes in unit tests. Use mock queues.

### Safety-Critical Components
If you modify `src/agents/guardian_agent.py` or `src/engine/action_filter.py`, you **MUST** provide a test case proving that your new logic correctly issues an `ACTION_KEEP_PHASE` veto when unsafe states are artificially injected.
