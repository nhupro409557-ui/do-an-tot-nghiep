-- Migration: Thêm search index cho bảng users để tối ưu tìm kiếm khách hàng
-- Yêu cầu: PostgreSQL extension pg_trgm (hỗ trợ LIKE/ILIKE index)

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Trigram index cho tìm kiếm theo tên (LIKE '%keyword%')
CREATE INDEX IF NOT EXISTS idx_users_fullname_trgm
    ON users USING GIN (full_name gin_trgm_ops);

-- Trigram index cho tìm kiếm theo email
CREATE INDEX IF NOT EXISTS idx_users_email_trgm
    ON users USING GIN (email gin_trgm_ops);

-- Trigram index cho tìm kiếm theo số điện thoại
CREATE INDEX IF NOT EXISTS idx_users_phone_trgm
    ON users USING GIN (phone gin_trgm_ops);

-- Composite index cho WHERE clause chính: status + role_id
CREATE INDEX IF NOT EXISTS idx_users_status_role
    ON users (status, role_id);

-- Index cho ORDER BY created_at DESC + pagination
CREATE INDEX IF NOT EXISTS idx_users_created_at_desc
    ON users (created_at DESC);
