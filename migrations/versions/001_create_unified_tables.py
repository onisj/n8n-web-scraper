"""Create unified tables

Revision ID: 001
Revises: 
Create Date: 2025-06-30 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create unified_documents table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS unified_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_type VARCHAR(32) NOT NULL,
            source_type VARCHAR(32) NOT NULL,
            url TEXT,
            file_path TEXT,
            workflow_id VARCHAR(255),
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            word_count INTEGER,
            char_count INTEGER,
            language VARCHAR(10),
            category VARCHAR(100),
            subcategory VARCHAR(100),
            tags TEXT[],
            node_names JSONB,
            node_types JSONB,
            integrations JSONB,
            headings JSONB,
            links JSONB,
            code_blocks JSONB,
            images JSONB,
            headings_count INTEGER,
            links_count INTEGER,
            code_blocks_count INTEGER,
            images_count INTEGER,
            is_processed BOOLEAN NOT NULL DEFAULT FALSE,
            processing_error TEXT,
            quality_score DOUBLE PRECISION,
            complexity_score DOUBLE PRECISION,
            completeness_score DOUBLE PRECISION,
            readability_score DOUBLE PRECISION,
            document_metadata JSONB DEFAULT '{}',
            scraped_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create unified_chunks table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS unified_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_type VARCHAR NOT NULL,
            content TEXT NOT NULL,
            content_hash VARCHAR NOT NULL,
            start_char INTEGER,
            end_char INTEGER,
            word_count INTEGER,
            node_names JSONB,
            node_types JSONB,
            integrations JSONB,
            embedding JSONB,
            embedding_model VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES unified_documents(id) ON DELETE CASCADE
        )
    """)
    
    # Create cache_entries table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS cache_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cache_key VARCHAR NOT NULL,
            namespace VARCHAR NOT NULL,
            data JSONB NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE,
            access_count INTEGER NOT NULL DEFAULT 0,
            last_accessed_at TIMESTAMP WITH TIME ZONE,
            data_size_bytes INTEGER,
            compression_type VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cache_key, namespace)
        )
    """)
    
    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_documents_category ON unified_documents(category)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_documents_subcategory ON unified_documents(subcategory)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_documents_url ON unified_documents(url)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_documents_file_path ON unified_documents(file_path)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_documents_workflow_id ON unified_documents(workflow_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_documents_title ON unified_documents(title)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_documents_content_hash ON unified_documents(content_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_documents_is_processed ON unified_documents(is_processed)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_documents_created_at ON unified_documents(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_documents_updated_at ON unified_documents(updated_at)")
    
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_chunks_document_id ON unified_chunks(document_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_chunks_chunk_type ON unified_chunks(chunk_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_chunks_content_hash ON unified_chunks(content_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_chunks_created_at ON unified_chunks(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_unified_chunks_updated_at ON unified_chunks(updated_at)")
    
    op.execute("CREATE INDEX IF NOT EXISTS ix_cache_entries_cache_key ON cache_entries(cache_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cache_entries_namespace ON cache_entries(namespace)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cache_entries_expires_at ON cache_entries(expires_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cache_entries_last_accessed_at ON cache_entries(last_accessed_at)")


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('unified_chunks')
    op.drop_table('cache_entries')
    op.drop_table('unified_documents')