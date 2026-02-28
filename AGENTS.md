# AGENTS.md - CatanPro Development Guide

## Project Overview
- **Backend**: Python with Flask and Flask-SocketIO
- **Frontend**: Vanilla JavaScript and HTML (no framework)
- **Architecture**: Modular component-based design

---

## Build, Lint, and Test Commands

### Python (Backend)
```bash
# Install dependencies
pip install -r server/requirements.txt

# Run the Flask server
python server/app.py

# Run with debug mode
FLASK_DEBUG=1 python server/app.py

# Run a single test
pytest server/tests/test_file.py::test_function_name -v
pytest server/tests/ -k "test_name_pattern" -v

# Run all tests
pytest server/tests/

# Lint Python code
flake8 server/
pylint server/
```

### JavaScript (Frontend)
No build system - vanilla JS served directly. For linting:
```bash
npm install eslint --save-dev
npx eslint server/static/js/
```

---

## Code Style Guidelines

### General Principles
- Keep functions small and focused (single responsibility)
- Maximum line length: 100 characters
- Use 2 spaces for indentation (no tabs)
- Comment complex logic, not obvious code

### Python Style

**Imports** (order: stdlib → external → project):
```python
import json
import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from game.game import Game
```
- Use absolute imports: `from server.game.models import Player`
- Avoid `from module import *`

**Naming Conventions**:
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

**Types**:
- Use type hints for function signatures
- Prefer explicit types over `Any`
- Use `Optional[X]` instead of `X | None`

**Error Handling**:
- Use specific exceptions, not bare `except:`
- Log errors before re-raising
- Never expose stack traces to users

**Example**:
```python
from typing import Optional
import logging
from flask import Flask

logger = logging.getLogger(__name__)

class GameError(Exception):
    pass

def create_app(config: dict) -> Flask:
    app = Flask(__name__)
    app.config.update(config)
    return app
```

### JavaScript Style

**General**: Use ES6+ syntax, keep scripts modular, avoid global variables.

**Naming**:
- Variables/functions: `camelCase`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`

**Error Handling**: Handle async errors with try/catch, display user-friendly messages.

---

## Project Structure
```
CatanPro/
├── server/
│   ├── app.py              # Flask + SocketIO entry point
│   ├── requirements.txt    # Python dependencies
│   ├── static/css/         # Stylesheets
│   ├── static/js/          # JavaScript files
│   ├── templates/          # HTML templates
│   ├── data/               # Game data (JSON)
│   ├── game/               # Game logic modules
│   ├── sockets/            # Socket handlers
│   └── tests/              # Python tests (pytest)
├── build.md                # Project specification
└── AGENTS.md               # This file
```

---

## Testing Guidelines
- Use `pytest` as test framework
- Place tests in `server/tests/` directory
- Follow naming: `test_<module>_<function>.py`
- Use fixtures for common test setup
- Mock external dependencies

---

## Socket Events
Document custom events when implementing:
- `connect` / `disconnect` - Client connects/disconnects
- `join` - Player joins game
- `start_game` - Start new game
- `next_turn` - Advance turn
- `place_settlement` / `place_road` - Place game pieces
- `set_color` - Set player color
- `error` - Error response

---

## Git Workflow
1. Create feature branch: `git checkout -b feature/feature-name`
2. Make changes and commit with descriptive messages
3. Use conventional commits: `feat:`, `fix:`, `refactor:`, `test:`

---

## Additional Notes
- Run linting before committing
- Ensure all tests pass before submitting PRs
- Frontend: vanilla JS in `server/static/js/`
- Backend: Flask + SocketIO in `server/`
