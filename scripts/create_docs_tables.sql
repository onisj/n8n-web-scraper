-- Create documentation tables separate from workflow tables

-- Main documentation table
CREATE TABLE IF NOT EXISTS documentation_pages (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_length INTEGER NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    headings JSONB,
    links JSONB,
    code_blocks JSONB,
    images JSONB,
    metadata JSONB,
    word_count INTEGER,
    scraped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for documentation pages
CREATE INDEX IF NOT EXISTS idx_documentation_pages_category ON documentation_pages(category);
CREATE INDEX IF NOT EXISTS idx_documentation_pages_subcategory ON documentation_pages(subcategory);
CREATE INDEX IF NOT EXISTS idx_documentation_pages_url ON documentation_pages(url);

-- Documentation chunks table for vector search
CREATE TABLE IF NOT EXISTS documentation_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documentation_pages(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_length INTEGER NOT NULL,
    embedding_vector VECTOR(1536),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for documentation chunks
CREATE INDEX IF NOT EXISTS idx_documentation_chunks_document_id ON documentation_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_documentation_chunks_embedding ON documentation_chunks USING ivfflat (embedding_vector vector_cosine_ops);

-- Category-specific tables

-- Integrations documentation
CREATE TABLE IF NOT EXISTS docs_integrations (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documentation_pages(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    headings_count INTEGER,
    links_count INTEGER,
    code_blocks_count INTEGER,
    images_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_docs_integrations_document_id ON docs_integrations(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_integrations_url ON docs_integrations(url);

-- Workflows documentation
CREATE TABLE IF NOT EXISTS docs_workflows (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documentation_pages(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    headings_count INTEGER,
    links_count INTEGER,
    code_blocks_count INTEGER,
    images_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_docs_workflows_document_id ON docs_workflows(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_workflows_url ON docs_workflows(url);

-- Hosting documentation
CREATE TABLE IF NOT EXISTS docs_hosting (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documentation_pages(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    headings_count INTEGER,
    links_count INTEGER,
    code_blocks_count INTEGER,
    images_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_docs_hosting_document_id ON docs_hosting(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_hosting_url ON docs_hosting(url);

-- Release notes documentation
CREATE TABLE IF NOT EXISTS docs_release_notes (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documentation_pages(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    headings_count INTEGER,
    links_count INTEGER,
    code_blocks_count INTEGER,
    images_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_docs_release_notes_document_id ON docs_release_notes(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_release_notes_url ON docs_release_notes(url);

-- User management documentation
CREATE TABLE IF NOT EXISTS docs_user_management (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documentation_pages(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    headings_count INTEGER,
    links_count INTEGER,
    code_blocks_count INTEGER,
    images_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_docs_user_management_document_id ON docs_user_management(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_user_management_url ON docs_user_management(url);

-- API documentation
CREATE TABLE IF NOT EXISTS docs_api (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documentation_pages(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    headings_count INTEGER,
    links_count INTEGER,
    code_blocks_count INTEGER,
    images_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_docs_api_document_id ON docs_api(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_api_url ON docs_api(url);

-- Code documentation
CREATE TABLE IF NOT EXISTS docs_code (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documentation_pages(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    headings_count INTEGER,
    links_count INTEGER,
    code_blocks_count INTEGER,
    images_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_docs_code_document_id ON docs_code(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_code_url ON docs_code(url);

-- Courses documentation
CREATE TABLE IF NOT EXISTS docs_courses (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documentation_pages(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    headings_count INTEGER,
    links_count INTEGER,
    code_blocks_count INTEGER,
    images_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_docs_courses_document_id ON docs_courses(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_courses_url ON docs_courses(url);

-- Advanced AI documentation
CREATE TABLE IF NOT EXISTS docs_advanced_ai (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documentation_pages(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    headings_count INTEGER,
    links_count INTEGER,
    code_blocks_count INTEGER,
    images_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_docs_advanced_ai_document_id ON docs_advanced_ai(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_advanced_ai_url ON docs_advanced_ai(url);

-- Glossary documentation
CREATE TABLE IF NOT EXISTS docs_glossary (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documentation_pages(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    headings_count INTEGER,
    links_count INTEGER,
    code_blocks_count INTEGER,
    images_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_docs_glossary_document_id ON docs_glossary(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_glossary_url ON docs_glossary(url);