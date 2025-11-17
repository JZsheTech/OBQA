-- EviQAsys OceanBase schema (M1)
CREATE TABLE IF NOT EXISTS collections (
  id BIGINT NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  description VARCHAR(1024),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS documents (
  id BIGINT NOT NULL AUTO_INCREMENT,
  collection_id BIGINT NOT NULL,
  title VARCHAR(512),
  md_text MEDIUMTEXT,
  file_name VARCHAR(512),
  file_path VARCHAR(1024),
  file_sha256 VARCHAR(128),
  file_size_bytes BIGINT,
  num_pages INT,
  element_count INT DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_documents_collection
    FOREIGN KEY (collection_id) REFERENCES collections(id)
    ON DELETE CASCADE
);

SET @missing_md_text := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'documents' AND COLUMN_NAME = 'md_text'
);
SET @sql := IF(@missing_md_text = 0, 'ALTER TABLE documents ADD COLUMN md_text MEDIUMTEXT AFTER title', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @missing_file_sha := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'documents' AND COLUMN_NAME = 'file_sha256'
);
SET @sql := IF(@missing_file_sha = 0, 'ALTER TABLE documents ADD COLUMN file_sha256 VARCHAR(128) AFTER file_path', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @missing_file_size := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'documents' AND COLUMN_NAME = 'file_size_bytes'
);
SET @sql := IF(@missing_file_size = 0, 'ALTER TABLE documents ADD COLUMN file_size_bytes BIGINT AFTER file_sha256', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @missing_element_count := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'documents' AND COLUMN_NAME = 'element_count'
);
SET @sql := IF(@missing_element_count = 0, 'ALTER TABLE documents ADD COLUMN element_count INT DEFAULT 0 AFTER num_pages', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS elements (
  id BIGINT NOT NULL AUTO_INCREMENT,
  doc_id BIGINT NOT NULL,
  `order` INT NOT NULL,
  elem_type VARCHAR(32) NOT NULL CHECK (elem_type IN ('text','header','image','table','equation')),
  header_name VARCHAR(512),
  header_level INT,
  level_nav VARCHAR(1024),
  text_content MEDIUMTEXT,
  text_caption MEDIUMTEXT,
  image_base64 MEDIUMTEXT,
  bbox_json JSON,
  page_no INT,
  -- vec_embedding uses VECTOR(<VECTOR_DIM>) sized by environment variable
  vec_embedding VECTOR({{VECTOR_DIM}}) NULL,
  order_start VARCHAR(255),
  order_end VARCHAR(255),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_elements_document
    FOREIGN KEY (doc_id) REFERENCES documents(id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chats (
  id BIGINT NOT NULL AUTO_INCREMENT,
  collection_id BIGINT NOT NULL,
  title VARCHAR(255),
  max_turn_order BIGINT DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_chats_collection
    FOREIGN KEY (collection_id) REFERENCES collections(id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS turns (
  id BIGINT NOT NULL AUTO_INCREMENT,
  chat_id BIGINT NOT NULL,
  `order` INT NOT NULL,
  user_question MEDIUMTEXT,
  llm_answer_text MEDIUMTEXT,
  llm_thought_text MEDIUMTEXT,
  response_tokens INT,
  used_llm_model VARCHAR(128),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_turns_chat
    FOREIGN KEY (chat_id) REFERENCES chats(id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS turn2element (
  chat_id BIGINT NOT NULL,
  turn_id BIGINT NOT NULL,
  turn_order INT NOT NULL,
  element_id BIGINT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (chat_id, turn_id, element_id),
  CONSTRAINT fk_turn2element_chat
    FOREIGN KEY (chat_id) REFERENCES chats(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_turn2element_turn
    FOREIGN KEY (turn_id) REFERENCES turns(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_turn2element_element
    FOREIGN KEY (element_id) REFERENCES elements(id)
    ON DELETE CASCADE
);
