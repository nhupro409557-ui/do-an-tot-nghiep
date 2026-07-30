## Admin Auth Notes

This note tracks the current admin authentication design and the rationale behind recent changes so later edits have a stable reference point.

### Cập nhật 2026-07-05 - Khóa lỗ hổng mạo danh user và xác minh auth ngoài hệ thống

- `get_current_user_id` không còn tin header `X-User-Id`; các route protected chỉ lấy user từ JWT Bearer hợp lệ.
- Bổ sung `get_optional_current_user_id` cho các luồng public có thể nhận JWT, ví dụ checkout guest hoặc AI chat, nhưng nếu có token sai thì trả `401`.
- Google Login không còn nhận email/tên/avatar do frontend tự gửi. Frontend chỉ gửi Google access token, backend tự gọi Google tokeninfo/userinfo và kiểm tra `GOOGLE_CLIENT_ID` trước khi tạo/cập nhật user.
- AI chat không còn dùng `X-User-Id`; nếu có phiên đăng nhập thì frontend gửi Bearer token, backend tự resolve user.

### Current flow

1. Admin enters email and password at `/admin/login`.
2. Backend validates the account, checks admin permissions, and applies lockout rules for repeated failures.
3. Backend requires MFA for all admin-capable accounts.
5. Every admin API still enforces permission checks on the backend, regardless of what the frontend renders.

### Recent hardening

- Silent refresh bootstrap is now explicit on the frontend so route guards wait for auth restoration before redirecting.
- Access-token fingerprinting is now based on `User-Agent` only instead of `User-Agent + IP prefix` to avoid false logouts on mobile and carrier networks.
- Frontend admin visibility must survive a server-backed refresh; tampering with `localStorage` alone is not enough to unlock backend-protected admin actions.

### Known security stance

- `localStorage` is treated as a UI cache only, not a source of authority.
- Real authorization lives in backend permission checks under `require_permission(...)`.
- Refresh token rotation and revocation remain the source of session continuity and forced logout control.

### Follow-up ideas

- Move high-volume auth and admin audit writes to a background queue or dedicated async log sink if write latency grows further.
- Consider secure cookies in non-local deployments and environment-based cookie settings.
- Add integration tests for MFA replay and refresh-token rotation.
