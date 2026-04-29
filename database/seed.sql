-- AIRA seed data
-- Passwords are bcrypt hashes for the values in the README ("Admin@123", "Officer@1", "Citizen@1")
-- Generated with: bcrypt(rounds=12)

USE aira;

-- Stations -------------------------------------------------------------
INSERT INTO stations (name, district, sector, latitude, longitude, contact_phone) VALUES
  ('Kigali Central Police Station',  'Nyarugenge', 'Nyarugenge', -1.9536, 30.0606, '+250788000001'),
  ('Remera Police Station',          'Gasabo',     'Remera',     -1.9501, 30.1100, '+250788000002'),
  ('Kicukiro Police Station',        'Kicukiro',   'Niboyi',     -1.9806, 30.1100, '+250788000003');

-- Users ----------------------------------------------------------------
-- Admin
INSERT INTO users (full_name, email, phone, password_hash, role, is_verified)
VALUES (
  'System Administrator',
  'admin@rnp.gov.rw',
  '+250788111111',
  '$2b$12$EorFu6YIFOrx4b4gE8Ks.eAFIi4Ko0Kj4y3L8.qS8Q4WjT3uVz3tq',
  'admin',
  1
);

-- Officer
INSERT INTO users (full_name, email, phone, password_hash, role, is_verified)
VALUES (
  'Officer John Mugisha',
  'officer1@rnp.gov.rw',
  '+250788222222',
  '$2b$12$ynqg9I/XmeqlF3bnTRRykuQENZBDB4U6S1c/fI2X1wA6P0V37yxKW',
  'officer',
  1
);

-- Citizen
INSERT INTO users (full_name, email, phone, password_hash, role, is_verified)
VALUES (
  'Jean Citizen',
  'citizen@example.com',
  '+250788333333',
  '$2b$12$LqBNm3dKWf1WB5xGxF0BMOqv8uuOYcIPa2g/uHSPgOIkiEv7lcgCi',
  'citizen',
  1
);

-- Officer profile ------------------------------------------------------
INSERT INTO officers (user_id, badge_number, station_id, `rank`, department)
SELECT u.id, 'RNP-0001', 1, 'Inspector', 'Patrol'
FROM users u WHERE u.email = 'officer1@rnp.gov.rw';

-- Note: the password hashes above are placeholders. Run
-- `python backend/scripts/seed_passwords.py` after first boot to replace
-- them with freshly generated hashes for the documented passwords.
