# Authentication and throttling

SmartHealthHub uses SimpleJWT bearer tokens and Django REST Framework (DRF)
throttling. This document describes the current security contract and its
operational limits.

## Access and refresh tokens

Access tokens authenticate API requests through the `Authorization: Bearer`
header. They are stateless and expire after 15 minutes by default. Refresh
tokens are longer-lived credentials, expiring after 7 days by default, and are
used only to obtain a new token pair.

`POST /api/v1/auth/register/` and `POST /api/v1/auth/login/` return an access
token and refresh token without changing the existing response key names.

## Refresh rotation and revocation

`POST /api/v1/auth/refresh/` accepts a refresh token and returns both a new
access token and a new refresh token. The submitted refresh token is
blacklisted as part of the successful rotation and cannot be reused. The newly
returned refresh token can be rotated in the same way.

SimpleJWT's `OutstandingToken` and `BlacklistedToken` tables provide this
infrastructure. They are internal implementation details; API clients should
store token strings, not database identifiers.

### Logout

`POST /api/v1/auth/logout/` accepts:

```json
{
  "refresh": "<refresh-token>"
}
```

A valid token is revoked with HTTP 204 and an empty response body. The endpoint
does not require an access token and revokes only the supplied refresh token,
not every session belonging to the user. Invalid, expired, malformed, or
already-revoked tokens return HTTP 400 with the stable validation message:

> Refresh token is invalid, expired, or already revoked.

Revoking a refresh token does not invalidate access tokens already issued from
that session. Access tokens remain stateless and usable until their normal
short expiration. SmartHealthHub does not maintain an access-token deny-list.

## Expired-token maintenance

Outstanding and blacklisted token records accumulate until expired rows are
removed. SimpleJWT provides the official command:

```bash
python manage.py flushexpiredtokens
```

This command is not run during application startup, in CI against production,
or by a background worker. Scheduling it belongs to the later production
operations/security phase once a real host and scheduler contract exist.

## API throttling

DRF's built-in anonymous, authenticated-user, and scoped throttles apply the
following defaults:

| Policy | Default | Environment variable |
| --- | ---: | --- |
| Anonymous API traffic | `100/hour` | `DRF_ANON_THROTTLE_RATE` |
| Authenticated API traffic | `1000/hour` | `DRF_USER_THROTTLE_RATE` |
| Registration | `5/hour` | `DRF_AUTH_REGISTER_THROTTLE_RATE` |
| Login | `10/min` | `DRF_AUTH_LOGIN_THROTTLE_RATE` |
| Refresh | `30/min` | `DRF_AUTH_REFRESH_THROTTLE_RATE` |
| Logout | `30/min` | `DRF_AUTH_LOGOUT_THROTTLE_RATE` |

The four authentication endpoints have independent scoped counters in addition
to the applicable global anonymous policy. Both successful and failed requests
consume an endpoint's throttle budget because throttling occurs before
credential or token validation. Requests over a limit use DRF's standard HTTP
429 response and retain its `Retry-After` header when available.

The health/readiness endpoint is explicitly unthrottled so rate limiting cannot
make container probes unhealthy.

### Client IP and trusted proxies

`DRF_NUM_PROXIES` defaults to `0`. At this safe default, anonymous and scoped
IP identification uses the direct connection address and does not trust an
arbitrary `X-Forwarded-For` chain. When deployed behind a known reverse-proxy
topology, operators must set this value to the exact number of trusted proxies.
Changing it changes which client address DRF uses for rate-limit counters. It
does not alter the separate forwarded-HTTPS trust setting.

### Security limits

These throttles provide bounded, best-effort application-level abuse control.
They are not complete brute-force protection, DDoS protection, or an exact
concurrency guarantee. The current cache/backend topology can make counters
approximate across multiple worker processes. Redis and distributed rate-limit
infrastructure are intentionally deferred until a later architecture phase.
