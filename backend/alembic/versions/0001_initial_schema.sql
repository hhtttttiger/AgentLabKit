--
-- PostgreSQL database dump
--


-- Dumped from database version 16.14 (Debian 16.14-1.pgdg12+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS '';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_catalog_revisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_catalog_revisions (
    id bigint NOT NULL,
    revision bigint NOT NULL,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: agent_catalog_revisions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_catalog_revisions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_catalog_revisions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_catalog_revisions_id_seq OWNED BY public.agent_catalog_revisions.id;


--
-- Name: agent_definition_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_definition_versions (
    id bigint NOT NULL,
    agent_id bigint NOT NULL,
    version_number bigint NOT NULL,
    system_prompt text,
    model_binding_key character varying(128),
    temperature double precision,
    max_tokens integer,
    response_format character varying(32),
    extra_json jsonb DEFAULT '{}'::jsonb,
    checksum character varying(64),
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: agent_definition_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_definition_versions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_definition_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_definition_versions_id_seq OWNED BY public.agent_definition_versions.id;


--
-- Name: agent_definitions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_definitions (
    id bigint NOT NULL,
    agent_key character varying(128) NOT NULL,
    display_name character varying(256) NOT NULL,
    description character varying(1024),
    icon character varying(64),
    tags_json jsonb DEFAULT '[]'::jsonb,
    is_enabled boolean DEFAULT true,
    published_version bigint,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: agent_definitions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_definitions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_definitions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_definitions_id_seq OWNED BY public.agent_definitions.id;


--
-- Name: agent_execution_audits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_execution_audits (
    id bigint NOT NULL,
    agent_key character varying(128) NOT NULL,
    run_id character varying(128) NOT NULL,
    agent_version bigint,
    input_summary text,
    output_summary text,
    tool_calls_json jsonb DEFAULT '[]'::jsonb,
    status character varying(32) DEFAULT 'success'::character varying,
    duration_ms bigint,
    token_usage_json jsonb DEFAULT '{}'::jsonb,
    error_message text,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: agent_execution_audits_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_execution_audits_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_execution_audits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_execution_audits_id_seq OWNED BY public.agent_execution_audits.id;


--
-- Name: agent_knowledge_base_bindings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_knowledge_base_bindings (
    id bigint NOT NULL,
    agent_version_id bigint NOT NULL,
    knowledge_base_id bigint NOT NULL,
    is_enabled boolean DEFAULT true,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: agent_knowledge_base_bindings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_knowledge_base_bindings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_knowledge_base_bindings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_knowledge_base_bindings_id_seq OWNED BY public.agent_knowledge_base_bindings.id;


--
-- Name: agent_mcp_bindings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_mcp_bindings (
    id bigint NOT NULL,
    agent_version_id bigint NOT NULL,
    server_name character varying(128) NOT NULL,
    is_enabled boolean DEFAULT true,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: agent_mcp_bindings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_mcp_bindings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_mcp_bindings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_mcp_bindings_id_seq OWNED BY public.agent_mcp_bindings.id;


--
-- Name: agent_mcp_servers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_mcp_servers (
    id bigint NOT NULL,
    name character varying(128) NOT NULL,
    display_name character varying(256) NOT NULL,
    transport_type character varying(32) NOT NULL,
    url character varying(1024),
    headers_json jsonb DEFAULT '{}'::jsonb,
    is_enabled boolean DEFAULT true,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: agent_mcp_servers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_mcp_servers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_mcp_servers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_mcp_servers_id_seq OWNED BY public.agent_mcp_servers.id;


--
-- Name: agent_skill_bindings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_skill_bindings (
    id bigint NOT NULL,
    agent_version_id bigint NOT NULL,
    skill_key character varying(128) NOT NULL,
    is_enabled boolean DEFAULT true,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: agent_skill_bindings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_skill_bindings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_skill_bindings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_skill_bindings_id_seq OWNED BY public.agent_skill_bindings.id;


--
-- Name: agent_skills; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_skills (
    id bigint NOT NULL,
    skill_key character varying(128) NOT NULL,
    display_name character varying(256) NOT NULL,
    description character varying(1024),
    content text NOT NULL,
    is_published boolean DEFAULT false,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: agent_skills_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_skills_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_skills_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_skills_id_seq OWNED BY public.agent_skills.id;


--
-- Name: agent_tool_bindings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_tool_bindings (
    id bigint NOT NULL,
    agent_version_id bigint NOT NULL,
    tool_name character varying(128) NOT NULL,
    is_enabled boolean DEFAULT true,
    extra_json jsonb DEFAULT '{}'::jsonb,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: agent_tool_bindings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_tool_bindings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_tool_bindings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_tool_bindings_id_seq OWNED BY public.agent_tool_bindings.id;


--
-- Name: agent_tools; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_tools (
    id bigint NOT NULL,
    tool_name character varying(128) NOT NULL,
    display_name character varying(256) NOT NULL,
    description character varying(1024),
    parameters_json jsonb DEFAULT '{}'::jsonb,
    source character varying(32) DEFAULT 'external'::character varying,
    is_enabled boolean DEFAULT true,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: agent_tools_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_tools_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_tools_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_tools_id_seq OWNED BY public.agent_tools.id;



--
-- Name: auth_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_users (
    id bigint NOT NULL,
    username character varying(256) NOT NULL,
    password_hash character varying(512) NOT NULL,
    display_name character varying(256),
    is_active boolean DEFAULT true,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: auth_users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.auth_users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.auth_users_id_seq OWNED BY public.auth_users.id;


--
-- Name: cost_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cost_alerts (
    id bigint NOT NULL,
    budget_id bigint NOT NULL,
    alert_type character varying(32) NOT NULL,
    current_spend_usd double precision NOT NULL,
    threshold_usd double precision NOT NULL,
    triggered_at_utc timestamp with time zone DEFAULT now(),
    acknowledged_at_utc timestamp with time zone,
    created_at_utc timestamp with time zone DEFAULT now(),
    updated_at_utc timestamp with time zone DEFAULT now()
);


--
-- Name: cost_alerts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cost_alerts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cost_alerts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cost_alerts_id_seq OWNED BY public.cost_alerts.id;


--
-- Name: cost_budgets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cost_budgets (
    id bigint NOT NULL,
    scope_type character varying(32) NOT NULL,
    scope_key character varying(128) DEFAULT '*'::character varying NOT NULL,
    monthly_limit_usd double precision DEFAULT '0'::double precision NOT NULL,
    alert_threshold_pct double precision DEFAULT '80'::double precision NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    extra_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at_utc timestamp with time zone DEFAULT now(),
    updated_at_utc timestamp with time zone DEFAULT now()
);


--
-- Name: cost_budgets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cost_budgets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cost_budgets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cost_budgets_id_seq OWNED BY public.cost_budgets.id;


--
-- Name: document_indexes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_indexes (
    id bigint NOT NULL,
    knowledge_base_id bigint NOT NULL,
    index_name character varying(128) NOT NULL,
    index_type character varying(64) NOT NULL,
    config_json jsonb DEFAULT '{}'::jsonb,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now(),
    document_id bigint,
    status character varying(32) DEFAULT 'pending'::character varying,
    stats_json jsonb DEFAULT '{}'::jsonb,
    built_at_utc timestamp without time zone
);


--
-- Name: document_indexes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_indexes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_indexes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_indexes_id_seq OWNED BY public.document_indexes.id;


--
-- Name: document_processing_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_processing_jobs (
    id bigint NOT NULL,
    document_id bigint NOT NULL,
    job_type character varying(64) NOT NULL,
    status character varying(32) DEFAULT 'pending'::character varying,
    error_message text,
    started_at_utc timestamp without time zone,
    completed_at_utc timestamp without time zone,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now(),
    current_stage character varying(64),
    stage_progress_json jsonb,
    CONSTRAINT chk_job_status CHECK (((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('running'::character varying)::text, ('completed'::character varying)::text, ('failed'::character varying)::text])))
);


--
-- Name: document_processing_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_processing_jobs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_processing_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_processing_jobs_id_seq OWNED BY public.document_processing_jobs.id;


--
-- Name: document_segments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_segments (
    id bigint NOT NULL,
    document_id bigint NOT NULL,
    segment_index integer NOT NULL,
    content text NOT NULL,
    extra_json jsonb DEFAULT '{}'::jsonb,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: document_segments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.document_segments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: document_segments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.document_segments_id_seq OWNED BY public.document_segments.id;


--
-- Name: eval_cases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eval_cases (
    id bigint NOT NULL,
    dataset_id bigint NOT NULL,
    case_index integer NOT NULL,
    input_text text NOT NULL,
    expected_output text,
    context_json jsonb DEFAULT '[]'::jsonb NOT NULL,
    tags_json jsonb DEFAULT '[]'::jsonb NOT NULL,
    metadata_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at_utc timestamp with time zone DEFAULT now(),
    updated_at_utc timestamp with time zone DEFAULT now()
);


--
-- Name: eval_cases_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.eval_cases_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: eval_cases_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.eval_cases_id_seq OWNED BY public.eval_cases.id;


--
-- Name: eval_datasets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eval_datasets (
    id bigint NOT NULL,
    name character varying(256) NOT NULL,
    description character varying(1024),
    tags_json jsonb DEFAULT '[]'::jsonb NOT NULL,
    case_count integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at_utc timestamp with time zone DEFAULT now(),
    updated_at_utc timestamp with time zone DEFAULT now()
);


--
-- Name: eval_datasets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.eval_datasets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: eval_datasets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.eval_datasets_id_seq OWNED BY public.eval_datasets.id;


--
-- Name: eval_run_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eval_run_configs (
    id bigint NOT NULL,
    name character varying(256) NOT NULL,
    dataset_id bigint NOT NULL,
    target_type character varying(32) DEFAULT 'agent'::character varying NOT NULL,
    target_key character varying(128) DEFAULT ''::character varying NOT NULL,
    metric_configs_json jsonb DEFAULT '[]'::jsonb NOT NULL,
    judge_model_binding_key character varying(128) DEFAULT ''::character varying NOT NULL,
    created_at_utc timestamp with time zone DEFAULT now(),
    updated_at_utc timestamp with time zone DEFAULT now()
);


--
-- Name: eval_run_configs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.eval_run_configs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: eval_run_configs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.eval_run_configs_id_seq OWNED BY public.eval_run_configs.id;


--
-- Name: eval_run_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eval_run_results (
    id bigint NOT NULL,
    run_id bigint NOT NULL,
    case_id bigint NOT NULL,
    actual_output text DEFAULT ''::text NOT NULL,
    metric_results_json jsonb DEFAULT '[]'::jsonb NOT NULL,
    overall_score double precision DEFAULT '0'::double precision NOT NULL,
    error_message text,
    duration_ms bigint DEFAULT '0'::bigint NOT NULL,
    created_at_utc timestamp with time zone DEFAULT now(),
    updated_at_utc timestamp with time zone DEFAULT now()
);


--
-- Name: eval_run_results_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.eval_run_results_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: eval_run_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.eval_run_results_id_seq OWNED BY public.eval_run_results.id;


--
-- Name: eval_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eval_runs (
    id bigint NOT NULL,
    config_id bigint NOT NULL,
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    started_at_utc timestamp with time zone,
    completed_at_utc timestamp with time zone,
    summary_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at_utc timestamp with time zone DEFAULT now(),
    updated_at_utc timestamp with time zone DEFAULT now()
);


--
-- Name: eval_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.eval_runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: eval_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.eval_runs_id_seq OWNED BY public.eval_runs.id;


--
-- Name: glossary_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.glossary_categories (
    id bigint NOT NULL,
    name character varying(256) NOT NULL,
    description character varying(1024),
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: glossary_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.glossary_categories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: glossary_categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.glossary_categories_id_seq OWNED BY public.glossary_categories.id;


--
-- Name: glossary_terms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.glossary_terms (
    id bigint NOT NULL,
    category_id bigint NOT NULL,
    term character varying(256) NOT NULL,
    definition text,
    synonyms_json jsonb,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: glossary_terms_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.glossary_terms_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: glossary_terms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.glossary_terms_id_seq OWNED BY public.glossary_terms.id;


--
-- Name: knowledge_base_glossary_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.knowledge_base_glossary_categories (
    id bigint NOT NULL,
    knowledge_base_id bigint NOT NULL,
    category_id bigint NOT NULL,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: knowledge_base_glossary_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.knowledge_base_glossary_categories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: knowledge_base_glossary_categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.knowledge_base_glossary_categories_id_seq OWNED BY public.knowledge_base_glossary_categories.id;


--
-- Name: knowledge_bases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.knowledge_bases (
    id bigint NOT NULL,
    name character varying(256) NOT NULL,
    description character varying(1024),
    icon character varying(64),
    index_names_json jsonb DEFAULT '[]'::jsonb,
    config_json jsonb DEFAULT '{}'::jsonb,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now(),
    status character varying(32) DEFAULT 'active'::character varying NOT NULL,
    CONSTRAINT chk_kb_status CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('processing'::character varying)::text, ('disabled'::character varying)::text, ('deleted'::character varying)::text])))
);


--
-- Name: knowledge_bases_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.knowledge_bases_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: knowledge_bases_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.knowledge_bases_id_seq OWNED BY public.knowledge_bases.id;


--
-- Name: knowledge_document_recall_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.knowledge_document_recall_stats (
    id bigint NOT NULL,
    document_id bigint NOT NULL,
    recall_count integer DEFAULT 0,
    last_recalled_at_utc timestamp without time zone,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: knowledge_document_recall_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.knowledge_document_recall_stats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: knowledge_document_recall_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.knowledge_document_recall_stats_id_seq OWNED BY public.knowledge_document_recall_stats.id;


--
-- Name: knowledge_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.knowledge_documents (
    id bigint NOT NULL,
    knowledge_base_id bigint NOT NULL,
    folder_id bigint,
    title character varying(512) NOT NULL,
    source_type character varying(32) NOT NULL,
    source_uri character varying(1024),
    content_type character varying(128),
    content text,
    extra_json jsonb DEFAULT '{}'::jsonb,
    status character varying(32) DEFAULT 'pending'::character varying,
    segment_count integer DEFAULT 0,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now(),
    file_size bigint DEFAULT '0'::bigint,
    stored_file_id character varying(256),
    ingest_error text,
    ingested_at_utc timestamp without time zone,
    qa_question text,
    CONSTRAINT chk_doc_status CHECK (((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('processing'::character varying)::text, ('completed'::character varying)::text, ('failed'::character varying)::text])))
);


--
-- Name: knowledge_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.knowledge_documents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: knowledge_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.knowledge_documents_id_seq OWNED BY public.knowledge_documents.id;


--
-- Name: knowledge_folders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.knowledge_folders (
    id bigint NOT NULL,
    knowledge_base_id bigint NOT NULL,
    parent_id bigint,
    name character varying(256) NOT NULL,
    sort_order integer DEFAULT 0,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now(),
    CONSTRAINT chk_folder_no_self_ref CHECK (((parent_id IS NULL) OR (parent_id <> id)))
);


--
-- Name: knowledge_folders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.knowledge_folders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: knowledge_folders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.knowledge_folders_id_seq OWNED BY public.knowledge_folders.id;


--
-- Name: llm_catalog_revisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_catalog_revisions (
    id bigint NOT NULL,
    revision bigint NOT NULL,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: llm_catalog_revisions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.llm_catalog_revisions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm_catalog_revisions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.llm_catalog_revisions_id_seq OWNED BY public.llm_catalog_revisions.id;


--
-- Name: llm_connection_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_connection_profiles (
    id bigint NOT NULL,
    profile_key character varying(128) NOT NULL,
    display_name character varying(256) NOT NULL,
    provider character varying(64) NOT NULL,
    base_url character varying(1024),
    websocket_base_url character varying(1024),
    api_version character varying(64),
    region character varying(64),
    extra_json jsonb DEFAULT '{}'::jsonb,
    is_enabled boolean NOT NULL,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: llm_connection_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.llm_connection_profiles_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm_connection_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.llm_connection_profiles_id_seq OWNED BY public.llm_connection_profiles.id;


--
-- Name: llm_features; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_features (
    id bigint NOT NULL,
    feature_key character varying(128) NOT NULL,
    display_name character varying(256) NOT NULL,
    description character varying(1024),
    value_type character varying(32) NOT NULL,
    allowed_values_json jsonb,
    is_filterable boolean NOT NULL,
    is_routable boolean NOT NULL,
    is_enabled boolean NOT NULL,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: llm_features_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.llm_features_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm_features_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.llm_features_id_seq OWNED BY public.llm_features.id;


--
-- Name: llm_model_bindings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_model_bindings (
    id bigint NOT NULL,
    binding_key character varying(128) NOT NULL,
    display_name character varying(256) NOT NULL,
    scene character varying(64) NOT NULL,
    type character varying(32) NOT NULL,
    capability character varying(32),
    model_id bigint NOT NULL,
    metadata_json jsonb DEFAULT '{}'::jsonb,
    is_enabled boolean NOT NULL,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: llm_model_bindings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.llm_model_bindings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm_model_bindings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.llm_model_bindings_id_seq OWNED BY public.llm_model_bindings.id;


--
-- Name: llm_model_features; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_model_features (
    id bigint NOT NULL,
    model_id bigint NOT NULL,
    feature_id bigint NOT NULL,
    is_supported boolean NOT NULL,
    value_json jsonb,
    source character varying(32) NOT NULL,
    remark character varying(512),
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: llm_model_features_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.llm_model_features_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm_model_features_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.llm_model_features_id_seq OWNED BY public.llm_model_features.id;


--
-- Name: llm_model_instances; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_model_instances (
    id bigint NOT NULL,
    instance_key character varying(128) NOT NULL,
    model_id bigint NOT NULL,
    provider_deployment_name character varying(128),
    region character varying(64),
    priority integer NOT NULL,
    weight integer NOT NULL,
    default_timeout_ms integer NOT NULL,
    extra_json jsonb DEFAULT '{}'::jsonb,
    is_enabled boolean NOT NULL,
    is_healthy boolean NOT NULL,
    encrypted_api_key character varying(512),
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: llm_model_instances_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.llm_model_instances_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm_model_instances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.llm_model_instances_id_seq OWNED BY public.llm_model_instances.id;


--
-- Name: llm_models; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_models (
    id bigint NOT NULL,
    model_key character varying(128) NOT NULL,
    type character varying(32) NOT NULL,
    model_name character varying(128) NOT NULL,
    display_name character varying(256) NOT NULL,
    description character varying(1024),
    tags_json jsonb DEFAULT '[]'::jsonb,
    routing_policy_json jsonb DEFAULT '{}'::jsonb,
    retry_policy_json jsonb DEFAULT '{}'::jsonb,
    is_enabled boolean NOT NULL,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now(),
    connection_profile_id bigint NOT NULL
);


--
-- Name: llm_models_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.llm_models_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm_models_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.llm_models_id_seq OWNED BY public.llm_models.id;


--
-- Name: memory_embeddings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.memory_embeddings (
    id bigint NOT NULL,
    memory_id bigint NOT NULL,
    embedding_model character varying(128) DEFAULT ''::character varying NOT NULL,
    vector public.vector(1024),
    created_at_utc timestamp with time zone DEFAULT now(),
    updated_at_utc timestamp with time zone DEFAULT now()
);


--
-- Name: memory_embeddings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.memory_embeddings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: memory_embeddings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.memory_embeddings_id_seq OWNED BY public.memory_embeddings.id;


--
-- Name: memory_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.memory_records (
    id bigint NOT NULL,
    user_id character varying(128) NOT NULL,
    session_id character varying(128),
    memory_type character varying(32) NOT NULL,
    content text NOT NULL,
    summary character varying(1024),
    source_turn_ids_json jsonb DEFAULT '[]'::jsonb NOT NULL,
    relevance_score double precision DEFAULT '0'::double precision NOT NULL,
    access_count integer DEFAULT 0 NOT NULL,
    last_accessed_at_utc timestamp with time zone,
    consolidated_from_json jsonb DEFAULT '[]'::jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    expires_at_utc timestamp with time zone,
    created_at_utc timestamp with time zone DEFAULT now(),
    updated_at_utc timestamp with time zone DEFAULT now()
);


--
-- Name: memory_records_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.memory_records_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: memory_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.memory_records_id_seq OWNED BY public.memory_records.id;


--
-- Name: model_attempt_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_attempt_logs (
    "Id" bigint NOT NULL,
    "RequestId" character varying(64) NOT NULL,
    "ModelKey" character varying(128) NOT NULL,
    "InstanceKey" character varying(128) NOT NULL,
    "AttemptNo" integer NOT NULL,
    "Success" boolean NOT NULL,
    "ErrorCode" character varying(64),
    "ErrorMessage" character varying(2048),
    "InputTokens" integer,
    "OutputTokens" integer,
    "EstimatedCost" numeric(18,6),
    "DurationMs" bigint DEFAULT '0'::bigint NOT NULL,
    "StartedAtUtc" timestamp with time zone NOT NULL,
    "CompletedAtUtc" timestamp with time zone NOT NULL,
    "CreatedAtUtc" timestamp with time zone NOT NULL,
    "UpdatedAtUtc" timestamp with time zone
);


--
-- Name: model_request_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_request_logs (
    "Id" bigint NOT NULL,
    "RequestId" character varying(64) NOT NULL,
    "ModelKey" character varying(128) NOT NULL,
    "Capability" character varying(32) NOT NULL,
    "Success" boolean NOT NULL,
    "AttemptCount" integer DEFAULT 0 NOT NULL,
    "FinalInstanceKey" character varying(128),
    "ErrorCode" character varying(64),
    "ErrorMessage" character varying(2048),
    "TotalInputTokens" integer DEFAULT 0 NOT NULL,
    "TotalOutputTokens" integer DEFAULT 0 NOT NULL,
    "TotalEstimatedCost" numeric(18,6) DEFAULT '0'::numeric NOT NULL,
    "TotalDurationMs" bigint DEFAULT '0'::bigint NOT NULL,
    "StartedAtUtc" timestamp with time zone NOT NULL,
    "CompletedAtUtc" timestamp with time zone NOT NULL,
    "CreatedAtUtc" timestamp with time zone NOT NULL,
    "UpdatedAtUtc" timestamp with time zone
);


--
-- Name: segment_embeddings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.segment_embeddings (
    id bigint NOT NULL,
    segment_id bigint NOT NULL,
    document_id bigint NOT NULL,
    knowledge_base_id bigint NOT NULL,
    embedding_model character varying(128) NOT NULL,
    vector public.vector(1024) NOT NULL,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: segment_embeddings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.segment_embeddings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: segment_embeddings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.segment_embeddings_id_seq OWNED BY public.segment_embeddings.id;


--
-- Name: stored_files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stored_files (
    id bigint NOT NULL,
    file_name character varying(512) NOT NULL,
    content_type character varying(128),
    size_bytes bigint DEFAULT '0'::bigint,
    storage_path character varying(1024) NOT NULL,
    storage_type character varying(32) DEFAULT 'local'::character varying,
    created_at_utc timestamp without time zone DEFAULT now(),
    updated_at_utc timestamp without time zone DEFAULT now()
);


--
-- Name: stored_files_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.stored_files_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stored_files_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.stored_files_id_seq OWNED BY public.stored_files.id;


--
-- Name: trace_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trace_records (
    id bigint NOT NULL,
    trace_id character varying(64) NOT NULL,
    root_span_id character varying(64) DEFAULT ''::character varying NOT NULL,
    agent_key character varying(128),
    session_id character varying(128),
    status character varying(16) DEFAULT 'ok'::character varying NOT NULL,
    total_duration_ms bigint,
    total_input_tokens integer DEFAULT 0 NOT NULL,
    total_output_tokens integer DEFAULT 0 NOT NULL,
    total_estimated_cost double precision DEFAULT '0'::double precision NOT NULL,
    span_count integer DEFAULT 0 NOT NULL,
    started_at_utc timestamp with time zone NOT NULL,
    completed_at_utc timestamp with time zone,
    created_at_utc timestamp with time zone DEFAULT now(),
    updated_at_utc timestamp with time zone DEFAULT now()
);


--
-- Name: trace_records_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.trace_records_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: trace_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.trace_records_id_seq OWNED BY public.trace_records.id;


--
-- Name: trace_spans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trace_spans (
    id bigint NOT NULL,
    trace_id character varying(64) NOT NULL,
    span_id character varying(64) NOT NULL,
    parent_span_id character varying(64),
    span_kind character varying(32) NOT NULL,
    name character varying(256) NOT NULL,
    status character varying(16) DEFAULT 'ok'::character varying NOT NULL,
    started_at_utc timestamp with time zone,
    completed_at_utc timestamp with time zone,
    duration_ms bigint,
    attributes_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    error_code character varying(64),
    error_message text,
    created_at_utc timestamp with time zone DEFAULT now(),
    updated_at_utc timestamp with time zone DEFAULT now()
);


--
-- Name: trace_spans_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.trace_spans_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: trace_spans_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.trace_spans_id_seq OWNED BY public.trace_spans.id;


--
-- Name: agent_catalog_revisions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_catalog_revisions ALTER COLUMN id SET DEFAULT nextval('public.agent_catalog_revisions_id_seq'::regclass);


--
-- Name: agent_definition_versions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_definition_versions ALTER COLUMN id SET DEFAULT nextval('public.agent_definition_versions_id_seq'::regclass);


--
-- Name: agent_definitions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_definitions ALTER COLUMN id SET DEFAULT nextval('public.agent_definitions_id_seq'::regclass);


--
-- Name: agent_execution_audits id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_execution_audits ALTER COLUMN id SET DEFAULT nextval('public.agent_execution_audits_id_seq'::regclass);


--
-- Name: agent_knowledge_base_bindings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_knowledge_base_bindings ALTER COLUMN id SET DEFAULT nextval('public.agent_knowledge_base_bindings_id_seq'::regclass);


--
-- Name: agent_mcp_bindings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_bindings ALTER COLUMN id SET DEFAULT nextval('public.agent_mcp_bindings_id_seq'::regclass);


--
-- Name: agent_mcp_servers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_servers ALTER COLUMN id SET DEFAULT nextval('public.agent_mcp_servers_id_seq'::regclass);


--
-- Name: agent_skill_bindings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_skill_bindings ALTER COLUMN id SET DEFAULT nextval('public.agent_skill_bindings_id_seq'::regclass);


--
-- Name: agent_skills id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_skills ALTER COLUMN id SET DEFAULT nextval('public.agent_skills_id_seq'::regclass);


--
-- Name: agent_tool_bindings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tool_bindings ALTER COLUMN id SET DEFAULT nextval('public.agent_tool_bindings_id_seq'::regclass);


--
-- Name: agent_tools id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tools ALTER COLUMN id SET DEFAULT nextval('public.agent_tools_id_seq'::regclass);


--
-- Name: auth_users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_users ALTER COLUMN id SET DEFAULT nextval('public.auth_users_id_seq'::regclass);


--
-- Name: cost_alerts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cost_alerts ALTER COLUMN id SET DEFAULT nextval('public.cost_alerts_id_seq'::regclass);


--
-- Name: cost_budgets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cost_budgets ALTER COLUMN id SET DEFAULT nextval('public.cost_budgets_id_seq'::regclass);


--
-- Name: document_indexes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_indexes ALTER COLUMN id SET DEFAULT nextval('public.document_indexes_id_seq'::regclass);


--
-- Name: document_processing_jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_processing_jobs ALTER COLUMN id SET DEFAULT nextval('public.document_processing_jobs_id_seq'::regclass);


--
-- Name: document_segments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_segments ALTER COLUMN id SET DEFAULT nextval('public.document_segments_id_seq'::regclass);


--
-- Name: eval_cases id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_cases ALTER COLUMN id SET DEFAULT nextval('public.eval_cases_id_seq'::regclass);


--
-- Name: eval_datasets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_datasets ALTER COLUMN id SET DEFAULT nextval('public.eval_datasets_id_seq'::regclass);


--
-- Name: eval_run_configs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_run_configs ALTER COLUMN id SET DEFAULT nextval('public.eval_run_configs_id_seq'::regclass);


--
-- Name: eval_run_results id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_run_results ALTER COLUMN id SET DEFAULT nextval('public.eval_run_results_id_seq'::regclass);


--
-- Name: eval_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_runs ALTER COLUMN id SET DEFAULT nextval('public.eval_runs_id_seq'::regclass);


--
-- Name: glossary_categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.glossary_categories ALTER COLUMN id SET DEFAULT nextval('public.glossary_categories_id_seq'::regclass);


--
-- Name: glossary_terms id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.glossary_terms ALTER COLUMN id SET DEFAULT nextval('public.glossary_terms_id_seq'::regclass);


--
-- Name: knowledge_base_glossary_categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_base_glossary_categories ALTER COLUMN id SET DEFAULT nextval('public.knowledge_base_glossary_categories_id_seq'::regclass);


--
-- Name: knowledge_bases id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_bases ALTER COLUMN id SET DEFAULT nextval('public.knowledge_bases_id_seq'::regclass);


--
-- Name: knowledge_document_recall_stats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_document_recall_stats ALTER COLUMN id SET DEFAULT nextval('public.knowledge_document_recall_stats_id_seq'::regclass);


--
-- Name: knowledge_documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_documents ALTER COLUMN id SET DEFAULT nextval('public.knowledge_documents_id_seq'::regclass);


--
-- Name: knowledge_folders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_folders ALTER COLUMN id SET DEFAULT nextval('public.knowledge_folders_id_seq'::regclass);


--
-- Name: llm_catalog_revisions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_catalog_revisions ALTER COLUMN id SET DEFAULT nextval('public.llm_catalog_revisions_id_seq'::regclass);


--
-- Name: llm_connection_profiles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_connection_profiles ALTER COLUMN id SET DEFAULT nextval('public.llm_connection_profiles_id_seq'::regclass);


--
-- Name: llm_features id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_features ALTER COLUMN id SET DEFAULT nextval('public.llm_features_id_seq'::regclass);


--
-- Name: llm_model_bindings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_bindings ALTER COLUMN id SET DEFAULT nextval('public.llm_model_bindings_id_seq'::regclass);


--
-- Name: llm_model_features id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_features ALTER COLUMN id SET DEFAULT nextval('public.llm_model_features_id_seq'::regclass);


--
-- Name: llm_model_instances id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_instances ALTER COLUMN id SET DEFAULT nextval('public.llm_model_instances_id_seq'::regclass);


--
-- Name: llm_models id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_models ALTER COLUMN id SET DEFAULT nextval('public.llm_models_id_seq'::regclass);


--
-- Name: memory_embeddings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_embeddings ALTER COLUMN id SET DEFAULT nextval('public.memory_embeddings_id_seq'::regclass);


--
-- Name: memory_records id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_records ALTER COLUMN id SET DEFAULT nextval('public.memory_records_id_seq'::regclass);


--
-- Name: segment_embeddings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.segment_embeddings ALTER COLUMN id SET DEFAULT nextval('public.segment_embeddings_id_seq'::regclass);


--
-- Name: stored_files id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stored_files ALTER COLUMN id SET DEFAULT nextval('public.stored_files_id_seq'::regclass);


--
-- Name: trace_records id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_records ALTER COLUMN id SET DEFAULT nextval('public.trace_records_id_seq'::regclass);


--
-- Name: trace_spans id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_spans ALTER COLUMN id SET DEFAULT nextval('public.trace_spans_id_seq'::regclass);


--
-- Name: agent_catalog_revisions agent_catalog_revisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_catalog_revisions
    ADD CONSTRAINT agent_catalog_revisions_pkey PRIMARY KEY (id);


--
-- Name: agent_catalog_revisions agent_catalog_revisions_revision_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_catalog_revisions
    ADD CONSTRAINT agent_catalog_revisions_revision_key UNIQUE (revision);


--
-- Name: agent_definition_versions agent_definition_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_definition_versions
    ADD CONSTRAINT agent_definition_versions_pkey PRIMARY KEY (id);


--
-- Name: agent_definitions agent_definitions_agent_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_definitions
    ADD CONSTRAINT agent_definitions_agent_key_key UNIQUE (agent_key);


--
-- Name: agent_definitions agent_definitions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_definitions
    ADD CONSTRAINT agent_definitions_pkey PRIMARY KEY (id);


--
-- Name: agent_execution_audits agent_execution_audits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_execution_audits
    ADD CONSTRAINT agent_execution_audits_pkey PRIMARY KEY (id);


--
-- Name: agent_knowledge_base_bindings agent_knowledge_base_bindings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_knowledge_base_bindings
    ADD CONSTRAINT agent_knowledge_base_bindings_pkey PRIMARY KEY (id);


--
-- Name: agent_mcp_bindings agent_mcp_bindings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_bindings
    ADD CONSTRAINT agent_mcp_bindings_pkey PRIMARY KEY (id);


--
-- Name: agent_mcp_servers agent_mcp_servers_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_servers
    ADD CONSTRAINT agent_mcp_servers_name_key UNIQUE (name);


--
-- Name: agent_mcp_servers agent_mcp_servers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_servers
    ADD CONSTRAINT agent_mcp_servers_pkey PRIMARY KEY (id);


--
-- Name: agent_skill_bindings agent_skill_bindings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_skill_bindings
    ADD CONSTRAINT agent_skill_bindings_pkey PRIMARY KEY (id);


--
-- Name: agent_skills agent_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_skills
    ADD CONSTRAINT agent_skills_pkey PRIMARY KEY (id);


--
-- Name: agent_skills agent_skills_skill_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_skills
    ADD CONSTRAINT agent_skills_skill_key_key UNIQUE (skill_key);


--
-- Name: agent_tool_bindings agent_tool_bindings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tool_bindings
    ADD CONSTRAINT agent_tool_bindings_pkey PRIMARY KEY (id);


--
-- Name: agent_tools agent_tools_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tools
    ADD CONSTRAINT agent_tools_pkey PRIMARY KEY (id);


--
-- Name: agent_tools agent_tools_tool_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tools
    ADD CONSTRAINT agent_tools_tool_name_key UNIQUE (tool_name);



--
-- Name: auth_users auth_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_users
    ADD CONSTRAINT auth_users_pkey PRIMARY KEY (id);


--
-- Name: auth_users auth_users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_users
    ADD CONSTRAINT auth_users_username_key UNIQUE (username);


--
-- Name: cost_alerts cost_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cost_alerts
    ADD CONSTRAINT cost_alerts_pkey PRIMARY KEY (id);


--
-- Name: cost_budgets cost_budgets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cost_budgets
    ADD CONSTRAINT cost_budgets_pkey PRIMARY KEY (id);


--
-- Name: document_indexes document_indexes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_indexes
    ADD CONSTRAINT document_indexes_pkey PRIMARY KEY (id);


--
-- Name: document_processing_jobs document_processing_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_processing_jobs
    ADD CONSTRAINT document_processing_jobs_pkey PRIMARY KEY (id);


--
-- Name: document_segments document_segments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_segments
    ADD CONSTRAINT document_segments_pkey PRIMARY KEY (id);


--
-- Name: eval_cases eval_cases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_cases
    ADD CONSTRAINT eval_cases_pkey PRIMARY KEY (id);


--
-- Name: eval_datasets eval_datasets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_datasets
    ADD CONSTRAINT eval_datasets_pkey PRIMARY KEY (id);


--
-- Name: eval_run_configs eval_run_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_run_configs
    ADD CONSTRAINT eval_run_configs_pkey PRIMARY KEY (id);


--
-- Name: eval_run_results eval_run_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_run_results
    ADD CONSTRAINT eval_run_results_pkey PRIMARY KEY (id);


--
-- Name: eval_runs eval_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_runs
    ADD CONSTRAINT eval_runs_pkey PRIMARY KEY (id);


--
-- Name: glossary_categories glossary_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.glossary_categories
    ADD CONSTRAINT glossary_categories_pkey PRIMARY KEY (id);


--
-- Name: glossary_terms glossary_terms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.glossary_terms
    ADD CONSTRAINT glossary_terms_pkey PRIMARY KEY (id);


--
-- Name: knowledge_base_glossary_categories knowledge_base_glossary_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_base_glossary_categories
    ADD CONSTRAINT knowledge_base_glossary_categories_pkey PRIMARY KEY (id);


--
-- Name: knowledge_bases knowledge_bases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_bases
    ADD CONSTRAINT knowledge_bases_pkey PRIMARY KEY (id);


--
-- Name: knowledge_document_recall_stats knowledge_document_recall_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_document_recall_stats
    ADD CONSTRAINT knowledge_document_recall_stats_pkey PRIMARY KEY (id);


--
-- Name: knowledge_documents knowledge_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_documents
    ADD CONSTRAINT knowledge_documents_pkey PRIMARY KEY (id);


--
-- Name: knowledge_folders knowledge_folders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_folders
    ADD CONSTRAINT knowledge_folders_pkey PRIMARY KEY (id);


--
-- Name: llm_catalog_revisions llm_catalog_revisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_catalog_revisions
    ADD CONSTRAINT llm_catalog_revisions_pkey PRIMARY KEY (id);


--
-- Name: llm_catalog_revisions llm_catalog_revisions_revision_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_catalog_revisions
    ADD CONSTRAINT llm_catalog_revisions_revision_key UNIQUE (revision);


--
-- Name: llm_connection_profiles llm_connection_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_connection_profiles
    ADD CONSTRAINT llm_connection_profiles_pkey PRIMARY KEY (id);


--
-- Name: llm_connection_profiles llm_connection_profiles_profile_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_connection_profiles
    ADD CONSTRAINT llm_connection_profiles_profile_key_key UNIQUE (profile_key);


--
-- Name: llm_features llm_features_feature_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_features
    ADD CONSTRAINT llm_features_feature_key_key UNIQUE (feature_key);


--
-- Name: llm_features llm_features_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_features
    ADD CONSTRAINT llm_features_pkey PRIMARY KEY (id);


--
-- Name: llm_model_bindings llm_model_bindings_binding_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_bindings
    ADD CONSTRAINT llm_model_bindings_binding_key_key UNIQUE (binding_key);


--
-- Name: llm_model_bindings llm_model_bindings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_bindings
    ADD CONSTRAINT llm_model_bindings_pkey PRIMARY KEY (id);


--
-- Name: llm_model_features llm_model_features_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_features
    ADD CONSTRAINT llm_model_features_pkey PRIMARY KEY (id);


--
-- Name: llm_model_instances llm_model_instances_instance_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_instances
    ADD CONSTRAINT llm_model_instances_instance_key_key UNIQUE (instance_key);


--
-- Name: llm_model_instances llm_model_instances_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_instances
    ADD CONSTRAINT llm_model_instances_pkey PRIMARY KEY (id);


--
-- Name: llm_models llm_models_model_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_models
    ADD CONSTRAINT llm_models_model_key_key UNIQUE (model_key);


--
-- Name: llm_models llm_models_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_models
    ADD CONSTRAINT llm_models_pkey PRIMARY KEY (id);


--
-- Name: memory_embeddings memory_embeddings_memory_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_embeddings
    ADD CONSTRAINT memory_embeddings_memory_id_key UNIQUE (memory_id);


--
-- Name: memory_embeddings memory_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_embeddings
    ADD CONSTRAINT memory_embeddings_pkey PRIMARY KEY (id);


--
-- Name: memory_records memory_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_records
    ADD CONSTRAINT memory_records_pkey PRIMARY KEY (id);


--
-- Name: model_attempt_logs model_attempt_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_attempt_logs
    ADD CONSTRAINT model_attempt_logs_pkey PRIMARY KEY ("Id");


--
-- Name: model_request_logs model_request_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_request_logs
    ADD CONSTRAINT model_request_logs_pkey PRIMARY KEY ("Id");


--
-- Name: segment_embeddings segment_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.segment_embeddings
    ADD CONSTRAINT segment_embeddings_pkey PRIMARY KEY (id);


--
-- Name: stored_files stored_files_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stored_files
    ADD CONSTRAINT stored_files_pkey PRIMARY KEY (id);


--
-- Name: trace_records trace_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_records
    ADD CONSTRAINT trace_records_pkey PRIMARY KEY (id);


--
-- Name: trace_records trace_records_trace_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_records
    ADD CONSTRAINT trace_records_trace_id_key UNIQUE (trace_id);


--
-- Name: trace_spans trace_spans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_spans
    ADD CONSTRAINT trace_spans_pkey PRIMARY KEY (id);


--
-- Name: trace_spans trace_spans_span_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trace_spans
    ADD CONSTRAINT trace_spans_span_id_key UNIQUE (span_id);


--
-- Name: agent_knowledge_base_bindings uq_agent_kb_binding; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_knowledge_base_bindings
    ADD CONSTRAINT uq_agent_kb_binding UNIQUE (agent_version_id, knowledge_base_id);


--
-- Name: agent_mcp_bindings uq_agent_mcp_binding; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_bindings
    ADD CONSTRAINT uq_agent_mcp_binding UNIQUE (agent_version_id, server_name);


--
-- Name: agent_skill_bindings uq_agent_skill_binding; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_skill_bindings
    ADD CONSTRAINT uq_agent_skill_binding UNIQUE (agent_version_id, skill_key);


--
-- Name: agent_tool_bindings uq_agent_tool_binding; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tool_bindings
    ADD CONSTRAINT uq_agent_tool_binding UNIQUE (agent_version_id, tool_name);


--
-- Name: knowledge_base_glossary_categories uq_kb_glossary_category; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_base_glossary_categories
    ADD CONSTRAINT uq_kb_glossary_category UNIQUE (knowledge_base_id, category_id);


--
-- Name: llm_model_features uq_model_feature; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_features
    ADD CONSTRAINT uq_model_feature UNIQUE (model_id, feature_id);


--
-- Name: ix_agent_audit_key_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_audit_key_time ON public.agent_execution_audits USING btree (agent_key, created_at_utc);


--
-- Name: ix_agent_audit_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_audit_run_id ON public.agent_execution_audits USING btree (run_id);


--
-- Name: ix_agent_kb_bindings_agent_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_kb_bindings_agent_version_id ON public.agent_knowledge_base_bindings USING btree (agent_version_id);


--
-- Name: ix_agent_kb_bindings_kb_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_kb_bindings_kb_id ON public.agent_knowledge_base_bindings USING btree (knowledge_base_id);


--
-- Name: ix_agent_mcp_bindings_agent_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_mcp_bindings_agent_version_id ON public.agent_mcp_bindings USING btree (agent_version_id);


--
-- Name: ix_agent_mcp_bindings_server_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_mcp_bindings_server_name ON public.agent_mcp_bindings USING btree (server_name);


--
-- Name: ix_agent_skill_bindings_agent_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_skill_bindings_agent_version_id ON public.agent_skill_bindings USING btree (agent_version_id);


--
-- Name: ix_agent_skill_bindings_skill_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_skill_bindings_skill_key ON public.agent_skill_bindings USING btree (skill_key);


--
-- Name: ix_agent_tool_bindings_agent_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_tool_bindings_agent_version_id ON public.agent_tool_bindings USING btree (agent_version_id);


--
-- Name: ix_agent_tool_bindings_tool_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_tool_bindings_tool_name ON public.agent_tool_bindings USING btree (tool_name);


--
-- Name: ix_agent_version_agent_ver; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_version_agent_ver ON public.agent_definition_versions USING btree (agent_id, version_number);


--
-- Name: ix_cost_alerts_budget_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cost_alerts_budget_id ON public.cost_alerts USING btree (budget_id);


--
-- Name: ix_cost_alerts_unacked; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cost_alerts_unacked ON public.cost_alerts USING btree (acknowledged_at_utc);


--
-- Name: ix_cost_budgets_scope; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_cost_budgets_scope ON public.cost_budgets USING btree (scope_type, scope_key);


--
-- Name: ix_cost_budgets_scope_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cost_budgets_scope_type ON public.cost_budgets USING btree (scope_type);


--
-- Name: ix_doc_processing_jobs_doc_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_doc_processing_jobs_doc_id ON public.document_processing_jobs USING btree (document_id);


--
-- Name: ix_document_indexes_doc_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_indexes_doc_id ON public.document_indexes USING btree (document_id);


--
-- Name: ix_document_indexes_kb_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_indexes_kb_id ON public.document_indexes USING btree (knowledge_base_id);


--
-- Name: ix_document_segment_doc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_segment_doc_idx ON public.document_segments USING btree (document_id, segment_index);


--
-- Name: ix_eval_cases_dataset_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eval_cases_dataset_id ON public.eval_cases USING btree (dataset_id);


--
-- Name: ix_eval_run_configs_dataset_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eval_run_configs_dataset_id ON public.eval_run_configs USING btree (dataset_id);


--
-- Name: ix_eval_run_results_case_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eval_run_results_case_id ON public.eval_run_results USING btree (case_id);


--
-- Name: ix_eval_run_results_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eval_run_results_run_id ON public.eval_run_results USING btree (run_id);


--
-- Name: ix_eval_runs_config_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eval_runs_config_id ON public.eval_runs USING btree (config_id);


--
-- Name: ix_glossary_terms_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_glossary_terms_category_id ON public.glossary_terms USING btree (category_id);


--
-- Name: ix_kb_doc_recall_stats_doc_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kb_doc_recall_stats_doc_id ON public.knowledge_document_recall_stats USING btree (document_id);


--
-- Name: ix_kb_glossary_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kb_glossary_category_id ON public.knowledge_base_glossary_categories USING btree (category_id);


--
-- Name: ix_kb_glossary_kb_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_kb_glossary_kb_id ON public.knowledge_base_glossary_categories USING btree (knowledge_base_id);


--
-- Name: ix_knowledge_doc_kb_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_doc_kb_status ON public.knowledge_documents USING btree (knowledge_base_id, status);


--
-- Name: ix_knowledge_folders_kb_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_folders_kb_id ON public.knowledge_folders USING btree (knowledge_base_id);


--
-- Name: ix_knowledge_folders_parent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_folders_parent_id ON public.knowledge_folders USING btree (parent_id);


--
-- Name: ix_llm_model_bindings_model_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_model_bindings_model_id ON public.llm_model_bindings USING btree (model_id);


--
-- Name: ix_llm_model_features_feature_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_model_features_feature_id ON public.llm_model_features USING btree (feature_id);


--
-- Name: ix_llm_model_features_model_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_model_features_model_id ON public.llm_model_features USING btree (model_id);


--
-- Name: ix_llm_model_instances_model_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_model_instances_model_id ON public.llm_model_instances USING btree (model_id);


--
-- Name: ix_llm_models_connection_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_models_connection_profile_id ON public.llm_models USING btree (connection_profile_id);


--
-- Name: ix_memory_embeddings_vec; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_memory_embeddings_vec ON public.memory_embeddings USING hnsw (vector public.vector_cosine_ops);


--
-- Name: ix_memory_records_memory_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_memory_records_memory_type ON public.memory_records USING btree (memory_type);


--
-- Name: ix_memory_records_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_memory_records_user_id ON public.memory_records USING btree (user_id);


--
-- Name: ix_memory_records_user_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_memory_records_user_type ON public.memory_records USING btree (user_id, memory_type);


--
-- Name: ix_model_attempt_logs_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_model_attempt_logs_request_id ON public.model_attempt_logs USING btree ("RequestId");


--
-- Name: ix_model_request_logs_model_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_model_request_logs_model_key ON public.model_request_logs USING btree ("ModelKey");


--
-- Name: ix_model_request_logs_started_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_model_request_logs_started_at ON public.model_request_logs USING btree ("StartedAtUtc");


--
-- Name: ix_model_request_logs_success; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_model_request_logs_success ON public.model_request_logs USING btree ("Success");


--
-- Name: ix_seg_emb_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_seg_emb_document_id ON public.segment_embeddings USING btree (document_id);


--
-- Name: ix_seg_emb_kb_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_seg_emb_kb_id ON public.segment_embeddings USING btree (knowledge_base_id);


--
-- Name: ix_seg_emb_kb_vec; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_seg_emb_kb_vec ON public.segment_embeddings USING hnsw (vector public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: ix_seg_emb_segment_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_seg_emb_segment_id ON public.segment_embeddings USING btree (segment_id);


--
-- Name: ix_trace_records_agent_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_trace_records_agent_key ON public.trace_records USING btree (agent_key);


--
-- Name: ix_trace_records_agent_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_trace_records_agent_time ON public.trace_records USING btree (agent_key, started_at_utc);


--
-- Name: ix_trace_spans_trace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_trace_spans_trace_id ON public.trace_spans USING btree (trace_id);


--
-- Name: cost_alerts cost_alerts_budget_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cost_alerts
    ADD CONSTRAINT cost_alerts_budget_id_fkey FOREIGN KEY (budget_id) REFERENCES public.cost_budgets(id) ON DELETE CASCADE;


--
-- Name: eval_cases eval_cases_dataset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_cases
    ADD CONSTRAINT eval_cases_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES public.eval_datasets(id) ON DELETE CASCADE;


--
-- Name: knowledge_documents fk_doc_folder_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_documents
    ADD CONSTRAINT fk_doc_folder_id FOREIGN KEY (folder_id) REFERENCES public.knowledge_folders(id) ON DELETE SET NULL;


--
-- Name: knowledge_documents fk_doc_kb_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_documents
    ADD CONSTRAINT fk_doc_kb_id FOREIGN KEY (knowledge_base_id) REFERENCES public.knowledge_bases(id) ON DELETE CASCADE;


--
-- Name: segment_embeddings fk_emb_doc_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.segment_embeddings
    ADD CONSTRAINT fk_emb_doc_id FOREIGN KEY (document_id) REFERENCES public.knowledge_documents(id) ON DELETE CASCADE;


--
-- Name: segment_embeddings fk_emb_kb_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.segment_embeddings
    ADD CONSTRAINT fk_emb_kb_id FOREIGN KEY (knowledge_base_id) REFERENCES public.knowledge_bases(id) ON DELETE CASCADE;


--
-- Name: segment_embeddings fk_emb_segment_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.segment_embeddings
    ADD CONSTRAINT fk_emb_segment_id FOREIGN KEY (segment_id) REFERENCES public.document_segments(id) ON DELETE CASCADE;


--
-- Name: knowledge_folders fk_folder_kb_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_folders
    ADD CONSTRAINT fk_folder_kb_id FOREIGN KEY (knowledge_base_id) REFERENCES public.knowledge_bases(id) ON DELETE CASCADE;


--
-- Name: document_indexes fk_index_doc_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_indexes
    ADD CONSTRAINT fk_index_doc_id FOREIGN KEY (document_id) REFERENCES public.knowledge_documents(id) ON DELETE CASCADE;


--
-- Name: document_indexes fk_index_kb_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_indexes
    ADD CONSTRAINT fk_index_kb_id FOREIGN KEY (knowledge_base_id) REFERENCES public.knowledge_bases(id) ON DELETE CASCADE;


--
-- Name: document_processing_jobs fk_job_doc_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_processing_jobs
    ADD CONSTRAINT fk_job_doc_id FOREIGN KEY (document_id) REFERENCES public.knowledge_documents(id) ON DELETE CASCADE;


--
-- Name: document_segments fk_segment_doc_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_segments
    ADD CONSTRAINT fk_segment_doc_id FOREIGN KEY (document_id) REFERENCES public.knowledge_documents(id) ON DELETE CASCADE;


--
-- Name: llm_model_bindings llm_model_bindings_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_bindings
    ADD CONSTRAINT llm_model_bindings_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.llm_models(id);


--
-- Name: llm_model_features llm_model_features_feature_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_features
    ADD CONSTRAINT llm_model_features_feature_id_fkey FOREIGN KEY (feature_id) REFERENCES public.llm_features(id);


--
-- Name: llm_model_features llm_model_features_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_features
    ADD CONSTRAINT llm_model_features_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.llm_models(id);


--
-- Name: llm_model_instances llm_model_instances_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_model_instances
    ADD CONSTRAINT llm_model_instances_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.llm_models(id);


--
-- Name: memory_embeddings memory_embeddings_memory_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_embeddings
    ADD CONSTRAINT memory_embeddings_memory_id_fkey FOREIGN KEY (memory_id) REFERENCES public.memory_records(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


