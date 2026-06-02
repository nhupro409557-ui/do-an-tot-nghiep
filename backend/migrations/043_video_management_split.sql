ALTER TABLE videos ADD COLUMN IF NOT EXISTS video_source VARCHAR(30) NOT NULL DEFAULT 'UPLOAD';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS video_category VARCHAR(60) NOT NULL DEFAULT 'PRODUCT';

ALTER TABLE content_comments ADD COLUMN IF NOT EXISTS reply_to_user_name VARCHAR(120);
ALTER TABLE content_comments ADD COLUMN IF NOT EXISTS moderation_reason VARCHAR(255);
ALTER TABLE content_comments ADD COLUMN IF NOT EXISTS is_retracted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE content_comments ADD COLUMN IF NOT EXISTS retracted_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS video_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(video_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_video_likes_video_id ON video_likes(video_id);
CREATE INDEX IF NOT EXISTS idx_video_likes_user_id ON video_likes(user_id);
CREATE INDEX IF NOT EXISTS idx_videos_video_category ON videos(video_category);
