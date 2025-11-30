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
  abstract TEXT,
  file_name VARCHAR(512),
  file_path VARCHAR(1024),
  file_sha256 VARCHAR(128),
  file_size_bytes BIGINT,
  num_pages INT,
  element_count INT DEFAULT 0,
  meta_info JSON,
  arxiv_favorite_id BIGINT NULL,
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

SET @missing_abstract := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'documents' AND COLUMN_NAME = 'abstract'
);
SET @sql := IF(@missing_abstract = 0, 'ALTER TABLE documents ADD COLUMN abstract TEXT AFTER md_text', 'SELECT 1');
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

SET @missing_meta_info := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'documents' AND COLUMN_NAME = 'meta_info'
);
SET @sql := IF(@missing_meta_info = 0, 'ALTER TABLE documents ADD COLUMN meta_info JSON AFTER element_count', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @missing_arxiv_favorite := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'documents' AND COLUMN_NAME = 'arxiv_favorite_id'
);
SET @sql := IF(@missing_arxiv_favorite = 0, 'ALTER TABLE documents ADD COLUMN arxiv_favorite_id BIGINT NULL AFTER meta_info', 'SELECT 1');
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
  raw_text_content MEDIUMTEXT,
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

SET @missing_raw_text_content := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'elements' AND COLUMN_NAME = 'raw_text_content'
);
SET @sql := IF(@missing_raw_text_content = 0, 'ALTER TABLE elements ADD COLUMN raw_text_content MEDIUMTEXT AFTER text_content', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS chunks (
  id BIGINT NOT NULL AUTO_INCREMENT,
  doc_id BIGINT NOT NULL,
  collection_id BIGINT NOT NULL,
  `order` INT NOT NULL,
  level_nav VARCHAR(1024),
  chunk_type VARCHAR(32) NOT NULL CHECK (chunk_type IN ('text','image','table')),
  chunk_text_main MEDIUMTEXT,
  elem_ids JSON,
  page_start INT,
  page_end INT,
  vec_embedding VECTOR({{VECTOR_DIM}}) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_chunks_document
    FOREIGN KEY (doc_id) REFERENCES documents(id)
    ON DELETE CASCADE
);

SET @missing_chunks_doc_idx := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'chunks' AND INDEX_NAME = 'idx_chunks_doc_order'
);
SET @sql := IF(@missing_chunks_doc_idx = 0, 'CREATE INDEX idx_chunks_doc_order ON chunks (doc_id, `order`)', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @missing_chunks_collection_idx := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'chunks' AND INDEX_NAME = 'idx_chunks_collection'
);
SET @sql := IF(@missing_chunks_collection_idx = 0, 'CREATE INDEX idx_chunks_collection ON chunks (collection_id, `order`)', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS page_text_chunks (
  id BIGINT NOT NULL AUTO_INCREMENT,
  doc_id BIGINT NOT NULL,
  collection_id BIGINT NOT NULL,
  chunk_text_main MEDIUMTEXT,
  elem_ids JSON,
  page_no INT,
  chunk_type VARCHAR(32) NOT NULL DEFAULT 'text' CHECK (chunk_type IN ('text')),
  vec_embedding VECTOR({{VECTOR_DIM}}) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_page_text_chunks_document
    FOREIGN KEY (doc_id) REFERENCES documents(id)
    ON DELETE CASCADE
);

SET @missing_page_chunks_doc_idx := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'page_text_chunks' AND INDEX_NAME = 'idx_page_text_chunks_doc_page'
);
SET @sql := IF(@missing_page_chunks_doc_idx = 0, 'CREATE INDEX idx_page_text_chunks_doc_page ON page_text_chunks (doc_id, page_no)', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @missing_page_chunks_collection_idx := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'page_text_chunks' AND INDEX_NAME = 'idx_page_text_chunks_collection'
);
SET @sql := IF(@missing_page_chunks_collection_idx = 0, 'CREATE INDEX idx_page_text_chunks_collection ON page_text_chunks (collection_id, page_no)', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS chats (
  id BIGINT NOT NULL AUTO_INCREMENT,
  collection_id BIGINT,
  document_id BIGINT,
  `type` VARCHAR(32) NOT NULL DEFAULT 'collection' CHECK (`type` IN ('collection','document')),
  title VARCHAR(255),
  max_turn_order BIGINT DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_chats_collection
    FOREIGN KEY (collection_id) REFERENCES collections(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_chats_document
    FOREIGN KEY (document_id) REFERENCES documents(id)
    ON DELETE CASCADE
);

SET @missing_chat_document_id := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'chats' AND COLUMN_NAME = 'document_id'
);
SET @sql := IF(@missing_chat_document_id = 0, 'ALTER TABLE chats ADD COLUMN document_id BIGINT AFTER collection_id', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @missing_chat_type := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'chats' AND COLUMN_NAME = 'type'
);
SET @sql := IF(@missing_chat_type = 0, "ALTER TABLE chats ADD COLUMN `type` VARCHAR(32) NOT NULL DEFAULT 'collection' AFTER document_id", "SELECT 1");
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @needs_collection_nullability_update := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'chats' AND COLUMN_NAME = 'collection_id' AND IS_NULLABLE = 'NO'
);
SET @sql := IF(@needs_collection_nullability_update > 0, 'ALTER TABLE chats MODIFY COLUMN collection_id BIGINT NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @missing_chat_document_fk := (
  SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'chats' AND CONSTRAINT_NAME = 'fk_chats_document'
);
SET @sql := IF(@missing_chat_document_fk = 0, 'ALTER TABLE chats ADD CONSTRAINT fk_chats_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE chats SET `type` = 'collection' WHERE `type` IS NULL OR `type` = '';

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

CREATE TABLE IF NOT EXISTS arxiv_favorite_doc (
  id BIGINT NOT NULL AUTO_INCREMENT,
  arxiv_id VARCHAR(64) NOT NULL,
  version VARCHAR(16),
  title TEXT NOT NULL,
  summary MEDIUMTEXT,
  authors JSON,
  primary_category VARCHAR(64),
  categories JSON,
  pdf_url VARCHAR(1024),
  abs_url VARCHAR(1024),
  doi VARCHAR(128),
  journal_ref VARCHAR(512),
  tags VARCHAR(512),
  note MEDIUMTEXT,
  published DATETIME,
  updated DATETIME,
  document_id BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uq_arxiv_favorite_doc_arxiv_id UNIQUE (arxiv_id),
  CONSTRAINT fk_arxiv_favorite_doc_document
    FOREIGN KEY (document_id) REFERENCES documents(id)
    ON DELETE SET NULL
);

SET @missing_arxiv_doc_fk := (
  SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'documents' AND CONSTRAINT_NAME = 'fk_documents_arxiv_favorite'
);
SET @sql := IF(@missing_arxiv_doc_fk = 0, 'ALTER TABLE documents ADD CONSTRAINT fk_documents_arxiv_favorite FOREIGN KEY (arxiv_favorite_id) REFERENCES arxiv_favorite_doc(id) ON DELETE SET NULL', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
