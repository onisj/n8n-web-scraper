
-- Base workflow documents table (existing)
CREATE TABLE IF NOT EXISTS workflow_documents (
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

-- Index for category-based queries
CREATE INDEX IF NOT EXISTS idx_workflow_documents_category ON workflow_documents(category);
CREATE INDEX IF NOT EXISTS idx_workflow_documents_subcategory ON workflow_documents(subcategory);
CREATE INDEX IF NOT EXISTS idx_workflow_documents_url ON workflow_documents(url);


-- 1 0 Migration Checklist specific table
CREATE TABLE IF NOT EXISTS docs_1_0_migration_checklist (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_1_0_migration_checklist_document_id ON docs_1_0_migration_checklist(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_1_0_migration_checklist_url ON docs_1_0_migration_checklist(url);


--  Workflows specific table
CREATE TABLE IF NOT EXISTS docs__workflows (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs__workflows_document_id ON docs__workflows(document_id);
CREATE INDEX IF NOT EXISTS idx_docs__workflows_url ON docs__workflows(url);


-- Advanced Ai specific table
CREATE TABLE IF NOT EXISTS docs_advanced_ai (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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


-- Api specific table
CREATE TABLE IF NOT EXISTS docs_api (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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


-- Choose N8N specific table
CREATE TABLE IF NOT EXISTS docs_choose_n8n (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_choose_n8n_document_id ON docs_choose_n8n(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_choose_n8n_url ON docs_choose_n8n(url);


-- Code specific table
CREATE TABLE IF NOT EXISTS docs_code (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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


-- Code Builtin specific table
CREATE TABLE IF NOT EXISTS docs_code_builtin (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_code_builtin_document_id ON docs_code_builtin(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_code_builtin_url ON docs_code_builtin(url);


-- Code Cookbook specific table
CREATE TABLE IF NOT EXISTS docs_code_cookbook (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_code_cookbook_document_id ON docs_code_cookbook(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_code_cookbook_url ON docs_code_cookbook(url);


-- Courses specific table
CREATE TABLE IF NOT EXISTS docs_courses (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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


-- Credentials specific table
CREATE TABLE IF NOT EXISTS docs_credentials (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_credentials_document_id ON docs_credentials(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_credentials_url ON docs_credentials(url);


-- Data specific table
CREATE TABLE IF NOT EXISTS docs_data (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_data_document_id ON docs_data(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_data_url ON docs_data(url);


-- Embed specific table
CREATE TABLE IF NOT EXISTS docs_embed (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_embed_document_id ON docs_embed(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_embed_url ON docs_embed(url);


-- External Secrets specific table
CREATE TABLE IF NOT EXISTS docs_external_secrets (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_external_secrets_document_id ON docs_external_secrets(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_external_secrets_url ON docs_external_secrets(url);


-- Flow Logic specific table
CREATE TABLE IF NOT EXISTS docs_flow_logic (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_flow_logic_document_id ON docs_flow_logic(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_flow_logic_url ON docs_flow_logic(url);


-- Glossary specific table
CREATE TABLE IF NOT EXISTS docs_glossary (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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


-- Help Community specific table
CREATE TABLE IF NOT EXISTS docs_help_community (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_help_community_document_id ON docs_help_community(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_help_community_url ON docs_help_community(url);


-- Hosting specific table
CREATE TABLE IF NOT EXISTS docs_hosting (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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


-- Hosting Architecture specific table
CREATE TABLE IF NOT EXISTS docs_hosting_architecture (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_hosting_architecture_document_id ON docs_hosting_architecture(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_hosting_architecture_url ON docs_hosting_architecture(url);


-- Hosting Configuration specific table
CREATE TABLE IF NOT EXISTS docs_hosting_configuration (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_hosting_configuration_document_id ON docs_hosting_configuration(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_hosting_configuration_url ON docs_hosting_configuration(url);


-- Hosting Installation specific table
CREATE TABLE IF NOT EXISTS docs_hosting_installation (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_hosting_installation_document_id ON docs_hosting_installation(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_hosting_installation_url ON docs_hosting_installation(url);


-- Insights specific table
CREATE TABLE IF NOT EXISTS docs_insights (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_insights_document_id ON docs_insights(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_insights_url ON docs_insights(url);


-- Integrations specific table
CREATE TABLE IF NOT EXISTS docs_integrations (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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


-- Integrations Builtin specific table
CREATE TABLE IF NOT EXISTS docs_integrations_builtin (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_integrations_builtin_document_id ON docs_integrations_builtin(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_integrations_builtin_url ON docs_integrations_builtin(url);


-- Integrations Creating-Nodes specific table
CREATE TABLE IF NOT EXISTS docs_integrations_creating-nodes (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_integrations_creating-nodes_document_id ON docs_integrations_creating-nodes(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_integrations_creating-nodes_url ON docs_integrations_creating-nodes(url);


-- Keyboard Shortcuts specific table
CREATE TABLE IF NOT EXISTS docs_keyboard_shortcuts (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_keyboard_shortcuts_document_id ON docs_keyboard_shortcuts(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_keyboard_shortcuts_url ON docs_keyboard_shortcuts(url);


-- Learning Path specific table
CREATE TABLE IF NOT EXISTS docs_learning_path (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_learning_path_document_id ON docs_learning_path(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_learning_path_url ON docs_learning_path(url);


-- License Key specific table
CREATE TABLE IF NOT EXISTS docs_license_key (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_license_key_document_id ON docs_license_key(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_license_key_url ON docs_license_key(url);


-- Log Streaming specific table
CREATE TABLE IF NOT EXISTS docs_log_streaming (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_log_streaming_document_id ON docs_log_streaming(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_log_streaming_url ON docs_log_streaming(url);


-- Manage Cloud specific table
CREATE TABLE IF NOT EXISTS docs_manage_cloud (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_manage_cloud_document_id ON docs_manage_cloud(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_manage_cloud_url ON docs_manage_cloud(url);


-- Privacy Security specific table
CREATE TABLE IF NOT EXISTS docs_privacy_security (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_privacy_security_document_id ON docs_privacy_security(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_privacy_security_url ON docs_privacy_security(url);


-- Reference specific table
CREATE TABLE IF NOT EXISTS docs_reference (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_reference_document_id ON docs_reference(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_reference_url ON docs_reference(url);


-- Release Notes specific table
CREATE TABLE IF NOT EXISTS docs_release_notes (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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


-- Release Notes Legacy specific table
CREATE TABLE IF NOT EXISTS docs_release_notes_legacy (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_release_notes_legacy_document_id ON docs_release_notes_legacy(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_release_notes_legacy_url ON docs_release_notes_legacy(url);


-- Root specific table
CREATE TABLE IF NOT EXISTS docs_root (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_root_document_id ON docs_root(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_root_url ON docs_root(url);


-- Source Control Environments specific table
CREATE TABLE IF NOT EXISTS docs_source_control_environments (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_source_control_environments_document_id ON docs_source_control_environments(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_source_control_environments_url ON docs_source_control_environments(url);


-- Sustainable Use License specific table
CREATE TABLE IF NOT EXISTS docs_sustainable_use_license (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_sustainable_use_license_document_id ON docs_sustainable_use_license(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_sustainable_use_license_url ON docs_sustainable_use_license(url);


-- Try It Out specific table
CREATE TABLE IF NOT EXISTS docs_try_it_out (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_try_it_out_document_id ON docs_try_it_out(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_try_it_out_url ON docs_try_it_out(url);


-- User Management specific table
CREATE TABLE IF NOT EXISTS docs_user_management (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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


-- Video Courses specific table
CREATE TABLE IF NOT EXISTS docs_video_courses (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_docs_video_courses_document_id ON docs_video_courses(document_id);
CREATE INDEX IF NOT EXISTS idx_docs_video_courses_url ON docs_video_courses(url);


-- Workflows specific table
CREATE TABLE IF NOT EXISTS docs_workflows (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES workflow_documents(id) ON DELETE CASCADE,
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
