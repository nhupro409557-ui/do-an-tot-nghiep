## Admin Auth Notes

This note tracks the current admin authentication design and the rationale behind recent changes so later edits have a stable reference point.

### Current flow

1. Admin enters email and password at `/admin/login`.
2. Backend validates the account, checks admin permissions, and applies lockout rules for repeated failures.
3. Backend requires MFA for all admin-capable accounts.
4. MFA verification issues the normal access token plus refresh-token cookie.
5. Every admin API still enforces permission checks on the backend, regardless of what the frontend renders.

### Recent hardening

- Silent refresh bootstrap is now explicit on the frontend so route guards wait for auth restoration before redirecting.
- Access-token fingerprinting is now based on `User-Agent` only instead of `User-Agent + IP prefix` to avoid false logouts on mobile and carrier networks.
- Admin MFA temp tokens now carry a `jti` and are marked as used after successful verification to reduce replay risk within the remaining token lifetime.
- Frontend admin visibility must survive a server-backed refresh; tampering with `localStorage` alone is not enough to unlock backend-protected admin actions.

### Known security stance

- `localStorage` is treated as a UI cache only, not a source of authority.
- Real authorization lives in backend permission checks under `require_permission(...)`.
- Refresh token rotation and revocation remain the source of session continuity and forced logout control.

### Follow-up ideas

- Move high-volume auth and admin audit writes to a background queue or dedicated async log sink if write latency grows further.
- Consider secure cookies in non-local deployments and environment-based cookie settings.
- Add integration tests for reload-on-admin-page, MFA replay, and refresh-token rotation.
