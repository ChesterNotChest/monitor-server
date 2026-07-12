# CI Test Runtime

## Purpose

Define the runtime dependencies required for the Jenkins/Docker test stage to
execute the Server test suite consistently with local development.

## Requirements

### Requirement: CI image supports async pytest tests

The Docker test image SHALL install the pytest plugin required to execute
`async def` tests marked with `pytest.mark.asyncio`.

#### Scenario: WSS async integration tests run in Jenkins

- **WHEN** Jenkins runs `python -m pytest src/tests/ --tb=short` inside the Docker image
- **THEN** tests marked with `pytest.mark.asyncio` execute instead of failing during collection
- **AND** the dependency set includes `pytest-asyncio`

### Requirement: Python dependency declarations stay aligned

Python test runtime dependencies SHALL be declared in both `requirements.txt`
and `environment.yml` when they are needed by CI and local conda development.

#### Scenario: Fresh Docker image and conda environment both run tests

- **WHEN** dependencies are installed from `requirements.txt` or `environment.yml`
- **THEN** the Server test suite has the same pytest async plugin available
