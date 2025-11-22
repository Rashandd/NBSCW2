# Contributing to Rashigo

First off, thank you for considering contributing to Rashigo! It's people like you that make Rashigo such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps which reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed after following the steps**
* **Explain which behavior you expected to see instead and why**
* **Include screenshots and animated GIFs** if possible
* **Include your environment details** (OS, Python version, Django version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title**
* **Provide a step-by-step description of the suggested enhancement**
* **Provide specific examples to demonstrate the steps**
* **Describe the current behavior** and **explain which behavior you expected to see instead**
* **Explain why this enhancement would be useful**

### Pull Requests

* Fill in the required template
* Do not include issue numbers in the PR title
* Follow the Python/Django style guides
* Include thoughtfully-worded, well-structured tests
* Document new code
* End all files with a newline

## Development Process

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/NBSCW2.git
   cd NBSCW2
   ```

3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```bash
   cd python_version
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

5. **Set up the database**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Making Changes

1. **Make your changes** in your feature branch

2. **Follow the coding standards**:
   - PEP 8 for Python code
   - Use type hints
   - Write docstrings for all public methods
   - Keep functions focused and small

3. **Write or update tests**:
   ```bash
   python manage.py test
   ```

4. **Run linters**:
   ```bash
   flake8 .
   pylint main/
   black --check .
   mypy .
   ```

5. **Update documentation** if needed

6. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

   Use conventional commit messages:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `style:` for formatting changes
   - `refactor:` for code refactoring
   - `test:` for adding tests
   - `chore:` for maintenance tasks

### Submitting Your Changes

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Submit a pull request** through GitHub

3. **Wait for review** - maintainers will review your PR and may request changes

## Style Guides

### Python Style Guide

* Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
* Use 4 spaces for indentation (no tabs)
* Maximum line length of 100 characters
* Use meaningful variable names
* Add type hints to function signatures
* Write docstrings for all public modules, functions, classes, and methods

Example:

```python
def calculate_win_rate(wins: int, total_games: int) -> float:
    """
    Calculate win rate percentage.
    
    Args:
        wins: Number of wins
        total_games: Total number of games played
    
    Returns:
        Win rate as a percentage (0-100)
    
    Raises:
        ValueError: If total_games is negative
    """
    if total_games < 0:
        raise ValueError("Total games cannot be negative")
    
    if total_games == 0:
        return 0.0
    
    return round((wins / total_games) * 100, 2)
```

### Django Style Guide

* Use class-based views when appropriate
* Keep views thin, move logic to services
* Use Django's built-in features when possible
* Follow Django's naming conventions
* Use Django's translation system for user-facing strings

### Git Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

### JavaScript Style Guide

* Use ES6+ features
* Use 2 spaces for indentation
* Use semicolons
* Use meaningful variable names
* Add JSDoc comments for functions

## Testing

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test main

# Run specific test class
python manage.py test main.tests.TestWorkflow

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

### Writing Tests

* Write tests for all new features
* Write tests for bug fixes
* Aim for high code coverage (>80%)
* Use Django's TestCase for database tests
* Use mocks for external services

Example:

```python
from django.test import TestCase
from main.models import AIAgent
from main.services.ai_agent_service import AIAgentService


class AIAgentServiceTest(TestCase):
    def setUp(self):
        self.agent = AIAgentService.create_agent(
            name="Test Agent",
            agent_type="assistant"
        )
    
    def test_create_agent(self):
        """Test agent creation"""
        self.assertEqual(self.agent.name, "Test Agent")
        self.assertEqual(self.agent.agent_type, "assistant")
        self.assertEqual(self.agent.status, "inactive")
    
    def test_activate_agent(self):
        """Test agent activation"""
        AIAgentService.activate_agent(self.agent)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.status, "active")
```

## Documentation

### Code Documentation

* Write docstrings for all public modules, functions, classes, and methods
* Use Google-style docstrings
* Include examples in docstrings when helpful
* Keep documentation up-to-date with code changes

### Project Documentation

* Update README.md for user-facing changes
* Update relevant documentation files in the repository
* Add examples for new features
* Include migration guides for breaking changes

## Community

### Getting Help

* Check the [documentation](README.md)
* Search [existing issues](https://github.com/yourusername/NBSCW2/issues)
* Ask in [GitHub Discussions](https://github.com/yourusername/NBSCW2/discussions)

### Staying Informed

* Watch the repository for updates
* Follow the project on social media
* Join our community chat (if available)

## Recognition

Contributors will be recognized in:
* The project README
* Release notes
* The project website (if applicable)

Thank you for contributing to Rashigo! 🎉
