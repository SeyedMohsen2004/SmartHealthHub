# Changelog

Notable project changes are recorded here in a concise, human-readable format.

## [1.1.0] - 2026-08-12

### Added

- Production-oriented non-root Gunicorn, Celery worker, Celery Beat, Redis, and
  one-shot release topology.
- Separate hash-locked runtime/development dependencies, Python advisory gates,
  and a CycloneDX runtime SBOM artifact.
- Explicit appointment lifecycle, cancelled-slot reuse, concurrency-safe
  booking/rescheduling, and database-enforced active-slot uniqueness.
- Refresh-token rotation, blacklist-backed revocation/logout, and bounded DRF
  global/auth-endpoint throttling.
- Durable, database-reconciled and idempotent in-app appointment reminders.
- Request correlation IDs and privacy-bounded completion logging.
- Digest-pinned base/service images and checksum-verified Trivy container gates.
- Focused architecture, security, operations, and domain documentation.

### Changed

- The OpenAPI release metadata now reports `1.1.0`; the public API namespace
  remains `/api/v1/`.

## [1.0.0] - 2026-06-09

- Initial stable release with JWT accounts, providers, appointments,
  notifications, PostgreSQL, Docker, OpenAPI, CI, and 38 automated tests.

[1.1.0]: https://github.com/SeyedMohsen2004/SmartHealthHub/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/SeyedMohsen2004/SmartHealthHub/releases/tag/v1.0.0
