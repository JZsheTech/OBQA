CREATE TABLE IF NOT EXISTS papers (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    arxiv_id VARCHAR(32) NOT NULL UNIQUE,
    version VARCHAR(16) NULL,
    title TEXT NOT NULL,
    summary MEDIUMTEXT NULL,
    authors TEXT NULL,
    primary_category VARCHAR(64) NULL,
    categories TEXT NULL,
    published DATETIME NULL,
    updated DATETIME NULL,
    pdf_url VARCHAR(512) NULL,
    abs_url VARCHAR(512) NULL,
    doi VARCHAR(128) NULL,
    journal_ref VARCHAR(512) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_papers_arxiv_id (arxiv_id),
    INDEX idx_papers_primary_category (primary_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS saved_papers (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    paper_id BIGINT NOT NULL,
    tags VARCHAR(512) NULL,
    note TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_saved_papers_paper
        FOREIGN KEY (paper_id) REFERENCES papers(id)
        ON DELETE CASCADE,
    INDEX idx_saved_papers_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
