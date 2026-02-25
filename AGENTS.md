# AGENTS.md - CatanPro Development Guide

## Project Overview
This is a Catan board game web application using:
- **Backend**: Python with Flask and Flask-SocketIO for server/game logic
- **Frontend**: Vanilla JavaScript and HTML (no React/framework)
- **Architecture**: Modular component-based design

---

## Build, Lint, and Test Commands

### Python (Backend)

```bash
# Install dependencies
pip install -r server/requirements.txt

# Run the Flask server
python server/app.py

# Run with Flask debug mode
FLASK_DEBUG=1 python server/app.py

# Run a single test
pytest server/tests/test_file.py::test_function_name -v
pytest server/tests/ -k "test_name_pattern" -v

# Run all tests
pytest server/tests/

# Lint Python code
flake8 server/
pylint server/

# Type checking (if using mypy)
mypy server/
```

### JavaScript (Frontend)
No build system - vanilla JS served directly. For linting:
```bash
# Install ESLint (if configured)
npm install eslint --save-dev
npx eslint server/static/js/
```

---

## Code Style Guidelines

### General Principles
- Keep functions small and focused (single responsibility)
- Write meaningful variable and function names
- Comment complex logic, not obvious code
- Maximum line length: 100 characters
- Use 2 spaces for indentation (no tabs)

### Python Style

**Imports**
- Standard library first, then third-party, then local
- Group by: stdlib → external → project
- Use absolute imports: `from server.game.models import Player`
- Avoid `from module import *`

**Naming Conventions**
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

**Types**
- Use type hints for function signatures
- Prefer explicit types over `Any`
- Use `Optional[X]` instead of `X | None`

**Error Handling**
- Use specific exceptions, not bare `except:`
- Log errors before re-raising
- Never expose stack traces to users
- Use context managers for resource cleanup

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

**General**
- Use ES6+ syntax
- Keep scripts modular in separate files
- Avoid global variables - use modules with explicit exports

**Naming Conventions**
- Variables/functions: `camelCase`
- Classes/Constructors: `PascalCase`
- Constants: `UPPER_SNAKE_CASE` or `camelCase` for config objects

**Error Handling**
- Always handle async errors with try/catch
- Display user-friendly error messages in UI
- Log detailed errors server-side

**Example**:
```javascript
const PLAYER_MAX_POINTS = 10;

class Player {
  constructor(id, name) {
    this.id = id;
    this.name = name;
    this.points = 0;
  }

  addPoints(points) {
    this.points += points;
  }
}

function calculateScore(player) {
  return player.points;
}
```

---

## Project Structure

```
CatanPro/
├── server/                 # Python backend
│   ├── app.py            # Flask + SocketIO entry point
│   ├── requirements.txt  # Python dependencies
│   ├── static/           # Static assets
│   │   ├── css/         # Stylesheets
│   │   └── js/          # JavaScript files
│   ├── templates/       # HTML templates
│   ├── data/            # Game data
│   ├── game/            # Game logic modules (create as needed)
│   ├── sockets/         # Socket handlers (create as needed)
│   └── tests/           # Python tests
├── build.md             # Original project specification
├── shell.nix            # Nix environment (optional)
└── AGENTS.md            # This file
```

---

## Git Workflow

1. Create feature branch: `git checkout -b feature/feature-name`
2. Make changes and commit with descriptive messages
3. Push and create PR when ready
4. Use conventional commits: `feat:`, `fix:`, `refactor:`, `test:`

---

## Testing Guidelines

### Python
- Use `pytest` as test framework
- Place tests in `server/tests/` directory
- Follow naming: `test_<module>_<function>.py`
- Use fixtures for common test setup
- Mock external dependencies

### JavaScript
- Manual testing in browser (no test framework currently)
- Add tests if Jest/Vitest is later configured

---

## Socket Events

When modifying socket handlers, document event names:
- `connect` - Client connects
- `disconnect` - Client disconnects
- Custom events for game actions (document as implemented)

---

## Additional Notes

- This is a Flask + SocketIO project (not React)
- Frontend uses vanilla JavaScript in `server/static/js/`
- HTML templates in `server/templates/`
- Run linting before committing
- Ensure all tests pass before submitting PRs
