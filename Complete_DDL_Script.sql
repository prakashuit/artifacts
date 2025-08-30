-- =====================================================
-- Document Ingestion Pipeline - Complete DDL Script
-- =====================================================
-- Version: 1.0
-- Date: 2025-08-30
-- Description: Complete database schema for Document Ingestion Pipeline
-- =====================================================

-- Drop tables in reverse dependency order (if they exist)
DROP TABLE IF EXISTS evaluation_runs CASCADE;
DROP TABLE IF EXISTS extraction_runs CASCADE;
DROP TABLE IF EXISTS prompts CASCADE;
DROP TABLE IF EXISTS templates CASCADE;
DROP TABLE IF EXISTS use_cases CASCADE;
DROP TABLE IF EXISTS namespaces CASCADE;

-- =====================================================
-- 1. NAMESPACES TABLE
-- =====================================================
CREATE TABLE namespaces (
    namespace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}',

    -- Constraints
    CONSTRAINT chk_namespace_name_length CHECK (LENGTH(name) >= 3),
    CONSTRAINT chk_namespace_created_by_length CHECK (LENGTH(created_by) >= 1)
);

-- Indexes for namespaces
CREATE INDEX idx_namespaces_name ON namespaces(name);
CREATE INDEX idx_namespaces_created_by ON namespaces(created_by);
CREATE INDEX idx_namespaces_is_active ON namespaces(is_active);
CREATE INDEX idx_namespaces_created_at ON namespaces(created_at);

-- =====================================================
-- 2. USE_CASES TABLE
-- =====================================================
CREATE TABLE use_cases (
    usecase_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner VARCHAR(255) NOT NULL,
    ingestion_type VARCHAR(50) NOT NULL,
    ingestion_config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',

    -- Foreign Key Constraints
    CONSTRAINT fk_usecase_namespace FOREIGN KEY (namespace_id) 
        REFERENCES namespaces(namespace_id) ON DELETE CASCADE,

    -- Check Constraints
    CONSTRAINT chk_usecase_name_length CHECK (LENGTH(name) >= 3),
    CONSTRAINT chk_usecase_owner_length CHECK (LENGTH(owner) >= 1),
    CONSTRAINT chk_usecase_ingestion_type CHECK (
        ingestion_type IN ('pdf', 'image', 'document', 'form', 'invoice', 'contract', 'other')
    ),

    -- Unique constraint for name within namespace
    CONSTRAINT uk_usecase_name_namespace UNIQUE (namespace_id, name)
);

-- Indexes for use_cases
CREATE INDEX idx_use_cases_namespace_id ON use_cases(namespace_id);
CREATE INDEX idx_use_cases_name ON use_cases(name);
CREATE INDEX idx_use_cases_owner ON use_cases(owner);
CREATE INDEX idx_use_cases_ingestion_type ON use_cases(ingestion_type);
CREATE INDEX idx_use_cases_is_active ON use_cases(is_active);
CREATE INDEX idx_use_cases_created_at ON use_cases(created_at);

-- =====================================================
-- 3. TEMPLATES TABLE
-- =====================================================
CREATE TABLE templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usecase_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sample_pdf_uri VARCHAR(1000),
    ground_truth_uri VARCHAR(1000),
    schema_definition JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    version_number INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}',

    -- Foreign Key Constraints
    CONSTRAINT fk_template_usecase FOREIGN KEY (usecase_id) 
        REFERENCES use_cases(usecase_id) ON DELETE CASCADE,

    -- Check Constraints
    CONSTRAINT chk_template_name_length CHECK (LENGTH(name) >= 3),
    CONSTRAINT chk_template_version_positive CHECK (version_number > 0),
    CONSTRAINT chk_template_sample_pdf_uri_format CHECK (
        sample_pdf_uri IS NULL OR 
        sample_pdf_uri ~ '^https?://.*\.(pdf|PDF)$'
    ),
    CONSTRAINT chk_template_ground_truth_uri_format CHECK (
        ground_truth_uri IS NULL OR 
        ground_truth_uri ~ '^https?://.*\.(json|JSON)$'
    ),

    -- Unique constraint for name within use case
    CONSTRAINT uk_template_name_usecase UNIQUE (usecase_id, name)
);

-- Indexes for templates
CREATE INDEX idx_templates_usecase_id ON templates(usecase_id);
CREATE INDEX idx_templates_name ON templates(name);
CREATE INDEX idx_templates_is_active ON templates(is_active);
CREATE INDEX idx_templates_version_number ON templates(version_number);
CREATE INDEX idx_templates_created_at ON templates(created_at);

-- =====================================================
-- 4. PROMPTS TABLE
-- =====================================================
CREATE TABLE prompts (
    prompt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    prompt_text TEXT NOT NULL,
    version_number INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    prompt_type VARCHAR(50) DEFAULT 'extraction',
    model_config JSONB DEFAULT '{}',

    -- Foreign Key Constraints
    CONSTRAINT fk_prompt_template FOREIGN KEY (template_id) 
        REFERENCES templates(template_id) ON DELETE CASCADE,

    -- Check Constraints
    CONSTRAINT chk_prompt_name_length CHECK (LENGTH(name) >= 3),
    CONSTRAINT chk_prompt_text_length CHECK (LENGTH(prompt_text) >= 10),
    CONSTRAINT chk_prompt_version_positive CHECK (version_number > 0),
    CONSTRAINT chk_prompt_created_by_length CHECK (LENGTH(created_by) >= 1),
    CONSTRAINT chk_prompt_type CHECK (
        prompt_type IN ('extraction', 'validation', 'enhancement', 'classification')
    ),

    -- Unique constraint for name within template
    CONSTRAINT uk_prompt_name_template UNIQUE (template_id, name, version_number)
);

-- Indexes for prompts
CREATE INDEX idx_prompts_template_id ON prompts(template_id);
CREATE INDEX idx_prompts_name ON prompts(name);
CREATE INDEX idx_prompts_is_active ON prompts(is_active);
CREATE INDEX idx_prompts_version_number ON prompts(version_number);
CREATE INDEX idx_prompts_created_by ON prompts(created_by);
CREATE INDEX idx_prompts_prompt_type ON prompts(prompt_type);
CREATE INDEX idx_prompts_created_at ON prompts(created_at);

-- =====================================================
-- 5. EXTRACTION_RUNS TABLE
-- =====================================================
CREATE TABLE extraction_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL,
    prompt_id UUID NOT NULL,
    input_document_uri VARCHAR(1000) NOT NULL,
    extracted_json_uri VARCHAR(1000),
    extraction_metadata JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    processing_time_ms INTEGER,
    model_used VARCHAR(100),
    confidence_score DECIMAL(5,4),
    retry_count INTEGER DEFAULT 0,
    created_by VARCHAR(255) NOT NULL,

    -- Foreign Key Constraints
    CONSTRAINT fk_extraction_run_template FOREIGN KEY (template_id) 
        REFERENCES templates(template_id) ON DELETE CASCADE,
    CONSTRAINT fk_extraction_run_prompt FOREIGN KEY (prompt_id) 
        REFERENCES prompts(prompt_id) ON DELETE CASCADE,

    -- Check Constraints
    CONSTRAINT chk_extraction_run_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'cancelled')
    ),
    CONSTRAINT chk_extraction_run_processing_time CHECK (
        processing_time_ms IS NULL OR processing_time_ms >= 0
    ),
    CONSTRAINT chk_extraction_run_confidence_score CHECK (
        confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)
    ),
    CONSTRAINT chk_extraction_run_retry_count CHECK (retry_count >= 0),
    CONSTRAINT chk_extraction_run_completed_after_started CHECK (
        completed_at IS NULL OR completed_at >= started_at
    ),
    CONSTRAINT chk_extraction_run_input_document_uri_format CHECK (
        input_document_uri ~ '^https?://.*'
    ),
    CONSTRAINT chk_extraction_run_extracted_json_uri_format CHECK (
        extracted_json_uri IS NULL OR 
        extracted_json_uri ~ '^https?://.*\.(json|JSON)$'
    )
);

-- Indexes for extraction_runs
CREATE INDEX idx_extraction_runs_template_id ON extraction_runs(template_id);
CREATE INDEX idx_extraction_runs_prompt_id ON extraction_runs(prompt_id);
CREATE INDEX idx_extraction_runs_status ON extraction_runs(status);
CREATE INDEX idx_extraction_runs_started_at ON extraction_runs(started_at);
CREATE INDEX idx_extraction_runs_completed_at ON extraction_runs(completed_at);
CREATE INDEX idx_extraction_runs_created_by ON extraction_runs(created_by);
CREATE INDEX idx_extraction_runs_model_used ON extraction_runs(model_used);
CREATE INDEX idx_extraction_runs_confidence_score ON extraction_runs(confidence_score);

-- =====================================================
-- 6. EVALUATION_RUNS TABLE
-- =====================================================
CREATE TABLE evaluation_runs (
    eval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_run_id UUID NOT NULL,
    accuracy DECIMAL(5,4),
    precision_score DECIMAL(5,4),
    recall_score DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    field_level_metrics JSONB DEFAULT '{}',
    mismatched_fields JSONB DEFAULT '[]',
    evaluation_summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    evaluation_metadata JSONB DEFAULT '{}',
    evaluator_type VARCHAR(50) DEFAULT 'automated',
    ground_truth_version VARCHAR(50),
    total_fields_evaluated INTEGER,
    correctly_extracted_fields INTEGER,

    -- Foreign Key Constraints
    CONSTRAINT fk_evaluation_run_extraction_run FOREIGN KEY (extraction_run_id) 
        REFERENCES extraction_runs(run_id) ON DELETE CASCADE,

    -- Check Constraints
    CONSTRAINT chk_evaluation_run_accuracy CHECK (
        accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 1)
    ),
    CONSTRAINT chk_evaluation_run_precision CHECK (
        precision_score IS NULL OR (precision_score >= 0 AND precision_score <= 1)
    ),
    CONSTRAINT chk_evaluation_run_recall CHECK (
        recall_score IS NULL OR (recall_score >= 0 AND recall_score <= 1)
    ),
    CONSTRAINT chk_evaluation_run_f1 CHECK (
        f1_score IS NULL OR (f1_score >= 0 AND f1_score <= 1)
    ),
    CONSTRAINT chk_evaluation_run_evaluator_type CHECK (
        evaluator_type IN ('automated', 'manual', 'hybrid')
    ),
    CONSTRAINT chk_evaluation_run_total_fields CHECK (
        total_fields_evaluated IS NULL OR total_fields_evaluated >= 0
    ),
    CONSTRAINT chk_evaluation_run_correct_fields CHECK (
        correctly_extracted_fields IS NULL OR correctly_extracted_fields >= 0
    ),
    CONSTRAINT chk_evaluation_run_correct_vs_total CHECK (
        total_fields_evaluated IS NULL OR 
        correctly_extracted_fields IS NULL OR 
        correctly_extracted_fields <= total_fields_evaluated
    )
);

-- Indexes for evaluation_runs
CREATE INDEX idx_evaluation_runs_extraction_run_id ON evaluation_runs(extraction_run_id);
CREATE INDEX idx_evaluation_runs_accuracy ON evaluation_runs(accuracy);
CREATE INDEX idx_evaluation_runs_precision_score ON evaluation_runs(precision_score);
CREATE INDEX idx_evaluation_runs_recall_score ON evaluation_runs(recall_score);
CREATE INDEX idx_evaluation_runs_f1_score ON evaluation_runs(f1_score);
CREATE INDEX idx_evaluation_runs_created_at ON evaluation_runs(created_at);
CREATE INDEX idx_evaluation_runs_evaluator_type ON evaluation_runs(evaluator_type);

-- =====================================================
-- TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_namespaces_updated_at 
    BEFORE UPDATE ON namespaces 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_use_cases_updated_at 
    BEFORE UPDATE ON use_cases 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_templates_updated_at 
    BEFORE UPDATE ON templates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prompts_updated_at 
    BEFORE UPDATE ON prompts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================

-- View: Complete extraction run details with related information
CREATE VIEW v_extraction_run_details AS
SELECT 
    er.run_id,
    er.status,
    er.started_at,
    er.completed_at,
    er.processing_time_ms,
    er.confidence_score,
    er.model_used,
    n.name as namespace_name,
    uc.name as usecase_name,
    t.name as template_name,
    p.name as prompt_name,
    p.version_number as prompt_version,
    er.input_document_uri,
    er.extracted_json_uri,
    er.created_by
FROM extraction_runs er
JOIN templates t ON er.template_id = t.template_id
JOIN prompts p ON er.prompt_id = p.prompt_id
JOIN use_cases uc ON t.usecase_id = uc.usecase_id
JOIN namespaces n ON uc.namespace_id = n.namespace_id;

-- View: Evaluation metrics summary
CREATE VIEW v_evaluation_metrics_summary AS
SELECT 
    n.name as namespace_name,
    uc.name as usecase_name,
    t.name as template_name,
    COUNT(er.run_id) as total_runs,
    AVG(ev.accuracy) as avg_accuracy,
    AVG(ev.precision_score) as avg_precision,
    AVG(ev.recall_score) as avg_recall,
    AVG(ev.f1_score) as avg_f1_score,
    MAX(ev.created_at) as last_evaluation_date
FROM namespaces n
JOIN use_cases uc ON n.namespace_id = uc.namespace_id
JOIN templates t ON uc.usecase_id = t.usecase_id
JOIN extraction_runs er ON t.template_id = er.template_id
LEFT JOIN evaluation_runs ev ON er.run_id = ev.extraction_run_id
WHERE er.status = 'completed'
GROUP BY n.namespace_id, n.name, uc.usecase_id, uc.name, t.template_id, t.name;

-- View: Active prompts with template information
CREATE VIEW v_active_prompts AS
SELECT 
    p.prompt_id,
    p.name as prompt_name,
    p.version_number,
    p.prompt_type,
    p.created_by,
    p.created_at,
    t.name as template_name,
    uc.name as usecase_name,
    n.name as namespace_name
FROM prompts p
JOIN templates t ON p.template_id = t.template_id
JOIN use_cases uc ON t.usecase_id = uc.usecase_id
JOIN namespaces n ON uc.namespace_id = n.namespace_id
WHERE p.is_active = TRUE
ORDER BY n.name, uc.name, t.name, p.name, p.version_number DESC;

-- =====================================================
-- SAMPLE DATA INSERTION (OPTIONAL)
-- =====================================================

-- Insert sample namespace
INSERT INTO namespaces (name, description, created_by) VALUES 
('finance_documents', 'Financial document processing namespace', 'admin');

-- Insert sample use case
INSERT INTO use_cases (namespace_id, name, description, owner, ingestion_type) 
SELECT namespace_id, 'invoice_processing', 'Process and extract data from invoices', 'finance_team', 'invoice'
FROM namespaces WHERE name = 'finance_documents';

-- Insert sample template
INSERT INTO templates (usecase_id, name, description, schema_definition)
SELECT usecase_id, 'standard_invoice', 'Standard invoice template', 
'{"fields": ["invoice_number", "date", "amount", "vendor", "line_items"]}'::jsonb
FROM use_cases WHERE name = 'invoice_processing';

-- Insert sample prompt
INSERT INTO prompts (template_id, name, prompt_text, created_by)
SELECT template_id, 'extract_invoice_data', 
'Extract the following fields from the invoice: invoice number, date, total amount, vendor name, and line items with descriptions and amounts.',
'admin'
FROM templates WHERE name = 'standard_invoice';

-- =====================================================
-- PERFORMANCE OPTIMIZATION QUERIES
-- =====================================================

-- Analyze tables for query optimization
ANALYZE namespaces;
ANALYZE use_cases;
ANALYZE templates;
ANALYZE prompts;
ANALYZE extraction_runs;
ANALYZE evaluation_runs;

-- =====================================================
-- SECURITY AND PERMISSIONS (OPTIONAL)
-- =====================================================

-- Create roles (uncomment if needed)
-- CREATE ROLE doc_ingestion_admin;
-- CREATE ROLE doc_ingestion_user;
-- CREATE ROLE doc_ingestion_readonly;

-- Grant permissions (uncomment if needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO doc_ingestion_admin;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO doc_ingestion_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO doc_ingestion_readonly;

-- =====================================================
-- SCRIPT COMPLETION
-- =====================================================

SELECT 'Document Ingestion Pipeline DDL Script completed successfully!' as status;
SELECT 'Total tables created: 6' as table_count;
SELECT 'Total indexes created: ' || COUNT(*) as index_count 
FROM pg_indexes WHERE schemaname = 'public' 
AND tablename IN ('namespaces', 'use_cases', 'templates', 'prompts', 'extraction_runs', 'evaluation_runs');

-- =====================================================
-- END OF DDL SCRIPT
-- =====================================================
