# Contributing to CARINA

First off, thank you for considering contributing to CARINA! It's people like you that make CARINA an incredible tool for urban mobility.

## Development Setup

1. Fork the repo and create your branch from `main`.
2. Follow the `docs/DEVELOPER_GUIDES.md` for local setup.
3. If you've added code that should be tested, add tests in the `tests/` directory.

## Testing Guidelines
Before submitting a Pull Request, ensure that all unit tests pass. 
Please read **[docs/TESTING.md](docs/TESTING.md)** for instructions on how to run the `pytest` suite and generate coverage reports.

## Pull Request Process
1. Ensure your code strictly follows the **SOLID** principles outlined in `ARCHITECTURE.md`.
2. Update the `README.md` or the `docs/` library with details of changes to the interface or architecture.
3. The PR will be reviewed by the core maintainers. If your PR modifies the `GuardianAgent` or `ActionFilter`, it will require a rigorous secondary security review.
