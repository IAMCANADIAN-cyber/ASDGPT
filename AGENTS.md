# Guidelines for AI Agents Working on ASDGPT

This document provides guidelines and instructions for AI agents (like you!) contributing to the ASDGPT project.

## General Principles

*   **Understand the Goal**: ASDGPT aims to be an autonomous co-regulator using sensor data and LMMs. Keep this high-level goal in mind when making changes.
*   **Maintain Modularity**: The project is structured into `core`, `sensors`, and other components. Strive to keep these modules loosely coupled and maintain clear responsibilities for each.
*   **Read Existing Code**: Before implementing new features or making changes, familiarize yourself with the relevant existing code and patterns.
*   **Prioritize Clarity**: Write clear, commented, and maintainable code.

## Python and Coding Style

*   **Python Version**: Assume Python 3.8+ unless specified otherwise.
*   **PEP 8**: Follow PEP 8 style guidelines for Python code. Use a linter/formatter if possible (e.g., Black, Flake8).
*   **Type Hinting**: Use type hints where practical to improve code readability and maintainability.
*   **Logging**: Utilize the `DataLogger` (`core/data_logger.py`) for logging application events, warnings, errors, and debug information. Avoid using `print()` statements for persistent logging in the core application logic. `print()` is acceptable in `if __name__ == '__main__':` test blocks.

## Configuration

*   **`config.py`**: Centralized configuration is managed in `config.py`.
    *   When adding new configurable parameters, add them to this file with clear comments.
    *   Ensure default values are sensible.
*   **`.env` for Secrets**: API keys and other secrets should **not** be hardcoded. Load them from an `.env` file using `python-dotenv`. `core/lmm_interface.py` provides an example. Add new secret keys to a template `.env.example` if one is created.

## Testing

*   **Test Framework**: The project uses `pytest` for testing.
*   **Running Tests**: Run `pytest` from the project root to execute the test suite.
*   **New Features**: All new features and significant changes must be accompanied by tests in the `tests/` directory.
    *   Aim for good test coverage.
    *   Write unit tests for individual components and integration tests for interactions between them.
*   **Legacy Tests**: Some modules may still contain `if __name__ == '__main__':` blocks for quick ad-hoc testing, but these should be migrated to `pytest` where appropriate.

## LMM Integration (`core/lmm_interface.py`)

*   This is a key area for development.
*   The current interface is a placeholder.
*   When implementing actual LMM calls:
    *   Ensure API keys are handled securely (via `.env`).
    *   Implement robust error handling for API calls (network issues, API errors, etc.).
    *   Structure prompts clearly.
    *   Process LMM responses carefully.

## Sensor Data Handling

*   **`sensors/`**: Modules for video and audio data acquisition.
*   Ensure sensor initialization and data retrieval are resilient to errors (e.g., device not found, read errors).
*   Implement retry logic where appropriate (as seen in current sensor classes).

## System Tray (`core/system_tray.py`)

*   The system tray provides the primary UI.
*   Changes to application state or available actions should be reflected in the tray icon or menu if appropriate.

## Committing Changes

*   (This is more for human users, but good for you to know the desired standard)
*   Use clear and descriptive commit messages.
*   Follow conventional commit message formats if adopted by the project (e.g., `feat: add new feature X`, `fix: resolve bug Y`).

## Asking for Clarification

*   If a task is ambiguous or you foresee significant architectural changes, it's better to ask for clarification (e.g., using `request_user_input`) than to make assumptions.

---
*This document will evolve as the project grows. Always check for the latest version.*
