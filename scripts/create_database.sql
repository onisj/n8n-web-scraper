-- Create database for n8n Documentation Automation System
-- This script sets up the main database schema

-- Create database (run this as postgres superuser)
-- CREATE DATABASE n8n_scraper;
-- \c n8n_scraper;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS docs;
CREATE SCHEMA IF NOT EXISTS automation;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Documentation tables
CREATE TABLE IF NOT EXISTS docs.pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    content TEXT,
    content_hash VARCHAR(64),
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active',
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS docs.page_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    page_id UUID REFERENCES docs.pages(id) ON DELETE CASCADE,
    section_type VARCHAR(50), -- 'heading', 'paragraph', 'code_block', 'list', etc.
    content TEXT,
    order_index INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS docs.page_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_page_id UUID REFERENCES docs.pages(id) ON DELETE CASCADE,
    target_url TEXT NOT NULL,
    link_text TEXT,
    link_type VARCHAR(20) DEFAULT 'internal', -- 'internal', 'external'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS docs.code_blocks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    page_id UUID REFERENCES docs.pages(id) ON DELETE CASCADE,
    language VARCHAR(50),
    code_content TEXT,
    line_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Automation tracking tables
CREATE TABLE IF NOT EXISTS automation.scraping_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'running', -- 'running', 'completed', 'failed'
    pages_scraped INTEGER DEFAULT 0,
    pages_updated INTEGER DEFAULT 0,
    pages_new INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS automation.change_detection (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    page_id UUID REFERENCES docs.pages(id) ON DELETE CASCADE,
    run_id UUID REFERENCES automation.scraping_runs(id) ON DELETE CASCADE,
    change_type VARCHAR(50), -- 'new', 'updated', 'deleted', 'unchanged'
    old_content_hash VARCHAR(64),
    new_content_hash VARCHAR(64),
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    changes_summary JSONB DEFAULT '{}'
);

-- Analytics tables
CREATE TABLE IF NOT EXISTS analytics.content_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_pages INTEGER,
    total_sections INTEGER,
    total_code_blocks INTEGER,
    total_links INTEGER,
    avg_page_length NUMERIC,
    most_common_languages JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_pages_url ON docs.pages(url);
CREATE INDEX IF NOT EXISTS idx_pages_updated_at ON docs.pages(updated_at);
CREATE INDEX IF NOT EXISTS idx_pages_content_hash ON docs.pages(content_hash);
CREATE INDEX IF NOT EXISTS idx_page_sections_page_id ON docs.page_sections(page_id);
CREATE INDEX IF NOT EXISTS idx_page_sections_type ON docs.page_sections(section_type);
CREATE INDEX IF NOT EXISTS idx_page_links_source ON docs.page_links(source_page_id);
CREATE INDEX IF NOT EXISTS idx_code_blocks_page_id ON docs.code_blocks(page_id);
CREATE INDEX IF NOT EXISTS idx_code_blocks_language ON docs.code_blocks(language);
CREATE INDEX IF NOT EXISTS idx_scraping_runs_started ON automation.scraping_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_change_detection_page ON automation.change_detection(page_id);
CREATE INDEX IF NOT EXISTS idx_change_detection_run ON automation.change_detection(run_id);

-- Create full-text search indexes
CREATE INDEX IF NOT EXISTS idx_pages_content_fts ON docs.pages USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_pages_title_fts ON docs.pages USING gin(to_tsvector('english', title));

-- Create triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_pages_updated_at BEFORE UPDATE ON docs.pages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial data or configuration
INSERT INTO analytics.content_stats (total_pages, total_sections, total_code_blocks, total_links, avg_page_length)
VALUES (0, 0, 0, 0, 0.0)
ON CONFLICT DO NOTHING;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA docs TO n8n_scraper_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA automation TO n8n_scraper_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO n8n_scraper_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA docs TO n8n_scraper_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA automation TO n8n_scraper_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA analytics TO n8n_scraper_user;

SELECT 'Database schema created successfully!' as result;