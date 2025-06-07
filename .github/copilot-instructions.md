# Overview
Survaize is a tool that automatically converts "paper" questionnaires into interactive survey apps. 
It uses a combination of OCR and generative AI vision models to understand the structure of survey questionnaires in order to 
generate survey apps compatible with data collection platforms like CSPro.

# Coding standards

1. Use type annotations - all function parameter and return types must be explicit
2. Use descriptive function and variable names
3. Each function should have a clear single responsibility
4. Include docstrings for public functions and classes
5. Prefer immutable data structures where possible, use @dataclass for simple data containers or Pydantic models for more complex validation
6. Use functional programming principles (pure functions, minimal side effects)
7. Use the Python logging library for logging e.g. `logger = logging.getLogger(__name__)`
8. Only add comments to complex hard to understand code, don't comment every line
9. Prefix private methods in classes with _
10. Always place imports at the top of the file

# File layout
All source code should be in one of the following directories or a subdirectory thereof.
- src: The main source code directory for Survaize.
- test: Contains unit tests for the Survaize application.
- evals: Contains evaluation scripts and data for testing the Survaize application.

Code outside of these directories will not execute correctly.

The src/survaize directory contains the main application code, organized as follows:
- interpreter: Main logic for interpreting questionnaires using AI models.
- readers: Reading different file formats (PDF, JSON).
- writers: Writing questionnaires to different formats (CSPro, JSON).
- models: Models for questionnaires.
- cspro: Models and serializers for CSPro files (dictionary, forms, question text).
- config: Configuration management including API keys and model settings.
- web/backend: FastAPI backend for serving the application.
- web/frontend: React frontend for the application.

# Running/testing
Use uv to run the application and tests to ensure the correct virtual environment.

To run the application:
```bash
uv run survaize
```

To run tests:
```bash
uv run pytest
```

To run an arbitrary Python script in the virtual env:
```bash
uv run python path/to/script.py
```

For linting:
```bash
uv run ruff check
```

Typechecking:
```bash
uv run basedpyright
```

To add a new dependency:
```bash
uv add package_name
```

# Architecture

### Core Components

1. **Models**
   - `Questionnaire` intermediate format for survey questionnaire (structured JSON)

2. **Document Readers**
   - `Reader` protocol, reads file and produces a `Questionnaire` 
   - `PDFReader` reads a PDF and generates a `Questionnaire`  (uses `AIQuestionnaireInterpreter` to find questionnaire structure)
   - `JSONReader` reads a `Questionnaire` from a JSON file

3. **Questionnaire Interpretation**
   - `AIQuestionnaireInterpreter` that uses LLMs to convert a `ScannedQuestionnaire` into a structured `Questionnaire` object

4. **Document Writers**
   - `Writer` protocol, takes a `Questionnaire` and writes it to disk
   - Writers for each output format (`CSProWriter`, `JSONWriter`)

5. **Converter**
   - Orchestrates conversion: input file → reader → writer
