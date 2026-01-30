CREATE TABLE IF NOT EXISTS user_profile (
  user_id UUID PRIMARY KEY,
  timezone TEXT DEFAULT 'Asia/Kolkata',
  tone_preference TEXT DEFAULT 'warm',
  depth_permission TEXT DEFAULT 'medium',
  preferences JSONB DEFAULT '{}'::jsonb,
  traits JSONB DEFAULT '{}'::jsonb,
  values TEXT[] DEFAULT ARRAY['clarity','balance']
);
