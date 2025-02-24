
## Code Quality

### Tools and Standards

- **Black**: Code formatter that ensures consistent Python code style
- **Flake8**: Linter that checks for Python code style and errors
- **isort**: Sorts and organizes Python imports

### Local Development Setup

1. **Pre-commit Hooks**

   ```bash
   # Install pre-commit hooks (automatically runs on every commit)
   pre-commit install
   ```

2. **Manual Code Formatting**

   You can format your code manually by running
   ```bash
   pre-commit run --all-files
   ```

   If you have issues with formatting, you can run the individual tools separately:
   ```bash
   # Format code with Black
   black .
   
   # Sort imports with isort
   isort .
   
   # Run Flake8 linting
   flake8 .
   ```