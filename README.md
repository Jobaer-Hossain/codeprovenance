# CodeProvenance

> **Automated Codebase Evolution & Architecture Drift Detector**  
> Static AST layer compliance, boundary enforcement, circular dependency detection, and prioritized micro-refactorings.

CodeProvenance parses your codebase into an Abstract Syntax Tree (AST), maps files to defined architectural layers (Clean Architecture, Hexagonal, or Multi-Tier), and audits dependency directions. It prevents architectural erosion by flagging layer inversions, circular couplings, and excessive cyclomatic complexity before code is merged.

---

## Key Features

1. **AST Layer Boundary Enforcement**: Ensures presentation/API controllers do not directly import raw database drivers (`sqlite3`, `psycopg2`, `prisma`, `sqlalchemy`), enforcing clean separation of concerns.
2. **Circular Coupling Detection**: Builds an internal dependency graph and runs cycle detection to isolate mutually dependent modules.
3. **McCabe Cyclomatic Complexity Analysis**: Flags methods with branching complexity $> 12$ and file length $> 400$ LOC.
4. **Architectural Health Score**: Computes an objective compliance percentage ($0 - 100\%$) for CI/CD gates.
5. **Interactive Web Dashboard & CLI**: Real-time terminal inspection and a modern, high-contrast web dashboard with Markdown audit export.

---

## Quickstart

### Installation
```bash
git clone https://github.com/Jobaer-Hossain/codeprovenance.git
cd codeprovenance

pip install -r requirements.txt
```

### CLI Scanning
```bash
# Scan current repository
python -m codeprovenance.cli scan

# View defined architectural layers
python -m codeprovenance.cli layers
```

### Web Dashboard
```bash
python run.py --port 8001
```
Open **`http://localhost:8001`** in your browser to inspect visual layer distributions and refactoring proposals.

---

## Architecture Blueprint

```json
{
  "layers": [
    {
      "name": "presentation",
      "allowed_dependencies": ["services", "domain", "core"]
    },
    {
      "name": "services",
      "allowed_dependencies": ["data", "models", "core"]
    },
    {
      "name": "data",
      "allowed_dependencies": ["core"]
    }
  ],
  "max_cyclomatic_complexity": 12
}
```

---

## Automated Tests
```bash
python -m unittest tests.test_codeprovenance
```

---

## License
MIT License. Free for open-source and commercial use.
