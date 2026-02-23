-- =====================================================
-- BioAttend Session-Based Attendance Migration
-- Run this to add new tables for session management
-- =====================================================

-- 1. Create attendance_sessions table
CREATE TABLE IF NOT EXISTS attendance_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    otp VARCHAR(6) NOT NULL,
    qr_token VARCHAR(64) NOT NULL,
    course_name TEXT NOT NULL,
    professor_name TEXT NOT NULL,
    classroom_location TEXT,
    classroom_lat DECIMAL(10, 8),
    classroom_lon DECIMAL(11, 8),
    geofence_radius INTEGER DEFAULT 50,
    allowed_wifi_ssid TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Constraints
    CONSTRAINT valid_geofence_radius CHECK (geofence_radius > 0 AND geofence_radius <= 500),
    CONSTRAINT valid_otp CHECK (LENGTH(otp) = 6),
    CONSTRAINT valid_expiry CHECK (expires_at > created_at)
);

-- 2. Create session_attendance table
CREATE TABLE IF NOT EXISTS session_attendance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Verification data
    device_info JSONB,
    location_data JSONB,
    verification_scores JSONB,
    liveness_data JSONB,
    verification_method TEXT,
    
    -- Prevent duplicate attendance in same session
    UNIQUE(session_id, student_id)
);

-- 3. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_active 
ON attendance_sessions(is_active, expires_at) 
WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_sessions_otp 
ON attendance_sessions(otp) 
WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_session_attendance_session 
ON session_attendance(session_id);

CREATE INDEX IF NOT EXISTS idx_session_attendance_student 
ON session_attendance(student_id);

CREATE INDEX IF NOT EXISTS idx_session_attendance_marked_at 
ON session_attendance(marked_at);

-- 4. Create view for active sessions
CREATE OR REPLACE VIEW active_sessions AS
SELECT 
    id,
    otp,
    course_name,
    professor_name,
    classroom_location,
    expires_at,
    EXTRACT(EPOCH FROM (expires_at - NOW())) AS seconds_remaining
FROM attendance_sessions
WHERE is_active = TRUE AND expires_at > NOW()
ORDER BY created_at DESC;

-- 5. Create function to auto-deactivate expired sessions
CREATE OR REPLACE FUNCTION deactivate_expired_sessions()
RETURNS void AS $$
BEGIN
    UPDATE attendance_sessions
    SET is_active = FALSE
    WHERE is_active = TRUE AND expires_at <= NOW();
END;
$$ LANGUAGE plpgsql;

-- 6. Add comments for documentation
COMMENT ON TABLE attendance_sessions IS 'Stores professor-created attendance sessions with location and time constraints';
COMMENT ON TABLE session_attendance IS 'Records student attendance for each session with verification details';
COMMENT ON COLUMN attendance_sessions.otp IS '6-digit one-time password valid for session duration';
COMMENT ON COLUMN attendance_sessions.qr_token IS 'Dynamic token for QR code that refreshes every 30 seconds';
COMMENT ON COLUMN session_attendance.verification_scores IS 'JSON object storing scores for wifi, gps, qr, device checks';
COMMENT ON COLUMN session_attendance.liveness_data IS 'JSON object storing blink count, head movement angles, confidence scores';

-- 7. Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE 'Tables created: attendance_sessions, session_attendance';
    RAISE NOTICE 'Indexes created: 5 indexes for performance';
    RAISE NOTICE 'Views created: active_sessions';
END $$;