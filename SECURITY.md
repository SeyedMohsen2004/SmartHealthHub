# Security Policy

## Supported releases

Security fixes are applied to the latest released minor version on `main`.
Older portfolio releases remain available as history but are not maintained as
parallel security branches.

## Reporting a vulnerability

Please do not publish exploitable details in a GitHub issue, discussion, or
pull request. GitHub private vulnerability reporting is not currently enabled,
and this repository does not publish a private security address. Open a minimal
issue that asks the maintainer to arrange a private reporting channel, without
including the vulnerability, affected data, proof of concept, or secrets.

Useful reports identify the affected version, impact, prerequisites, and a
minimal reproducible case once a private channel is available. Reports about
authentication, authorization, cross-user data access, token handling,
appointment integrity, dependency or container vulnerabilities, and unsafe
production defaults are in scope.

The maintainer will acknowledge and assess reports as availability permits.
No response-time, remediation-time, disclosure, reward, or bug-bounty promise
is made.

## Project boundary

SmartHealthHub is a portfolio and reference deployment architecture. It is not
a hosted healthcare service and makes no compliance certification. Never test
against a system or data set without the operator's explicit authorization.
