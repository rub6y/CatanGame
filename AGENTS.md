# AGENTS.md - CatanPro Development Guide

## Project Overview
This is a Catan board game web application using:
- **Backend**: Python with Flask and sockets for server/game logic
- **Frontend**: JavaScript and HTML
- **Architecture**: Modular component-based design

---

## Build, Lint, and Test Commands

### Python (Backend)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask server
python app.py

# Run with Flask debug mode
FLASK_DEBUG=1 python app.py

# Run a single test
pytest tests/test_file.py::test_function_name -v
pytest tests/test_file.py -k "test_name_pattern" -v

# Run all tests
pytest

# Lint Python code
flake8 .
pylint src/

# Type checking (if using mypy)
mypy src/
```

### JavaScript (Frontend)

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run tests
npm test
npm test -- --testPathPattern="test_name"
npm test -- --testNamePattern="test_name"

# Lint
npm run lint
npm run lint -- --fix

# Format code
npm run format
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
- Use absolute imports: `from app.models import User`
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

**Imports**
- Use ES6 modules: `import { x } from './module'`
- Prefer default exports for single exports
- Group: React → external → local

**Naming Conventions**
- Variables/functions: `camelCase`
- Components/Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE` or `camelCase` for config objects

**Types**
- Use TypeScript when possible
- Define interfaces for data structures
- Avoid `any` type

**Error Handling**
- Always handle async errors with try/catch
- Use error boundaries in React
- Display user-friendly error messages
- Log detailed errors server-side

**Example**:
```typescript
interface Player {
  id: string;
  name: string;
  points: number;
}

const PLAYER_MAX_POINTS = 10;

function calculateScore(player: Player): number {
  return player.points;
}
```

---

## Project Structure

```
CatanPro/
├── server/                 # Python backend
│   ├── app.py             # Flask entry point
│   ├── game/              # Game logic modules
│   │   ├── __init__.py
│   │   ├── board.py
│   │   ├── player.py
│   │   └── ...
│   ├── sockets/           # Socket handlers
│   └── tests/             # Python tests
├── client/                # Frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom hooks
│   │   ├── services/    # API clients
│   │   └── ...
│   ├── public/
│   └── tests/            # JS tests
└── requirements.txt       # Python dependencies
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
- Place tests in `tests/` directory
- Follow naming: `test_<module>_<function>.py`
- Use fixtures for common test setup
- Mock external dependencies

### JavaScript
- Use Jest or Vitest
- Place tests alongside source files (`Component.test.tsx`) or in `__tests__/`
- Use `@testing-library/react` for component tests
- Write integration tests for API calls

---

## Additional Notes

- Check `Documents/chatProject` for Python project structure reference (as mentioned in build.md)
- Run linting before committing
- Ensure all tests pass before submitting PRs
