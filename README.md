# StegVerse GSL

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/github/license/StegVerse-org/stegverse-gsl)

Release: v1.0.0

Governance Specification Language (GSL) for StegVerse architecture manifests. Defines, validates, and enforces the structure of ecosystem repositories.

## What It Does

- **Architecture manifests** — JSON schema for repo structure validation
- **Governance rules** — Policy definitions for component interaction
- **Discovery scripts** — Auto-generate architecture documentation
- **Validation engine** — Verify repos against canonical manifests

## Install

```bash
pip install stegverse-gsl
```

## Quick Start

```python
from gsl import load_manifest, validate_repo

# Load canonical architecture
manifest = load_manifest("stegverse.architecture.json")

# Validate a repo
result = validate_repo("StegVerse-org/StegVerse-SDK", manifest)
print(result["valid"])  # True | False
```

## Integration

| System | Role |
|--------|------|
| Architecture Guard | CI validation via `architecture-guard.yml` |
| demo_ingest_engine | Manifest-aware ingestion |
| StegVerse-SDK | SDK structure validation |
| StegDB | Architecture state tracking |

## Links

- Repository: https://github.com/StegVerse-org/stegverse-gsl
- Issues: https://github.com/StegVerse-org/stegverse-gsl/issues

---

**StegVerse: Execution is not assumed. Execution is admitted.**
