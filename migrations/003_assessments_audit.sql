-- Enrollments, versioned exams, attempts and audit events.
CREATE TABLE IF NOT EXISTS enrollments (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  course_key VARCHAR(120) NOT NULL DEFAULT 'ai-learning-lab',
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP,
  assigned_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT uq_enrollment_user_course UNIQUE (user_id, course_key)
);

CREATE TABLE IF NOT EXISTS exams (
  id SERIAL PRIMARY KEY,
  course_key VARCHAR(120) NOT NULL DEFAULT 'ai-learning-lab',
  title VARCHAR(200) NOT NULL,
  version VARCHAR(40) NOT NULL DEFAULT '1.0',
  question_ids TEXT NOT NULL DEFAULT '[]',
  pass_percent INTEGER NOT NULL DEFAULT 75,
  is_published BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attempts (
  id SERIAL PRIMARY KEY,
  exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  answers TEXT NOT NULL DEFAULT '{}',
  score_percent INTEGER NOT NULL DEFAULT 0,
  passed BOOLEAN NOT NULL DEFAULT FALSE,
  status VARCHAR(32) NOT NULL DEFAULT 'submitted',
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  submitted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id SERIAL PRIMARY KEY,
  actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  action VARCHAR(120) NOT NULL,
  resource_type VARCHAR(80) NOT NULL DEFAULT 'system',
  resource_id VARCHAR(120),
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
