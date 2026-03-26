# Agent Guidelines for terminal-todo

## Project Overview
A terminal-based todo application built with [Textual](https://textual.textualize.io/). Single Python package in `terminal_todo/` with app logic in `app.py` and styles in `todo.tcss`.

## Build & Installation Commands

```bash
# Install in development/editable mode
pip install -e .

# Install dependencies only
pip install -r requirements.txt

# Run the application
todo

# Or run directly
python -m terminal_todo.app
```

## Testing
**Note**: This project currently has no test suite. When adding tests:
- Use `pytest` as the testing framework
- Create a `tests/` directory at the project root
- Test files should follow `test_*.py` naming convention
- Run tests with `pytest` or `python -m pytest`
- Run a single test: `pytest tests/test_file.py::test_function_name`

## Code Style Guidelines

### Python Version
- Target Python 3.8+ (specified in `setup.py`)

### Type Hints
- Use type hints for all function parameters and return types
- Include return type `-> None` explicitly for void functions
- Example: `def action_add(self) -> None:`

### Docstrings
- Add docstrings to all public classes and methods
- Use triple quotes with description on first line
- Example:
  ```python
  def _load_data(self) -> None:
      """Load tasks and tabs from persistent storage."""
  ```

### Naming Conventions
- **Classes**: `PascalCase` (e.g., `TodoApp`, `TaskRadioButton`)
- **Methods/Functions**: `snake_case` (e.g., `action_add`, `_save_data`)
- **Constants**: `SCREAMING_SNAKE_CASE` (e.g., `DATA_DIR`, `DATA_FILE`)
- **Private methods**: Prefix with `_` (e.g., `_load_data`)

### Import Organization
1. Standard library imports (`json`, `pathlib`)
2. Third-party imports (`from textual...`)
3. Local application imports

Keep imports sorted alphabetically within each group:
```python
import json
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Input, ListView
```

### Textual Framework Conventions
- Use `BINDINGS` class attribute for keyboard shortcuts
- Define custom `Message` subclasses for widget communication
- Use decorators (`@on`, `@property`) appropriately
- Use `CSS_PATH` property to specify stylesheet location
- Actions are prefixed with `action_` (e.g., `action_add`)

### Error Handling
- Use broad exception catching only when necessary
- Example from codebase:
  ```python
  try:
      with open(data_path, "w", encoding="utf-8") as f:
          json.dump(data, f, ensure_ascii=False, indent=2)
  except IOError:
      pass
  ```

### File Structure
```
terminal_todo/
├── __init__.py      # Empty package init
├── app.py           # Main application code
└── todo.tcss        # Textual CSS styles
```

### CSS (Textual)
- Store styles in `.tcss` files alongside Python modules
- Use CSS variables (`$surface`, `$accent`, etc.) for theming
- Target widgets by ID (`#id`) or class (`.class`)

### Data Persistence
- Store data in `~/.terminal-todo/data.json`
- Use JSON for serialization
- Handle missing/corrupted data gracefully with try/except

### Development Workflow
1. Make changes to `terminal_todo/app.py` or CSS files
2. Run `pip install -e .` to reinstall in dev mode
3. Test changes with `todo` or `python -m terminal_todo.app`
4. Data file: `~/.terminal-todo/data.json`

### Key Classes
- `TodoApp`: Main application class inheriting from `textual.app.App`
- `TaskRadioButton`: Custom widget extending `RadioButton` with delete functionality

### Message Handling
Textual uses a message-based communication system. Use `@on` decorator for message handlers:
```python
@on(Input.Submitted, "#task_input")
def add_todo_item(self) -> None:
    ...
```
