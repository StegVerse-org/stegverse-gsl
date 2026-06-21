# StegVerse GSL

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)

Release: v1.0.0

Governance Specification Language (GSL) for StegVerse architecture manifests.

GSL defines and validates the structure of ecosystem repositories, component interactions, manifest contracts, and governance-facing repository metadata.

---

## What it does

- architecture manifest definitions;
- JSON schema validation for repository structure;
- governance rule descriptions for component interaction;
- discovery-script support for generating architecture documentation;
- validation of repositories against canonical manifests.

---

## Install

```bash
pip install stegverse-gsl
```

---

## Quick start

```python
from gsl import load_manifest, validate_repo

manifest = load_manifest("stegverse.architecture.json")
result = validate_repo("StegVerse-org/StegVerse-SDK", manifest)

print(result["valid"])
```

---

## Integration

| System | Role |
|---|---|
| Architecture Guard | CI validation via workflow guard. |
| `StegVerse-org/demo_ingest_engine` | Manifest-aware ingestion. |
| `StegVerse-org/StegVerse-SDK` | SDK structure and route manifest validation. |
| `StegVerse-org/discovery` | Repository discovery and manifest indexing. |

---

## Boundary rule

GSL validates declared structure. It does not by itself create execution authority, admission authority, endorsement, external compatibility recognition, provenance recognition, collaboration, or validation.

---

## Links

- Repository: https://github.com/StegVerse-org/stegverse-gsl
- Issues: https://github.com/StegVerse-org/stegverse-gsl/issues
