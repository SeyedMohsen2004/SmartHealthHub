# Python dependencies

SmartHealthHub keeps human-reviewed direct requirements separate from generated,
hash-locked installation files:

| File | Responsibility |
| --- | --- |
| `requirements.in` | Direct packages required by the production application |
| `requirements-dev.in` | Runtime source set plus test, quality, audit, and lock tooling |
| `requirements.txt` | Generated, pinned, hash-locked production dependency graph |
| `requirements-dev.txt` | Generated, pinned, hash-locked development and CI graph |

The production Docker target installs only `requirements.txt`. The development
Docker target and CI install `requirements-dev.txt`. Do not edit either generated
`.txt` lock by hand.

## Deterministic installation

Use Python 3.12, matching the Docker image and CI:

```bash
python -m pip install --require-hashes --requirement requirements.txt
```

For development and CI:

```bash
python -m pip install --require-hashes --requirement requirements-dev.txt
python -m pip check
```

## Regenerating locks

Lock generation is standardized on pip-tools 7.6.0. Install that exact version
in a disposable Python 3.12 environment, then compile both graphs:

```bash
python -m pip install pip-tools==7.6.0
CUSTOM_COMPILE_COMMAND="python -m piptools compile --generate-hashes --allow-unsafe --strip-extras --output-file=requirements.txt requirements.in" \
  python -m piptools compile --upgrade --generate-hashes --allow-unsafe \
    --strip-extras --resolver=backtracking \
    --output-file=requirements.txt requirements.in
CUSTOM_COMPILE_COMMAND="python -m piptools compile --generate-hashes --allow-unsafe --strip-extras --output-file=requirements-dev.txt requirements-dev.in" \
  python -m piptools compile --upgrade --generate-hashes --allow-unsafe \
    --strip-extras --resolver=backtracking \
    --output-file=requirements-dev.txt requirements-dev.in
```

CI recompiles without `--upgrade` and fails on a lock diff. This detects
source/lock drift without making an unrelated package release fail an otherwise
unchanged commit.

Review lock diffs before committing. Broad or forced upgrades can conceal a
compatibility change; update direct constraints only for an understood security,
support, or compatibility reason.

## Advisory audits and SBOM

The development lock includes pip-audit 2.10.1. Audit the two graphs separately:

```bash
python -m pip_audit --requirement requirements.txt --disable-pip
python -m pip_audit --requirement requirements-dev.txt --disable-pip
```

CI also emits a CycloneDX JSON SBOM artifact for the runtime graph. It is an
inventory aid, not proof that the software is vulnerability-free. Audit results
describe advisories known to the tool's data sources at scan time and still need
compatibility-aware review rather than automatic forced upgrades.
