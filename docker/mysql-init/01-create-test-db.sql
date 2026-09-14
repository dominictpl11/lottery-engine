-- Tests run against a separate schema so they never touch dev data.
-- Executed once, on first initialisation of the MySQL data volume.
CREATE DATABASE IF NOT EXISTS lottery_test
    DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON lottery_test.* TO 'lottery'@'%';
FLUSH PRIVILEGES;
