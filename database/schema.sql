-- AIRA — AI Incident Reporting Application
-- MySQL 8.0+ schema

CREATE DATABASE IF NOT EXISTS aira
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE aira;

-- ----------------------------------------------------------------------
-- users
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  full_name       VARCHAR(150)  NOT NULL,
  email           VARCHAR(190)  NOT NULL UNIQUE,
  phone           VARCHAR(20)   NULL,
  password_hash   VARCHAR(255)  NOT NULL,
  national_id     VARCHAR(32)   NULL,
  role            ENUM('citizen','officer','admin') NOT NULL DEFAULT 'citizen',
  is_verified     TINYINT(1)    NOT NULL DEFAULT 0,
  is_active       TINYINT(1)    NOT NULL DEFAULT 1,
  created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_users_role (role),
  INDEX idx_users_phone (phone)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------
-- stations
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stations (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name            VARCHAR(150)  NOT NULL,
  district        VARCHAR(100)  NULL,
  sector          VARCHAR(100)  NULL,
  latitude        DECIMAL(10,7) NULL,
  longitude       DECIMAL(10,7) NULL,
  contact_phone   VARCHAR(20)   NULL,
  created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_stations_district (district)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------
-- officers
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS officers (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id         BIGINT UNSIGNED NOT NULL UNIQUE,
  badge_number    VARCHAR(50)   NOT NULL UNIQUE,
  station_id      BIGINT UNSIGNED NULL,
  `rank`          VARCHAR(50)   NULL,
  department      VARCHAR(100)  NULL,
  created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_officers_user    FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE,
  CONSTRAINT fk_officers_station FOREIGN KEY (station_id) REFERENCES stations(id) ON DELETE SET NULL,
  INDEX idx_officers_station (station_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------
-- incidents
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS incidents (
  id                   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  reporter_id          BIGINT UNSIGNED NOT NULL,
  image_url            VARCHAR(500)  NULL,
  ai_description       TEXT          NULL,
  user_description     TEXT          NULL,
  incident_type        VARCHAR(80)   NULL,
  severity_level       ENUM('low','medium','high','critical') NOT NULL DEFAULT 'medium',
  latitude             DECIMAL(10,7) NULL,
  longitude            DECIMAL(10,7) NULL,
  status               ENUM('pending','analyzing','verified','assigned','in_progress','resolved','rejected')
                       NOT NULL DEFAULT 'pending',
  assigned_officer_id  BIGINT UNSIGNED NULL,
  station_id           BIGINT UNSIGNED NULL,
  created_at           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  resolved_at          DATETIME      NULL,
  CONSTRAINT fk_incidents_reporter FOREIGN KEY (reporter_id)         REFERENCES users(id)    ON DELETE CASCADE,
  CONSTRAINT fk_incidents_officer  FOREIGN KEY (assigned_officer_id) REFERENCES officers(id) ON DELETE SET NULL,
  CONSTRAINT fk_incidents_station  FOREIGN KEY (station_id)          REFERENCES stations(id) ON DELETE SET NULL,
  INDEX idx_incidents_status      (status),
  INDEX idx_incidents_reporter    (reporter_id),
  INDEX idx_incidents_officer     (assigned_officer_id),
  INDEX idx_incidents_created_at  (created_at),
  INDEX idx_incidents_type        (incident_type),
  INDEX idx_incidents_severity    (severity_level),
  INDEX idx_incidents_geo         (latitude, longitude)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------
-- incident_images (multiple images per incident)
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS incident_images (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  incident_id   BIGINT UNSIGNED NOT NULL,
  image_url     VARCHAR(500)  NOT NULL,
  image_order   INT           NOT NULL DEFAULT 0,
  created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_images_incident FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
  INDEX idx_images_incident (incident_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------
-- ai_analysis
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_analysis (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  incident_id       BIGINT UNSIGNED NOT NULL,
  detected_objects  JSON          NULL,
  scene_label       VARCHAR(120)  NULL,
  caption           TEXT          NULL,
  confidence_score  DECIMAL(5,4)  NULL,
  model_version     VARCHAR(50)   NULL,
  raw_output        JSON          NULL,
  created_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ai_incident FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
  INDEX idx_ai_incident (incident_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------
-- incident_updates (status history / audit)
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS incident_updates (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  incident_id     BIGINT UNSIGNED NOT NULL,
  officer_id      BIGINT UNSIGNED NULL,
  update_message  TEXT          NULL,
  status_change   VARCHAR(50)   NULL,
  created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_updates_incident FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
  CONSTRAINT fk_updates_officer  FOREIGN KEY (officer_id)  REFERENCES officers(id)  ON DELETE SET NULL,
  INDEX idx_updates_incident (incident_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------
-- notifications
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
  id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id             BIGINT UNSIGNED NOT NULL,
  title               VARCHAR(200)  NOT NULL,
  message             TEXT          NULL,
  type                VARCHAR(50)   NOT NULL DEFAULT 'info',
  related_incident_id BIGINT UNSIGNED NULL,
  is_read             TINYINT(1)    NOT NULL DEFAULT 0,
  created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_notif_user     FOREIGN KEY (user_id)             REFERENCES users(id)     ON DELETE CASCADE,
  CONSTRAINT fk_notif_incident FOREIGN KEY (related_incident_id) REFERENCES incidents(id) ON DELETE SET NULL,
  INDEX idx_notif_user (user_id),
  INDEX idx_notif_read (is_read)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------
-- feedback_messages (chat between citizen and police)
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feedback_messages (
  id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  incident_id  BIGINT UNSIGNED NOT NULL,
  sender_id    BIGINT UNSIGNED NOT NULL,
  sender_role  ENUM('citizen','officer','admin') NOT NULL,
  message      TEXT          NOT NULL,
  created_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_msg_incident FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
  CONSTRAINT fk_msg_sender   FOREIGN KEY (sender_id)   REFERENCES users(id)     ON DELETE CASCADE,
  INDEX idx_msg_incident (incident_id),
  INDEX idx_msg_created  (created_at)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------
-- device_tokens (push notifications)
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS device_tokens (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     BIGINT UNSIGNED NOT NULL,
  token       VARCHAR(500)  NOT NULL,
  platform    ENUM('android','ios','web') NOT NULL,
  created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_dev_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY uq_dev_token (token(255)),
  INDEX idx_dev_user (user_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------
-- password_reset_codes
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS password_reset_codes (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     BIGINT UNSIGNED NOT NULL,
  code        VARCHAR(10)   NOT NULL,
  expires_at  DATETIME      NOT NULL,
  used        TINYINT(1)    NOT NULL DEFAULT 0,
  created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_prc_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_prc_user (user_id)
) ENGINE=InnoDB;
