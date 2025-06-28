-- Fix foreign key constraints to point to documentation_pages instead of workflow_documents

-- Drop all existing foreign key constraints
ALTER TABLE docs_integrations DROP CONSTRAINT IF EXISTS docs_integrations_document_id_fkey;
ALTER TABLE docs_workflows DROP CONSTRAINT IF EXISTS docs_workflows_document_id_fkey;
ALTER TABLE docs_hosting DROP CONSTRAINT IF EXISTS docs_hosting_document_id_fkey;
ALTER TABLE docs_release_notes DROP CONSTRAINT IF EXISTS docs_release_notes_document_id_fkey;
ALTER TABLE docs_user_management DROP CONSTRAINT IF EXISTS docs_user_management_document_id_fkey;
ALTER TABLE docs_api DROP CONSTRAINT IF EXISTS docs_api_document_id_fkey;
ALTER TABLE docs_code DROP CONSTRAINT IF EXISTS docs_code_document_id_fkey;
ALTER TABLE docs_courses DROP CONSTRAINT IF EXISTS docs_courses_document_id_fkey;
ALTER TABLE docs_advanced_ai DROP CONSTRAINT IF EXISTS docs_advanced_ai_document_id_fkey;
ALTER TABLE docs_glossary DROP CONSTRAINT IF EXISTS docs_glossary_document_id_fkey;

-- Add new foreign key constraints pointing to documentation_pages
ALTER TABLE docs_integrations ADD CONSTRAINT docs_integrations_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;
    
ALTER TABLE docs_workflows ADD CONSTRAINT docs_workflows_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;
    
ALTER TABLE docs_hosting ADD CONSTRAINT docs_hosting_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;
    
ALTER TABLE docs_release_notes ADD CONSTRAINT docs_release_notes_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;
    
ALTER TABLE docs_user_management ADD CONSTRAINT docs_user_management_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;
    
ALTER TABLE docs_api ADD CONSTRAINT docs_api_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;
    
ALTER TABLE docs_code ADD CONSTRAINT docs_code_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;
    
ALTER TABLE docs_courses ADD CONSTRAINT docs_courses_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;
    
ALTER TABLE docs_advanced_ai ADD CONSTRAINT docs_advanced_ai_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;
    
ALTER TABLE docs_glossary ADD CONSTRAINT docs_glossary_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

-- Also drop and recreate constraints for other category tables that might exist
ALTER TABLE docs_1_0_migration_checklist DROP CONSTRAINT IF EXISTS docs_1_0_migration_checklist_document_id_fkey;
ALTER TABLE docs_1_0_migration_checklist ADD CONSTRAINT docs_1_0_migration_checklist_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_external_secrets DROP CONSTRAINT IF EXISTS docs_external_secrets_document_id_fkey;
ALTER TABLE docs_external_secrets ADD CONSTRAINT docs_external_secrets_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_insights DROP CONSTRAINT IF EXISTS docs_insights_document_id_fkey;
ALTER TABLE docs_insights ADD CONSTRAINT docs_insights_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_keyboard_shortcuts DROP CONSTRAINT IF EXISTS docs_keyboard_shortcuts_document_id_fkey;
ALTER TABLE docs_keyboard_shortcuts ADD CONSTRAINT docs_keyboard_shortcuts_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_learning_path DROP CONSTRAINT IF EXISTS docs_learning_path_document_id_fkey;
ALTER TABLE docs_learning_path ADD CONSTRAINT docs_learning_path_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_license_key DROP CONSTRAINT IF EXISTS docs_license_key_document_id_fkey;
ALTER TABLE docs_license_key ADD CONSTRAINT docs_license_key_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_log_streaming DROP CONSTRAINT IF EXISTS docs_log_streaming_document_id_fkey;
ALTER TABLE docs_log_streaming ADD CONSTRAINT docs_log_streaming_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_privacy_security DROP CONSTRAINT IF EXISTS docs_privacy_security_document_id_fkey;
ALTER TABLE docs_privacy_security ADD CONSTRAINT docs_privacy_security_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_reference DROP CONSTRAINT IF EXISTS docs_reference_document_id_fkey;
ALTER TABLE docs_reference ADD CONSTRAINT docs_reference_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_release_notes_legacy DROP CONSTRAINT IF EXISTS docs_release_notes_legacy_document_id_fkey;
ALTER TABLE docs_release_notes_legacy ADD CONSTRAINT docs_release_notes_legacy_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_root DROP CONSTRAINT IF EXISTS docs_root_document_id_fkey;
ALTER TABLE docs_root ADD CONSTRAINT docs_root_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_source_control_environments DROP CONSTRAINT IF EXISTS docs_source_control_environments_document_id_fkey;
ALTER TABLE docs_source_control_environments ADD CONSTRAINT docs_source_control_environments_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_sustainable_use_license DROP CONSTRAINT IF EXISTS docs_sustainable_use_license_document_id_fkey;
ALTER TABLE docs_sustainable_use_license ADD CONSTRAINT docs_sustainable_use_license_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_try_it_out DROP CONSTRAINT IF EXISTS docs_try_it_out_document_id_fkey;
ALTER TABLE docs_try_it_out ADD CONSTRAINT docs_try_it_out_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs_video_courses DROP CONSTRAINT IF EXISTS docs_video_courses_document_id_fkey;
ALTER TABLE docs_video_courses ADD CONSTRAINT docs_video_courses_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;

ALTER TABLE docs__workflows DROP CONSTRAINT IF EXISTS docs__workflows_document_id_fkey;
ALTER TABLE docs__workflows ADD CONSTRAINT docs__workflows_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documentation_pages(id) ON DELETE CASCADE;