-- Unified PostgreSQL Schema for n8n Web Scraper
-- This schema consolidates documentation and workflow data into a single, coherent structure

-- Drop existing tables if they exist (for clean migration)
DROP TABLE IF EXISTS docs_workflows CASCADE;
DROP TABLE IF EXISTS docs_video_courses CASCADE;
DROP TABLE IF EXISTS docs_user_management CASCADE;
DROP TABLE IF EXISTS docs_try_it_out CASCADE;
DROP TABLE IF EXISTS docs_sustainable_use_license CASCADE;
DROP TABLE IF EXISTS docs_source_control_environments CASCADE;
DROP TABLE IF EXISTS docs_root CASCADE;
DROP TABLE IF EXISTS docs_release_notes CASCADE;
DROP TABLE IF EXISTS docs_reference CASCADE;
DROP TABLE IF EXISTS docs_courses CASCADE;
DROP TABLE IF EXISTS docs_code_cookbook CASCADE;
DROP TABLE IF EXISTS docs_code_builtin CASCADE;
DROP TABLE IF EXISTS docs_code CASCADE;
DROP TABLE IF EXISTS docs_choose_n8n CASCADE;
DROP TABLE IF EXISTS docs_api CASCADE;
DROP TABLE IF EXISTS docs_advanced_ai CASCADE;
DROP TABLE IF EXISTS docs__workflows CASCADE;
DROP TABLE IF EXISTS docs_1_0_migration_checklist CASCADE;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Unified Documents Table
-- This table handles both scraped documentation and workflow documents
CREATE TABLE IF NOT EXISTS unified_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Document Type and Source
    document_type VARCHAR(32) NOT NULL CHECK (document_type IN ('documentation', 'workflow')),
    source_type VARCHAR(32) NOT NULL CHECK (source_type IN ('web_scrape', 'file_import', 'api')),
    
    -- Common Identification Fields
    title VARCHAR(1024) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    
    -- URL/Path Information (unified)
    url TEXT, -- For documentation
    file_path VARCHAR(1024), -- For workflows
    file_name VARCHAR(256),
    
    -- Categorization
    category VARCHAR(128),
    subcategory VARCHAR(128),
    tags JSONB DEFAULT '[]'::jsonb,
    
    -- Content Analysis
    word_count INTEGER CHECK (word_count >= 0),
    content_length INTEGER,
    language VARCHAR(10) DEFAULT 'en',
    
    -- Workflow-specific fields (NULL for documentation)
    workflow_id VARCHAR(128), -- n8n workflow ID
    workflow_data JSONB, -- Full workflow JSON
    version VARCHAR(32),
    node_count INTEGER CHECK (node_count >= 0),
    connection_count INTEGER CHECK (connection_count >= 0),
    trigger_types JSONB DEFAULT '[]'::jsonb,
    node_types JSONB DEFAULT '[]'::jsonb,
    integrations JSONB DEFAULT '[]'::jsonb,
    
    -- Documentation-specific fields (NULL for workflows)
    headings JSONB DEFAULT '[]'::jsonb,
    links JSONB DEFAULT '[]'::jsonb,
    code_blocks JSONB DEFAULT '[]'::jsonb,
    images JSONB DEFAULT '[]'::jsonb,
    headings_count INTEGER,
    links_count INTEGER,
    code_blocks_count INTEGER,
    images_count INTEGER,
    
    -- Processing Status
    is_processed BOOLEAN DEFAULT FALSE NOT NULL,
    processing_error TEXT,
    
    -- Quality Metrics
    quality_score FLOAT CHECK (quality_score >= 0 AND quality_score <= 1),
    complexity_score FLOAT CHECK (complexity_score >= 0 AND complexity_score <= 1),
    completeness_score FLOAT CHECK (completeness_score >= 0 AND completeness_score <= 1),
    readability_score FLOAT CHECK (readability_score >= 0 AND readability_score <= 1),
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    scraped_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Unified Chunks Table
-- This table handles chunks for both documentation and workflows
CREATE TABLE IF NOT EXISTS unified_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Foreign key to parent document
    document_id UUID NOT NULL REFERENCES unified_documents(id) ON DELETE CASCADE,
    
    -- Chunk Properties
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    chunk_type VARCHAR(64) NOT NULL, -- 'content', 'description', 'nodes', 'connections', etc.
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    
    -- Position Information (for documentation chunks)
    start_char INTEGER,
    end_char INTEGER,
    word_count INTEGER CHECK (word_count >= 0),
    
    -- Workflow-specific chunk metadata (NULL for documentation)
    node_names JSONB DEFAULT '[]'::jsonb,
    node_types JSONB DEFAULT '[]'::jsonb,
    integrations JSONB DEFAULT '[]'::jsonb,
    
    -- Vector Embeddings
    embedding JSONB,
    embedding_model VARCHAR(128),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Conversation History Table (unchanged from models.py)
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Session Information
    session_id VARCHAR(128) NOT NULL,
    user_id VARCHAR(128),
    
    -- Conversation Content
    user_message TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    
    -- Context and Metadata
    context_documents JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Performance Metrics
    response_time_ms INTEGER CHECK (response_time_ms >= 0),
    token_count INTEGER CHECK (token_count >= 0),
    
    -- User Feedback
    user_feedback VARCHAR(20) CHECK (user_feedback IN ('positive', 'negative', 'neutral')),
    relevance_score FLOAT CHECK (relevance_score >= 0 AND relevance_score <= 1),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- System Metrics Table (unchanged from models.py)
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Metric Information
    metric_name VARCHAR(128) NOT NULL,
    metric_type VARCHAR(32) NOT NULL CHECK (metric_type IN ('counter', 'gauge', 'histogram')),
    
    -- Metric Value
    value FLOAT NOT NULL,
    
    -- Metadata
    labels JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamp
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Audit Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Cache Entries Table (unchanged from models.py)
CREATE TABLE IF NOT EXISTS cache_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Cache Key Information
    cache_key VARCHAR(512) NOT NULL,
    namespace VARCHAR(128) NOT NULL DEFAULT 'default',
    
    -- Cache Data
    data JSONB NOT NULL,
    
    -- Cache Management
    expires_at TIMESTAMP WITH TIME ZONE,
    access_count INTEGER NOT NULL DEFAULT 0 CHECK (access_count >= 0),
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    
    -- Storage Information
    data_size_bytes INTEGER CHECK (data_size_bytes >= 0),
    compression_type VARCHAR(32),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Search Queries Table (unchanged from models.py)
CREATE TABLE IF NOT EXISTS search_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Session Information
    session_id VARCHAR(128),
    user_id VARCHAR(128),
    
    -- Query Information
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64) NOT NULL,
    
    -- Search Configuration
    search_type VARCHAR(32) NOT NULL DEFAULT 'semantic' CHECK (search_type IN ('semantic', 'keyword', 'hybrid')),
    limit_results INTEGER NOT NULL DEFAULT 10 CHECK (limit_results > 0),
    
    -- Results Information
    results_count INTEGER NOT NULL DEFAULT 0 CHECK (results_count >= 0),
    response_time_ms INTEGER CHECK (response_time_ms >= 0),
    
    -- User Interaction
    relevance_scores JSONB DEFAULT '[]'::jsonb,
    user_clicked_results JSONB DEFAULT '[]'::jsonb,
    user_satisfaction VARCHAR(20) CHECK (user_satisfaction IN ('satisfied', 'neutral', 'unsatisfied')),
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create Indexes for Performance

-- Unified Documents Indexes
CREATE INDEX IF NOT EXISTS idx_unified_documents_type ON unified_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_unified_documents_source ON unified_documents(source_type);
CREATE INDEX IF NOT EXISTS idx_unified_documents_category ON unified_documents(category);
CREATE INDEX IF NOT EXISTS idx_unified_documents_subcategory ON unified_documents(subcategory);
CREATE INDEX IF NOT EXISTS idx_unified_documents_title ON unified_documents(title);
CREATE INDEX IF NOT EXISTS idx_unified_documents_content_hash ON unified_documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_unified_documents_workflow_id ON unified_documents(workflow_id) WHERE workflow_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_unified_documents_url ON unified_documents(url) WHERE url IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_unified_documents_file_path ON unified_documents(file_path) WHERE file_path IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_unified_documents_file_name ON unified_documents(file_name) WHERE file_name IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_unified_documents_processed ON unified_documents(is_processed, created_at);
CREATE INDEX IF NOT EXISTS idx_unified_documents_created_at ON unified_documents(created_at);
CREATE INDEX IF NOT EXISTS idx_unified_documents_updated_at ON unified_documents(updated_at);

-- Unified Chunks Indexes
CREATE INDEX IF NOT EXISTS idx_unified_chunks_document_id ON unified_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_unified_chunks_document_chunk ON unified_chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_unified_chunks_type ON unified_chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_unified_chunks_content_hash ON unified_chunks(content_hash);
CREATE INDEX IF NOT EXISTS idx_unified_chunks_created_at ON unified_chunks(created_at);

-- Conversation History Indexes
CREATE INDEX IF NOT EXISTS idx_conversation_history_session ON conversation_history(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_history_user ON conversation_history(user_id, created_at) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_conversation_history_feedback ON conversation_history(user_feedback) WHERE user_feedback IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_conversation_history_created_at ON conversation_history(created_at);

-- System Metrics Indexes
CREATE INDEX IF NOT EXISTS idx_system_metrics_name_timestamp ON system_metrics(metric_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_system_metrics_type_timestamp ON system_metrics(metric_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);

-- Cache Entries Indexes
CREATE INDEX IF NOT EXISTS idx_cache_entries_key_namespace ON cache_entries(cache_key, namespace);
CREATE INDEX IF NOT EXISTS idx_cache_entries_expires_at ON cache_entries(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cache_entries_namespace ON cache_entries(namespace);
CREATE INDEX IF NOT EXISTS idx_cache_entries_last_accessed ON cache_entries(last_accessed_at) WHERE last_accessed_at IS NOT NULL;

-- Search Queries Indexes
CREATE INDEX IF NOT EXISTS idx_search_queries_hash ON search_queries(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_queries_session ON search_queries(session_id, created_at) WHERE session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_search_queries_user ON search_queries(user_id, created_at) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_search_queries_type ON search_queries(search_type);
CREATE INDEX IF NOT EXISTS idx_search_queries_created_at ON search_queries(created_at);

-- Create Unique Constraints
ALTER TABLE unified_documents ADD CONSTRAINT uq_unified_documents_url_hash 
    UNIQUE (url, content_hash) DEFERRABLE INITIALLY DEFERRED;
    
ALTER TABLE unified_documents ADD CONSTRAINT uq_unified_documents_file_path 
    UNIQUE (file_path) DEFERRABLE INITIALLY DEFERRED;
    
ALTER TABLE unified_chunks ADD CONSTRAINT uq_unified_chunks_document_chunk 
    UNIQUE (document_id, chunk_index);
    
ALTER TABLE cache_entries ADD CONSTRAINT uq_cache_entries_key_namespace 
    UNIQUE (cache_key, namespace);

-- Create Functions for Automatic Timestamp Updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create Triggers for Automatic Timestamp Updates
CREATE TRIGGER update_unified_documents_updated_at BEFORE UPDATE ON unified_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_unified_chunks_updated_at BEFORE UPDATE ON unified_chunks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_conversation_history_updated_at BEFORE UPDATE ON conversation_history
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_system_metrics_updated_at BEFORE UPDATE ON system_metrics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_cache_entries_updated_at BEFORE UPDATE ON cache_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_search_queries_updated_at BEFORE UPDATE ON search_queries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create Views for Backward Compatibility

-- View for workflow documents (backward compatibility)
CREATE OR REPLACE VIEW workflow_documents AS
SELECT 
    id,
    workflow_id,
    title AS name,
    description,
    file_path,
    file_name,
    content_hash AS file_hash,
    workflow_data,
    version,
    tags,
    category,
    node_count,
    connection_count,
    trigger_types,
    node_types,
    integrations,
    is_processed,
    processing_error,
    complexity_score,
    completeness_score,
    created_at,
    updated_at
FROM unified_documents
WHERE document_type = 'workflow';

-- View for scraped documents (backward compatibility)
CREATE OR REPLACE VIEW scraped_documents AS
SELECT 
    id,
    url,
    title,
    content_hash,
    content,
    description AS summary,
    metadata,
    word_count,
    language,
    is_processed,
    processing_error,
    quality_score,
    readability_score,
    created_at,
    updated_at
FROM unified_documents
WHERE document_type = 'documentation';

-- View for workflow chunks (backward compatibility)
CREATE OR REPLACE VIEW workflow_chunks AS
SELECT 
    c.id,
    c.document_id AS workflow_id,
    c.chunk_index,
    c.chunk_type,
    c.content,
    c.content_hash,
    c.node_names,
    c.node_types,
    c.integrations,
    c.embedding,
    c.embedding_model,
    c.created_at,
    c.updated_at
FROM unified_chunks c
JOIN unified_documents d ON c.document_id = d.id
WHERE d.document_type = 'workflow';

-- View for document chunks (backward compatibility)
CREATE OR REPLACE VIEW document_chunks AS
SELECT 
    c.id,
    c.document_id,
    c.chunk_index,
    c.content,
    c.content_hash,
    c.start_char,
    c.end_char,
    c.word_count,
    c.embedding,
    c.embedding_model,
    c.created_at,
    c.updated_at
FROM unified_chunks c
JOIN unified_documents d ON c.document_id = d.id
WHERE d.document_type = 'documentation';

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO scraper_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO scraper_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO scraper_user;

COMMIT;