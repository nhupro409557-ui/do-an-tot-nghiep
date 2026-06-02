# Data Invariants
1. A user can only access and modify their own `/users/{userId}` document.
2. Only an admin can write to `/products/{productId}` and `/vouchers/{voucherId}` and `/ai_context/{contextId}`.
3. Anyone can read active products.
4. A user can only create an order in `/orders/{orderId}` where `request.auth.uid == data.userId`.
5. Only admins can update the status of an order.
6. A user can only create a review in `/products/{productId}/reviews/{reviewId}` where `request.auth.uid == data.userId`.
7. Points and tiers can only be modified by admins.
8. Timestamps must be server times.

# Dirty Dozen Payloads
1. User creates a product (Admin only).
2. User modifies their own `role` or `points` to become admin or get free points.
3. User reads another user's profile.
4. User queries all orders without filtering by their own `userId`.
5. User creates an order for another `userId`.
6. User updates the `status` of an order.
7. User creates an order with a massive string ID to exhaust DB limits.
8. User creates a review under someone else's ID.
9. User updates another user's order.
10. Unauthenticated user gets a product.
11. User deletes a product.
12. User bypasses schema by adding an extra field like `isAdmin` to their review.

# Admin Auth Notes
1. The admin area must wait for silent refresh to finish before redirecting on reload.
2. Frontend `localStorage` values are cache only; backend permission checks remain authoritative.
3. Admin MFA temp tokens should be single-use within their short lifetime to reduce replay risk.
4. Token fingerprinting should avoid brittle IP-prefix coupling because mobile networks change IPs frequently.
