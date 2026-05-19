--
-- PostgreSQL database dump
--

\restrict oS7EXPb1g91gGhpt1fps0UCYPcIrL9amxmIYwAfaUOtWoydmC773bPpmmZAUitJ

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

-- Started on 2026-05-19 12:10:28

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 6 (class 2615 OID 210963)
-- Name: qastraschema; Type: SCHEMA; Schema: -; Owner: qastra
--

CREATE SCHEMA qastraschema;


ALTER SCHEMA qastraschema OWNER TO qastra;

--
-- TOC entry 918 (class 1247 OID 211100)
-- Name: integrationcategory; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.integrationcategory AS ENUM (
    'project_management',
    'communication',
    'documentation',
    'version_control'
);


ALTER TYPE qastraschema.integrationcategory OWNER TO qastra;

--
-- TOC entry 915 (class 1247 OID 211082)
-- Name: integrationtype; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.integrationtype AS ENUM (
    'jira',
    'redmine',
    'azure_devops',
    'slack',
    'confluence',
    'github',
    'gitlab',
    'teams'
);


ALTER TYPE qastraschema.integrationtype OWNER TO qastra;

--
-- TOC entry 894 (class 1247 OID 210984)
-- Name: requirementsourcetype; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.requirementsourcetype AS ENUM (
    'upload',
    'jira',
    'azure_devops',
    'confluence',
    'manual'
);


ALTER TYPE qastraschema.requirementsourcetype OWNER TO qastra;

--
-- TOC entry 921 (class 1247 OID 211110)
-- Name: syncstatus; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.syncstatus AS ENUM (
    'idle',
    'syncing',
    'success',
    'failed'
);


ALTER TYPE qastraschema.syncstatus OWNER TO qastra;

--
-- TOC entry 900 (class 1247 OID 211006)
-- Name: testcasecategory; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.testcasecategory AS ENUM (
    'smoke',
    'regression',
    'e2e',
    'integration',
    'sanity'
);


ALTER TYPE qastraschema.testcasecategory OWNER TO qastra;

--
-- TOC entry 897 (class 1247 OID 210996)
-- Name: testcasepriority; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.testcasepriority AS ENUM (
    'critical',
    'high',
    'medium',
    'low'
);


ALTER TYPE qastraschema.testcasepriority OWNER TO qastra;

--
-- TOC entry 903 (class 1247 OID 211018)
-- Name: testcasestatus; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.testcasestatus AS ENUM (
    'draft',
    'ready',
    'deprecated'
);


ALTER TYPE qastraschema.testcasestatus OWNER TO qastra;

--
-- TOC entry 912 (class 1247 OID 211072)
-- Name: testresultstatus; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.testresultstatus AS ENUM (
    'passed',
    'failed',
    'skipped',
    'error'
);


ALTER TYPE qastraschema.testresultstatus OWNER TO qastra;

--
-- TOC entry 909 (class 1247 OID 211058)
-- Name: testrunstatus; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.testrunstatus AS ENUM (
    'pending',
    'running',
    'passed',
    'failed',
    'cancelled',
    'error'
);


ALTER TYPE qastraschema.testrunstatus OWNER TO qastra;

--
-- TOC entry 906 (class 1247 OID 211026)
-- Name: teststepaction; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.teststepaction AS ENUM (
    'navigate',
    'click',
    'type',
    'fill',
    'select',
    'check',
    'uncheck',
    'hover',
    'screenshot',
    'wait',
    'assert_text',
    'assert_visible',
    'assert_url',
    'assert_title',
    'custom'
);


ALTER TYPE qastraschema.teststepaction OWNER TO qastra;

--
-- TOC entry 891 (class 1247 OID 210974)
-- Name: userrole; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.userrole AS ENUM (
    'admin',
    'manager',
    'tester',
    'viewer'
);


ALTER TYPE qastraschema.userrole OWNER TO qastra;

--
-- TOC entry 933 (class 1247 OID 211152)
-- Name: userstoryitemtype; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.userstoryitemtype AS ENUM (
    'epic',
    'story',
    'bug',
    'task',
    'subtask',
    'feature',
    'requirement',
    'other'
);


ALTER TYPE qastraschema.userstoryitemtype OWNER TO qastra;

--
-- TOC entry 927 (class 1247 OID 211132)
-- Name: userstorypriority; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.userstorypriority AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);


ALTER TYPE qastraschema.userstorypriority OWNER TO qastra;

--
-- TOC entry 930 (class 1247 OID 211142)
-- Name: userstorysource; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.userstorysource AS ENUM (
    'jira',
    'redmine',
    'azure_devops',
    'manual'
);


ALTER TYPE qastraschema.userstorysource OWNER TO qastra;

--
-- TOC entry 924 (class 1247 OID 211120)
-- Name: userstorystatus; Type: TYPE; Schema: qastraschema; Owner: qastra
--

CREATE TYPE qastraschema.userstorystatus AS ENUM (
    'open',
    'in_progress',
    'done',
    'blocked',
    'closed'
);


ALTER TYPE qastraschema.userstorystatus OWNER TO qastra;

--
-- TOC entry 255 (class 1255 OID 211500)
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: qastraschema; Owner: qastra
--

CREATE FUNCTION qastraschema.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$;


ALTER FUNCTION qastraschema.update_updated_at_column() OWNER TO qastra;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 220 (class 1259 OID 210967)
-- Name: alembic_version; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE qastraschema.alembic_version OWNER TO qastra;

--
-- TOC entry 242 (class 1259 OID 211478)
-- Name: audit_logs; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.audit_logs (
    id integer NOT NULL,
    user_id integer,
    action character varying(50) NOT NULL,
    entity_type character varying(100) NOT NULL,
    entity_id integer,
    description text,
    old_values jsonb,
    new_values jsonb,
    ip_address character varying(45),
    user_agent character varying(500),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE qastraschema.audit_logs OWNER TO qastra;

--
-- TOC entry 241 (class 1259 OID 211477)
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.audit_logs_id_seq OWNER TO qastra;

--
-- TOC entry 5382 (class 0 OID 0)
-- Dependencies: 241
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.audit_logs_id_seq OWNED BY qastraschema.audit_logs.id;


--
-- TOC entry 250 (class 1259 OID 211626)
-- Name: email_verifications; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.email_verifications (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    otp_hash character varying(255) NOT NULL,
    user_data jsonb NOT NULL,
    security_questions jsonb,
    expires_at timestamp with time zone NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    locked_until timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE qastraschema.email_verifications OWNER TO qastra;

--
-- TOC entry 249 (class 1259 OID 211625)
-- Name: email_verifications_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.email_verifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.email_verifications_id_seq OWNER TO qastra;

--
-- TOC entry 5383 (class 0 OID 0)
-- Dependencies: 249
-- Name: email_verifications_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.email_verifications_id_seq OWNED BY qastraschema.email_verifications.id;


--
-- TOC entry 246 (class 1259 OID 211544)
-- Name: gap_analysis_runs; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.gap_analysis_runs (
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    project_id integer NOT NULL,
    requirement_id integer NOT NULL,
    created_by integer,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    result_json jsonb,
    error_message text,
    pdf_path character varying(500)
);


ALTER TABLE qastraschema.gap_analysis_runs OWNER TO qastra;

--
-- TOC entry 245 (class 1259 OID 211543)
-- Name: gap_analysis_runs_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.gap_analysis_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.gap_analysis_runs_id_seq OWNER TO qastra;

--
-- TOC entry 5384 (class 0 OID 0)
-- Dependencies: 245
-- Name: gap_analysis_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.gap_analysis_runs_id_seq OWNED BY qastraschema.gap_analysis_runs.id;


--
-- TOC entry 244 (class 1259 OID 211513)
-- Name: integrity_check_results; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.integrity_check_results (
    id integer NOT NULL,
    project_id integer NOT NULL,
    run_id character varying(64) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    app_url character varying(500) NOT NULL,
    app_reachable boolean,
    login_successful boolean,
    overall_status character varying(20),
    steps_total integer DEFAULT 0,
    steps_passed integer DEFAULT 0,
    steps_failed integer DEFAULT 0,
    summary text,
    error_message text,
    steps_data jsonb,
    screenshots jsonb,
    duration_ms integer,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    live_progress jsonb
);


ALTER TABLE qastraschema.integrity_check_results OWNER TO qastra;

--
-- TOC entry 243 (class 1259 OID 211512)
-- Name: integrity_check_results_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.integrity_check_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.integrity_check_results_id_seq OWNER TO qastra;

--
-- TOC entry 5385 (class 0 OID 0)
-- Dependencies: 243
-- Name: integrity_check_results_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.integrity_check_results_id_seq OWNED BY qastraschema.integrity_check_results.id;


--
-- TOC entry 222 (class 1259 OID 211170)
-- Name: organizations; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.organizations (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    slug character varying(100) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE qastraschema.organizations OWNER TO qastra;

--
-- TOC entry 221 (class 1259 OID 211169)
-- Name: organizations_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.organizations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.organizations_id_seq OWNER TO qastra;

--
-- TOC entry 5386 (class 0 OID 0)
-- Dependencies: 221
-- Name: organizations_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.organizations_id_seq OWNED BY qastraschema.organizations.id;


--
-- TOC entry 254 (class 1259 OID 211671)
-- Name: password_reset_tokens; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.password_reset_tokens (
    id integer NOT NULL,
    user_id integer NOT NULL,
    token_hash character varying(255) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE qastraschema.password_reset_tokens OWNER TO qastra;

--
-- TOC entry 253 (class 1259 OID 211670)
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.password_reset_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.password_reset_tokens_id_seq OWNER TO qastra;

--
-- TOC entry 5387 (class 0 OID 0)
-- Dependencies: 253
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.password_reset_tokens_id_seq OWNED BY qastraschema.password_reset_tokens.id;


--
-- TOC entry 228 (class 1259 OID 211246)
-- Name: project_integrations; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.project_integrations (
    id integer NOT NULL,
    project_id integer NOT NULL,
    integration_type qastraschema.integrationtype NOT NULL,
    integration_category qastraschema.integrationcategory NOT NULL,
    name character varying(255),
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    last_sync_at timestamp with time zone,
    sync_status qastraschema.syncstatus DEFAULT 'idle'::qastraschema.syncstatus NOT NULL,
    last_sync_error character varying(500),
    items_synced integer DEFAULT 0,
    configured_by_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE qastraschema.project_integrations OWNER TO qastra;

--
-- TOC entry 227 (class 1259 OID 211245)
-- Name: project_integrations_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.project_integrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.project_integrations_id_seq OWNER TO qastra;

--
-- TOC entry 5388 (class 0 OID 0)
-- Dependencies: 227
-- Name: project_integrations_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.project_integrations_id_seq OWNED BY qastraschema.project_integrations.id;


--
-- TOC entry 226 (class 1259 OID 211218)
-- Name: projects; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.projects (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    app_url character varying(500),
    app_credentials jsonb,
    is_active boolean DEFAULT true NOT NULL,
    owner_id integer NOT NULL,
    organization_id integer,
    jira_project_key character varying(50),
    azure_devops_project character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE qastraschema.projects OWNER TO qastra;

--
-- TOC entry 225 (class 1259 OID 211217)
-- Name: projects_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.projects_id_seq OWNER TO qastra;

--
-- TOC entry 5389 (class 0 OID 0)
-- Dependencies: 225
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.projects_id_seq OWNED BY qastraschema.projects.id;


--
-- TOC entry 232 (class 1259 OID 211325)
-- Name: requirements; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.requirements (
    id integer NOT NULL,
    project_id integer NOT NULL,
    title character varying(500) NOT NULL,
    content text,
    source_type qastraschema.requirementsourcetype DEFAULT 'manual'::qastraschema.requirementsourcetype,
    source_url character varying(1000),
    source_id character varying(100),
    file_path character varying(500),
    file_name character varying(255),
    file_type character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE qastraschema.requirements OWNER TO qastra;

--
-- TOC entry 231 (class 1259 OID 211324)
-- Name: requirements_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.requirements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.requirements_id_seq OWNER TO qastra;

--
-- TOC entry 5390 (class 0 OID 0)
-- Dependencies: 231
-- Name: requirements_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.requirements_id_seq OWNED BY qastraschema.requirements.id;


--
-- TOC entry 252 (class 1259 OID 211648)
-- Name: security_questions; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.security_questions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    question_text character varying(500) NOT NULL,
    answer_hash character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE qastraschema.security_questions OWNER TO qastra;

--
-- TOC entry 251 (class 1259 OID 211647)
-- Name: security_questions_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.security_questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.security_questions_id_seq OWNER TO qastra;

--
-- TOC entry 5391 (class 0 OID 0)
-- Dependencies: 251
-- Name: security_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.security_questions_id_seq OWNED BY qastraschema.security_questions.id;


--
-- TOC entry 234 (class 1259 OID 211348)
-- Name: test_cases; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.test_cases (
    id integer NOT NULL,
    project_id integer NOT NULL,
    requirement_id integer,
    user_story_id integer,
    title character varying(500) NOT NULL,
    description text,
    preconditions text,
    priority qastraschema.testcasepriority DEFAULT 'medium'::qastraschema.testcasepriority,
    category qastraschema.testcasecategory DEFAULT 'regression'::qastraschema.testcasecategory,
    status qastraschema.testcasestatus DEFAULT 'draft'::qastraschema.testcasestatus,
    tags character varying(500),
    is_automated boolean DEFAULT true,
    integrity_check boolean DEFAULT false,
    is_generated boolean DEFAULT false,
    generation_prompt text,
    created_by integer,
    jira_key character varying(50),
    azure_devops_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    case_number integer NOT NULL,
    source character varying(16) DEFAULT 'manual'::character varying NOT NULL
);


ALTER TABLE qastraschema.test_cases OWNER TO qastra;

--
-- TOC entry 233 (class 1259 OID 211347)
-- Name: test_cases_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.test_cases_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.test_cases_id_seq OWNER TO qastra;

--
-- TOC entry 5392 (class 0 OID 0)
-- Dependencies: 233
-- Name: test_cases_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.test_cases_id_seq OWNED BY qastraschema.test_cases.id;


--
-- TOC entry 248 (class 1259 OID 211586)
-- Name: test_recommendation_runs; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.test_recommendation_runs (
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    project_id integer NOT NULL,
    requirement_id integer NOT NULL,
    created_by integer,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    result_json jsonb,
    error_message text,
    pdf_path character varying(500)
);


ALTER TABLE qastraschema.test_recommendation_runs OWNER TO qastra;

--
-- TOC entry 247 (class 1259 OID 211585)
-- Name: test_recommendation_runs_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.test_recommendation_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.test_recommendation_runs_id_seq OWNER TO qastra;

--
-- TOC entry 5393 (class 0 OID 0)
-- Dependencies: 247
-- Name: test_recommendation_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.test_recommendation_runs_id_seq OWNED BY qastraschema.test_recommendation_runs.id;


--
-- TOC entry 240 (class 1259 OID 211449)
-- Name: test_results; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.test_results (
    id integer NOT NULL,
    test_run_id integer NOT NULL,
    test_case_id integer NOT NULL,
    status qastraschema.testresultstatus NOT NULL,
    duration_ms integer,
    error_message text,
    error_stack text,
    failed_step integer,
    screenshot_path character varying(500),
    video_path character varying(500),
    trace_path character varying(500),
    step_results jsonb,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    adapted_steps jsonb,
    original_steps jsonb,
    agent_logs jsonb
);


ALTER TABLE qastraschema.test_results OWNER TO qastra;

--
-- TOC entry 239 (class 1259 OID 211448)
-- Name: test_results_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.test_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.test_results_id_seq OWNER TO qastra;

--
-- TOC entry 5394 (class 0 OID 0)
-- Dependencies: 239
-- Name: test_results_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.test_results_id_seq OWNED BY qastraschema.test_results.id;


--
-- TOC entry 238 (class 1259 OID 211416)
-- Name: test_runs; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.test_runs (
    id integer NOT NULL,
    project_id integer NOT NULL,
    name character varying(255),
    description character varying(1000),
    status qastraschema.testrunstatus DEFAULT 'pending'::qastraschema.testrunstatus,
    triggered_by integer,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    total_tests integer DEFAULT 0,
    passed_tests integer DEFAULT 0,
    failed_tests integer DEFAULT 0,
    skipped_tests integer DEFAULT 0,
    browser character varying(50) DEFAULT 'chromium'::character varying,
    headless character varying(10) DEFAULT 'true'::character varying,
    config jsonb,
    report_path character varying(500),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    run_number integer NOT NULL
);


ALTER TABLE qastraschema.test_runs OWNER TO qastra;

--
-- TOC entry 237 (class 1259 OID 211415)
-- Name: test_runs_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.test_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.test_runs_id_seq OWNER TO qastra;

--
-- TOC entry 5395 (class 0 OID 0)
-- Dependencies: 237
-- Name: test_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.test_runs_id_seq OWNED BY qastraschema.test_runs.id;


--
-- TOC entry 236 (class 1259 OID 211393)
-- Name: test_steps; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.test_steps (
    id integer NOT NULL,
    test_case_id integer NOT NULL,
    step_number integer NOT NULL,
    action qastraschema.teststepaction NOT NULL,
    target character varying(500),
    value text,
    description text,
    expected_result text,
    playwright_code text,
    selector_type character varying(50),
    selector_confidence integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE qastraschema.test_steps OWNER TO qastra;

--
-- TOC entry 235 (class 1259 OID 211392)
-- Name: test_steps_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.test_steps_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.test_steps_id_seq OWNER TO qastra;

--
-- TOC entry 5396 (class 0 OID 0)
-- Dependencies: 235
-- Name: test_steps_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.test_steps_id_seq OWNED BY qastraschema.test_steps.id;


--
-- TOC entry 230 (class 1259 OID 211284)
-- Name: user_stories; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.user_stories (
    id integer NOT NULL,
    project_id integer NOT NULL,
    external_id character varying(100),
    external_key character varying(50),
    external_url character varying(500),
    source qastraschema.userstorysource DEFAULT 'manual'::qastraschema.userstorysource NOT NULL,
    integration_id integer,
    title character varying(500) NOT NULL,
    description text,
    acceptance_criteria text,
    status qastraschema.userstorystatus DEFAULT 'open'::qastraschema.userstorystatus NOT NULL,
    priority qastraschema.userstorypriority DEFAULT 'medium'::qastraschema.userstorypriority NOT NULL,
    item_type qastraschema.userstoryitemtype DEFAULT 'story'::qastraschema.userstoryitemtype NOT NULL,
    parent_key character varying(100),
    story_points integer,
    assignee character varying(255),
    reporter character varying(255),
    labels character varying(500)[],
    sprint_id character varying(50),
    sprint_name character varying(255),
    integrity_check boolean DEFAULT false NOT NULL,
    last_synced_at timestamp with time zone,
    external_updated_at timestamp with time zone,
    external_created_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE qastraschema.user_stories OWNER TO qastra;

--
-- TOC entry 229 (class 1259 OID 211283)
-- Name: user_stories_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.user_stories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.user_stories_id_seq OWNER TO qastra;

--
-- TOC entry 5397 (class 0 OID 0)
-- Dependencies: 229
-- Name: user_stories_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.user_stories_id_seq OWNED BY qastraschema.user_stories.id;


--
-- TOC entry 224 (class 1259 OID 211188)
-- Name: users; Type: TABLE; Schema: qastraschema; Owner: qastra
--

CREATE TABLE qastraschema.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(255),
    role qastraschema.userrole DEFAULT 'tester'::qastraschema.userrole NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_superuser boolean DEFAULT false NOT NULL,
    organization_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_verified boolean DEFAULT true NOT NULL,
    company_name character varying(255),
    country_code character varying(10),
    phone_number character varying(20)
);


ALTER TABLE qastraschema.users OWNER TO qastra;

--
-- TOC entry 223 (class 1259 OID 211187)
-- Name: users_id_seq; Type: SEQUENCE; Schema: qastraschema; Owner: qastra
--

CREATE SEQUENCE qastraschema.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE qastraschema.users_id_seq OWNER TO qastra;

--
-- TOC entry 5398 (class 0 OID 0)
-- Dependencies: 223
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: qastraschema; Owner: qastra
--

ALTER SEQUENCE qastraschema.users_id_seq OWNED BY qastraschema.users.id;


--
-- TOC entry 5050 (class 2604 OID 211481)
-- Name: audit_logs id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.audit_logs ALTER COLUMN id SET DEFAULT nextval('qastraschema.audit_logs_id_seq'::regclass);


--
-- TOC entry 5068 (class 2604 OID 211629)
-- Name: email_verifications id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.email_verifications ALTER COLUMN id SET DEFAULT nextval('qastraschema.email_verifications_id_seq'::regclass);


--
-- TOC entry 5060 (class 2604 OID 211547)
-- Name: gap_analysis_runs id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.gap_analysis_runs ALTER COLUMN id SET DEFAULT nextval('qastraschema.gap_analysis_runs_id_seq'::regclass);


--
-- TOC entry 5053 (class 2604 OID 211516)
-- Name: integrity_check_results id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.integrity_check_results ALTER COLUMN id SET DEFAULT nextval('qastraschema.integrity_check_results_id_seq'::regclass);


--
-- TOC entry 4990 (class 2604 OID 211173)
-- Name: organizations id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.organizations ALTER COLUMN id SET DEFAULT nextval('qastraschema.organizations_id_seq'::regclass);


--
-- TOC entry 5075 (class 2604 OID 211674)
-- Name: password_reset_tokens id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.password_reset_tokens ALTER COLUMN id SET DEFAULT nextval('qastraschema.password_reset_tokens_id_seq'::regclass);


--
-- TOC entry 5005 (class 2604 OID 211249)
-- Name: project_integrations id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.project_integrations ALTER COLUMN id SET DEFAULT nextval('qastraschema.project_integrations_id_seq'::regclass);


--
-- TOC entry 5001 (class 2604 OID 211221)
-- Name: projects id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.projects ALTER COLUMN id SET DEFAULT nextval('qastraschema.projects_id_seq'::regclass);


--
-- TOC entry 5020 (class 2604 OID 211328)
-- Name: requirements id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.requirements ALTER COLUMN id SET DEFAULT nextval('qastraschema.requirements_id_seq'::regclass);


--
-- TOC entry 5072 (class 2604 OID 211651)
-- Name: security_questions id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.security_questions ALTER COLUMN id SET DEFAULT nextval('qastraschema.security_questions_id_seq'::regclass);


--
-- TOC entry 5024 (class 2604 OID 211351)
-- Name: test_cases id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_cases ALTER COLUMN id SET DEFAULT nextval('qastraschema.test_cases_id_seq'::regclass);


--
-- TOC entry 5064 (class 2604 OID 211589)
-- Name: test_recommendation_runs id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_recommendation_runs ALTER COLUMN id SET DEFAULT nextval('qastraschema.test_recommendation_runs_id_seq'::regclass);


--
-- TOC entry 5047 (class 2604 OID 211452)
-- Name: test_results id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_results ALTER COLUMN id SET DEFAULT nextval('qastraschema.test_results_id_seq'::regclass);


--
-- TOC entry 5037 (class 2604 OID 211419)
-- Name: test_runs id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_runs ALTER COLUMN id SET DEFAULT nextval('qastraschema.test_runs_id_seq'::regclass);


--
-- TOC entry 5034 (class 2604 OID 211396)
-- Name: test_steps id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_steps ALTER COLUMN id SET DEFAULT nextval('qastraschema.test_steps_id_seq'::regclass);


--
-- TOC entry 5012 (class 2604 OID 211287)
-- Name: user_stories id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.user_stories ALTER COLUMN id SET DEFAULT nextval('qastraschema.user_stories_id_seq'::regclass);


--
-- TOC entry 4994 (class 2604 OID 211191)
-- Name: users id; Type: DEFAULT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.users ALTER COLUMN id SET DEFAULT nextval('qastraschema.users_id_seq'::regclass);


--
-- TOC entry 5342 (class 0 OID 210967)
-- Dependencies: 220
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.alembic_version (version_num) FROM stdin;
m3r4g5e6s7g8n9
\.


--
-- TOC entry 5364 (class 0 OID 211478)
-- Dependencies: 242
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.audit_logs (id, user_id, action, entity_type, entity_id, description, old_values, new_values, ip_address, user_agent, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5372 (class 0 OID 211626)
-- Dependencies: 250
-- Data for Name: email_verifications; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.email_verifications (id, email, otp_hash, user_data, security_questions, expires_at, attempts, locked_until, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5368 (class 0 OID 211544)
-- Dependencies: 246
-- Data for Name: gap_analysis_runs; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.gap_analysis_runs (id, created_at, updated_at, project_id, requirement_id, created_by, status, result_json, error_message, pdf_path) FROM stdin;
\.


--
-- TOC entry 5366 (class 0 OID 211513)
-- Dependencies: 244
-- Data for Name: integrity_check_results; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.integrity_check_results (id, project_id, run_id, status, app_url, app_reachable, login_successful, overall_status, steps_total, steps_passed, steps_failed, summary, error_message, steps_data, screenshots, duration_ms, started_at, completed_at, created_at, updated_at, live_progress) FROM stdin;
\.


--
-- TOC entry 5344 (class 0 OID 211170)
-- Dependencies: 222
-- Data for Name: organizations; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.organizations (id, name, slug, is_active, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5376 (class 0 OID 211671)
-- Dependencies: 254
-- Data for Name: password_reset_tokens; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.password_reset_tokens (id, user_id, token_hash, expires_at, used, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5350 (class 0 OID 211246)
-- Dependencies: 228
-- Data for Name: project_integrations; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.project_integrations (id, project_id, integration_type, integration_category, name, config, is_enabled, last_sync_at, sync_status, last_sync_error, items_synced, configured_by_id, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5348 (class 0 OID 211218)
-- Dependencies: 226
-- Data for Name: projects; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.projects (id, name, description, app_url, app_credentials, is_active, owner_id, organization_id, jira_project_key, azure_devops_project, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5354 (class 0 OID 211325)
-- Dependencies: 232
-- Data for Name: requirements; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.requirements (id, project_id, title, content, source_type, source_url, source_id, file_path, file_name, file_type, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5374 (class 0 OID 211648)
-- Dependencies: 252
-- Data for Name: security_questions; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.security_questions (id, user_id, question_text, answer_hash, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5356 (class 0 OID 211348)
-- Dependencies: 234
-- Data for Name: test_cases; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.test_cases (id, project_id, requirement_id, user_story_id, title, description, preconditions, priority, category, status, tags, is_automated, integrity_check, is_generated, generation_prompt, created_by, jira_key, azure_devops_id, created_at, updated_at, case_number, source) FROM stdin;
\.


--
-- TOC entry 5370 (class 0 OID 211586)
-- Dependencies: 248
-- Data for Name: test_recommendation_runs; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.test_recommendation_runs (id, created_at, updated_at, project_id, requirement_id, created_by, status, result_json, error_message, pdf_path) FROM stdin;
\.


--
-- TOC entry 5362 (class 0 OID 211449)
-- Dependencies: 240
-- Data for Name: test_results; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.test_results (id, test_run_id, test_case_id, status, duration_ms, error_message, error_stack, failed_step, screenshot_path, video_path, trace_path, step_results, started_at, completed_at, created_at, updated_at, adapted_steps, original_steps, agent_logs) FROM stdin;
\.


--
-- TOC entry 5360 (class 0 OID 211416)
-- Dependencies: 238
-- Data for Name: test_runs; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.test_runs (id, project_id, name, description, status, triggered_by, started_at, completed_at, total_tests, passed_tests, failed_tests, skipped_tests, browser, headless, config, report_path, created_at, updated_at, run_number) FROM stdin;
\.


--
-- TOC entry 5358 (class 0 OID 211393)
-- Dependencies: 236
-- Data for Name: test_steps; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.test_steps (id, test_case_id, step_number, action, target, value, description, expected_result, playwright_code, selector_type, selector_confidence, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5352 (class 0 OID 211284)
-- Dependencies: 230
-- Data for Name: user_stories; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.user_stories (id, project_id, external_id, external_key, external_url, source, integration_id, title, description, acceptance_criteria, status, priority, item_type, parent_key, story_points, assignee, reporter, labels, sprint_id, sprint_name, integrity_check, last_synced_at, external_updated_at, external_created_at, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5346 (class 0 OID 211188)
-- Dependencies: 224
-- Data for Name: users; Type: TABLE DATA; Schema: qastraschema; Owner: qastra
--

COPY qastraschema.users (id, email, hashed_password, full_name, role, is_active, is_superuser, organization_id, created_at, updated_at, is_verified, company_name, country_code, phone_number) FROM stdin;
1	admin@qastra.dev	$2b$12$WLvcssHE4A.dduGVIxTVGujYQH7usB96ermap26ykH256Y/z5P51e	QAstra Admin	admin	t	t	\N	2026-05-19 12:06:22.038357+05:30	2026-05-19 12:06:22.038357+05:30	t	\N	\N	\N
\.


--
-- TOC entry 5399 (class 0 OID 0)
-- Dependencies: 241
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.audit_logs_id_seq', 1, false);


--
-- TOC entry 5400 (class 0 OID 0)
-- Dependencies: 249
-- Name: email_verifications_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.email_verifications_id_seq', 1, false);


--
-- TOC entry 5401 (class 0 OID 0)
-- Dependencies: 245
-- Name: gap_analysis_runs_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.gap_analysis_runs_id_seq', 1, false);


--
-- TOC entry 5402 (class 0 OID 0)
-- Dependencies: 243
-- Name: integrity_check_results_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.integrity_check_results_id_seq', 1, false);


--
-- TOC entry 5403 (class 0 OID 0)
-- Dependencies: 221
-- Name: organizations_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.organizations_id_seq', 1, false);


--
-- TOC entry 5404 (class 0 OID 0)
-- Dependencies: 253
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.password_reset_tokens_id_seq', 1, false);


--
-- TOC entry 5405 (class 0 OID 0)
-- Dependencies: 227
-- Name: project_integrations_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.project_integrations_id_seq', 1, false);


--
-- TOC entry 5406 (class 0 OID 0)
-- Dependencies: 225
-- Name: projects_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.projects_id_seq', 1, false);


--
-- TOC entry 5407 (class 0 OID 0)
-- Dependencies: 231
-- Name: requirements_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.requirements_id_seq', 1, false);


--
-- TOC entry 5408 (class 0 OID 0)
-- Dependencies: 251
-- Name: security_questions_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.security_questions_id_seq', 1, false);


--
-- TOC entry 5409 (class 0 OID 0)
-- Dependencies: 233
-- Name: test_cases_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.test_cases_id_seq', 1, false);


--
-- TOC entry 5410 (class 0 OID 0)
-- Dependencies: 247
-- Name: test_recommendation_runs_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.test_recommendation_runs_id_seq', 1, false);


--
-- TOC entry 5411 (class 0 OID 0)
-- Dependencies: 239
-- Name: test_results_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.test_results_id_seq', 1, false);


--
-- TOC entry 5412 (class 0 OID 0)
-- Dependencies: 237
-- Name: test_runs_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.test_runs_id_seq', 1, false);


--
-- TOC entry 5413 (class 0 OID 0)
-- Dependencies: 235
-- Name: test_steps_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.test_steps_id_seq', 1, false);


--
-- TOC entry 5414 (class 0 OID 0)
-- Dependencies: 229
-- Name: user_stories_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.user_stories_id_seq', 1, false);


--
-- TOC entry 5415 (class 0 OID 0)
-- Dependencies: 223
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: qastraschema; Owner: qastra
--

SELECT pg_catalog.setval('qastraschema.users_id_seq', 1, true);


--
-- TOC entry 5080 (class 2606 OID 210972)
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- TOC entry 5128 (class 2606 OID 211492)
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- TOC entry 5148 (class 2606 OID 211644)
-- Name: email_verifications email_verifications_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.email_verifications
    ADD CONSTRAINT email_verifications_pkey PRIMARY KEY (id);


--
-- TOC entry 5138 (class 2606 OID 211560)
-- Name: gap_analysis_runs gap_analysis_runs_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.gap_analysis_runs
    ADD CONSTRAINT gap_analysis_runs_pkey PRIMARY KEY (id);


--
-- TOC entry 5132 (class 2606 OID 211533)
-- Name: integrity_check_results integrity_check_results_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.integrity_check_results
    ADD CONSTRAINT integrity_check_results_pkey PRIMARY KEY (id);


--
-- TOC entry 5134 (class 2606 OID 211535)
-- Name: integrity_check_results integrity_check_results_run_id_key; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.integrity_check_results
    ADD CONSTRAINT integrity_check_results_run_id_key UNIQUE (run_id);


--
-- TOC entry 5082 (class 2606 OID 211184)
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- TOC entry 5084 (class 2606 OID 211186)
-- Name: organizations organizations_slug_key; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.organizations
    ADD CONSTRAINT organizations_slug_key UNIQUE (slug);


--
-- TOC entry 5156 (class 2606 OID 211686)
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- TOC entry 5095 (class 2606 OID 211268)
-- Name: project_integrations project_integrations_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.project_integrations
    ADD CONSTRAINT project_integrations_pkey PRIMARY KEY (id);


--
-- TOC entry 5097 (class 2606 OID 211270)
-- Name: project_integrations project_integrations_project_id_integration_type_key; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.project_integrations
    ADD CONSTRAINT project_integrations_project_id_integration_type_key UNIQUE (project_id, integration_type);


--
-- TOC entry 5091 (class 2606 OID 211234)
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- TOC entry 5107 (class 2606 OID 211340)
-- Name: requirements requirements_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.requirements
    ADD CONSTRAINT requirements_pkey PRIMARY KEY (id);


--
-- TOC entry 5153 (class 2606 OID 211663)
-- Name: security_questions security_questions_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.security_questions
    ADD CONSTRAINT security_questions_pkey PRIMARY KEY (id);


--
-- TOC entry 5112 (class 2606 OID 211368)
-- Name: test_cases test_cases_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_cases
    ADD CONSTRAINT test_cases_pkey PRIMARY KEY (id);


--
-- TOC entry 5146 (class 2606 OID 211602)
-- Name: test_recommendation_runs test_recommendation_runs_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_recommendation_runs
    ADD CONSTRAINT test_recommendation_runs_pkey PRIMARY KEY (id);


--
-- TOC entry 5126 (class 2606 OID 211464)
-- Name: test_results test_results_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_results
    ADD CONSTRAINT test_results_pkey PRIMARY KEY (id);


--
-- TOC entry 5120 (class 2606 OID 211436)
-- Name: test_runs test_runs_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_runs
    ADD CONSTRAINT test_runs_pkey PRIMARY KEY (id);


--
-- TOC entry 5117 (class 2606 OID 211408)
-- Name: test_steps test_steps_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_steps
    ADD CONSTRAINT test_steps_pkey PRIMARY KEY (id);


--
-- TOC entry 5114 (class 2606 OID 211581)
-- Name: test_cases uq_test_cases_project_case_number; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_cases
    ADD CONSTRAINT uq_test_cases_project_case_number UNIQUE (project_id, case_number);


--
-- TOC entry 5122 (class 2606 OID 211584)
-- Name: test_runs uq_test_runs_project_run_number; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_runs
    ADD CONSTRAINT uq_test_runs_project_run_number UNIQUE (project_id, run_number);


--
-- TOC entry 5104 (class 2606 OID 211308)
-- Name: user_stories user_stories_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.user_stories
    ADD CONSTRAINT user_stories_pkey PRIMARY KEY (id);


--
-- TOC entry 5087 (class 2606 OID 211210)
-- Name: users users_email_key; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- TOC entry 5089 (class 2606 OID 211208)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 5129 (class 1259 OID 211499)
-- Name: idx_audit_logs_entity; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_audit_logs_entity ON qastraschema.audit_logs USING btree (entity_type, entity_id);


--
-- TOC entry 5130 (class 1259 OID 211498)
-- Name: idx_audit_logs_user; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_audit_logs_user ON qastraschema.audit_logs USING btree (user_id);


--
-- TOC entry 5149 (class 1259 OID 211646)
-- Name: idx_email_verifications_expires; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_email_verifications_expires ON qastraschema.email_verifications USING btree (expires_at);


--
-- TOC entry 5092 (class 1259 OID 211281)
-- Name: idx_project_integrations_project; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_project_integrations_project ON qastraschema.project_integrations USING btree (project_id);


--
-- TOC entry 5093 (class 1259 OID 211282)
-- Name: idx_project_integrations_type; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_project_integrations_type ON qastraschema.project_integrations USING btree (integration_type);


--
-- TOC entry 5105 (class 1259 OID 211346)
-- Name: idx_requirements_project; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_requirements_project ON qastraschema.requirements USING btree (project_id);


--
-- TOC entry 5108 (class 1259 OID 211391)
-- Name: idx_test_cases_integrity_check; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_test_cases_integrity_check ON qastraschema.test_cases USING btree (project_id, integrity_check) WHERE (integrity_check = true);


--
-- TOC entry 5109 (class 1259 OID 211389)
-- Name: idx_test_cases_project; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_test_cases_project ON qastraschema.test_cases USING btree (project_id);


--
-- TOC entry 5110 (class 1259 OID 211390)
-- Name: idx_test_cases_requirement; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_test_cases_requirement ON qastraschema.test_cases USING btree (requirement_id);


--
-- TOC entry 5123 (class 1259 OID 211475)
-- Name: idx_test_results_run; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_test_results_run ON qastraschema.test_results USING btree (test_run_id);


--
-- TOC entry 5124 (class 1259 OID 211476)
-- Name: idx_test_results_test_case; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_test_results_test_case ON qastraschema.test_results USING btree (test_case_id);


--
-- TOC entry 5118 (class 1259 OID 211447)
-- Name: idx_test_runs_project; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_test_runs_project ON qastraschema.test_runs USING btree (project_id);


--
-- TOC entry 5115 (class 1259 OID 211414)
-- Name: idx_test_steps_test_case; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_test_steps_test_case ON qastraschema.test_steps USING btree (test_case_id);


--
-- TOC entry 5098 (class 1259 OID 211320)
-- Name: idx_user_stories_external_key; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_user_stories_external_key ON qastraschema.user_stories USING btree (external_key);


--
-- TOC entry 5099 (class 1259 OID 211321)
-- Name: idx_user_stories_integration; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_user_stories_integration ON qastraschema.user_stories USING btree (integration_id);


--
-- TOC entry 5100 (class 1259 OID 211323)
-- Name: idx_user_stories_integrity_check; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_user_stories_integrity_check ON qastraschema.user_stories USING btree (project_id, integrity_check) WHERE (integrity_check = true);


--
-- TOC entry 5101 (class 1259 OID 211319)
-- Name: idx_user_stories_project; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_user_stories_project ON qastraschema.user_stories USING btree (project_id);


--
-- TOC entry 5102 (class 1259 OID 211322)
-- Name: idx_user_stories_sprint; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_user_stories_sprint ON qastraschema.user_stories USING btree (sprint_id);


--
-- TOC entry 5085 (class 1259 OID 211216)
-- Name: idx_users_email; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX idx_users_email ON qastraschema.users USING btree (email);


--
-- TOC entry 5150 (class 1259 OID 211645)
-- Name: ix_email_verifications_email; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE UNIQUE INDEX ix_email_verifications_email ON qastraschema.email_verifications USING btree (email);


--
-- TOC entry 5139 (class 1259 OID 211578)
-- Name: ix_gap_analysis_runs_created_by; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX ix_gap_analysis_runs_created_by ON qastraschema.gap_analysis_runs USING btree (created_by);


--
-- TOC entry 5140 (class 1259 OID 211576)
-- Name: ix_gap_analysis_runs_project_id; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX ix_gap_analysis_runs_project_id ON qastraschema.gap_analysis_runs USING btree (project_id);


--
-- TOC entry 5141 (class 1259 OID 211577)
-- Name: ix_gap_analysis_runs_requirement_id; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX ix_gap_analysis_runs_requirement_id ON qastraschema.gap_analysis_runs USING btree (requirement_id);


--
-- TOC entry 5135 (class 1259 OID 211541)
-- Name: ix_integrity_check_results_project_id; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX ix_integrity_check_results_project_id ON qastraschema.integrity_check_results USING btree (project_id);


--
-- TOC entry 5136 (class 1259 OID 211542)
-- Name: ix_integrity_check_results_run_id; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX ix_integrity_check_results_run_id ON qastraschema.integrity_check_results USING btree (run_id);


--
-- TOC entry 5154 (class 1259 OID 211692)
-- Name: ix_password_reset_tokens_user_id; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX ix_password_reset_tokens_user_id ON qastraschema.password_reset_tokens USING btree (user_id);


--
-- TOC entry 5151 (class 1259 OID 211669)
-- Name: ix_security_questions_user_id; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX ix_security_questions_user_id ON qastraschema.security_questions USING btree (user_id);


--
-- TOC entry 5142 (class 1259 OID 211620)
-- Name: ix_test_recommendation_runs_created_by; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX ix_test_recommendation_runs_created_by ON qastraschema.test_recommendation_runs USING btree (created_by);


--
-- TOC entry 5143 (class 1259 OID 211618)
-- Name: ix_test_recommendation_runs_project_id; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX ix_test_recommendation_runs_project_id ON qastraschema.test_recommendation_runs USING btree (project_id);


--
-- TOC entry 5144 (class 1259 OID 211619)
-- Name: ix_test_recommendation_runs_requirement_id; Type: INDEX; Schema: qastraschema; Owner: qastra
--

CREATE INDEX ix_test_recommendation_runs_requirement_id ON qastraschema.test_recommendation_runs USING btree (requirement_id);


--
-- TOC entry 5194 (class 2620 OID 211509)
-- Name: audit_logs update_audit_logs_updated_at; Type: TRIGGER; Schema: qastraschema; Owner: qastra
--

CREATE TRIGGER update_audit_logs_updated_at BEFORE UPDATE ON qastraschema.audit_logs FOR EACH ROW EXECUTE FUNCTION qastraschema.update_updated_at_column();


--
-- TOC entry 5184 (class 2620 OID 211501)
-- Name: organizations update_organizations_updated_at; Type: TRIGGER; Schema: qastraschema; Owner: qastra
--

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON qastraschema.organizations FOR EACH ROW EXECUTE FUNCTION qastraschema.update_updated_at_column();


--
-- TOC entry 5187 (class 2620 OID 211510)
-- Name: project_integrations update_project_integrations_updated_at; Type: TRIGGER; Schema: qastraschema; Owner: qastra
--

CREATE TRIGGER update_project_integrations_updated_at BEFORE UPDATE ON qastraschema.project_integrations FOR EACH ROW EXECUTE FUNCTION qastraschema.update_updated_at_column();


--
-- TOC entry 5186 (class 2620 OID 211503)
-- Name: projects update_projects_updated_at; Type: TRIGGER; Schema: qastraschema; Owner: qastra
--

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON qastraschema.projects FOR EACH ROW EXECUTE FUNCTION qastraschema.update_updated_at_column();


--
-- TOC entry 5189 (class 2620 OID 211504)
-- Name: requirements update_requirements_updated_at; Type: TRIGGER; Schema: qastraschema; Owner: qastra
--

CREATE TRIGGER update_requirements_updated_at BEFORE UPDATE ON qastraschema.requirements FOR EACH ROW EXECUTE FUNCTION qastraschema.update_updated_at_column();


--
-- TOC entry 5190 (class 2620 OID 211505)
-- Name: test_cases update_test_cases_updated_at; Type: TRIGGER; Schema: qastraschema; Owner: qastra
--

CREATE TRIGGER update_test_cases_updated_at BEFORE UPDATE ON qastraschema.test_cases FOR EACH ROW EXECUTE FUNCTION qastraschema.update_updated_at_column();


--
-- TOC entry 5193 (class 2620 OID 211508)
-- Name: test_results update_test_results_updated_at; Type: TRIGGER; Schema: qastraschema; Owner: qastra
--

CREATE TRIGGER update_test_results_updated_at BEFORE UPDATE ON qastraschema.test_results FOR EACH ROW EXECUTE FUNCTION qastraschema.update_updated_at_column();


--
-- TOC entry 5192 (class 2620 OID 211507)
-- Name: test_runs update_test_runs_updated_at; Type: TRIGGER; Schema: qastraschema; Owner: qastra
--

CREATE TRIGGER update_test_runs_updated_at BEFORE UPDATE ON qastraschema.test_runs FOR EACH ROW EXECUTE FUNCTION qastraschema.update_updated_at_column();


--
-- TOC entry 5191 (class 2620 OID 211506)
-- Name: test_steps update_test_steps_updated_at; Type: TRIGGER; Schema: qastraschema; Owner: qastra
--

CREATE TRIGGER update_test_steps_updated_at BEFORE UPDATE ON qastraschema.test_steps FOR EACH ROW EXECUTE FUNCTION qastraschema.update_updated_at_column();


--
-- TOC entry 5188 (class 2620 OID 211511)
-- Name: user_stories update_user_stories_updated_at; Type: TRIGGER; Schema: qastraschema; Owner: qastra
--

CREATE TRIGGER update_user_stories_updated_at BEFORE UPDATE ON qastraschema.user_stories FOR EACH ROW EXECUTE FUNCTION qastraschema.update_updated_at_column();


--
-- TOC entry 5185 (class 2620 OID 211502)
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: qastraschema; Owner: qastra
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON qastraschema.users FOR EACH ROW EXECUTE FUNCTION qastraschema.update_updated_at_column();


--
-- TOC entry 5174 (class 2606 OID 211493)
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES qastraschema.users(id);


--
-- TOC entry 5176 (class 2606 OID 211561)
-- Name: gap_analysis_runs gap_analysis_runs_created_by_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.gap_analysis_runs
    ADD CONSTRAINT gap_analysis_runs_created_by_fkey FOREIGN KEY (created_by) REFERENCES qastraschema.users(id) ON DELETE SET NULL;


--
-- TOC entry 5177 (class 2606 OID 211566)
-- Name: gap_analysis_runs gap_analysis_runs_project_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.gap_analysis_runs
    ADD CONSTRAINT gap_analysis_runs_project_id_fkey FOREIGN KEY (project_id) REFERENCES qastraschema.projects(id) ON DELETE CASCADE;


--
-- TOC entry 5178 (class 2606 OID 211571)
-- Name: gap_analysis_runs gap_analysis_runs_requirement_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.gap_analysis_runs
    ADD CONSTRAINT gap_analysis_runs_requirement_id_fkey FOREIGN KEY (requirement_id) REFERENCES qastraschema.requirements(id) ON DELETE CASCADE;


--
-- TOC entry 5175 (class 2606 OID 211536)
-- Name: integrity_check_results integrity_check_results_project_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.integrity_check_results
    ADD CONSTRAINT integrity_check_results_project_id_fkey FOREIGN KEY (project_id) REFERENCES qastraschema.projects(id) ON DELETE CASCADE;


--
-- TOC entry 5183 (class 2606 OID 211687)
-- Name: password_reset_tokens password_reset_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES qastraschema.users(id) ON DELETE CASCADE;


--
-- TOC entry 5160 (class 2606 OID 211276)
-- Name: project_integrations project_integrations_configured_by_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.project_integrations
    ADD CONSTRAINT project_integrations_configured_by_id_fkey FOREIGN KEY (configured_by_id) REFERENCES qastraschema.users(id);


--
-- TOC entry 5161 (class 2606 OID 211271)
-- Name: project_integrations project_integrations_project_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.project_integrations
    ADD CONSTRAINT project_integrations_project_id_fkey FOREIGN KEY (project_id) REFERENCES qastraschema.projects(id) ON DELETE CASCADE;


--
-- TOC entry 5158 (class 2606 OID 211240)
-- Name: projects projects_organization_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.projects
    ADD CONSTRAINT projects_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES qastraschema.organizations(id);


--
-- TOC entry 5159 (class 2606 OID 211235)
-- Name: projects projects_owner_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.projects
    ADD CONSTRAINT projects_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES qastraschema.users(id);


--
-- TOC entry 5164 (class 2606 OID 211341)
-- Name: requirements requirements_project_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.requirements
    ADD CONSTRAINT requirements_project_id_fkey FOREIGN KEY (project_id) REFERENCES qastraschema.projects(id);


--
-- TOC entry 5182 (class 2606 OID 211664)
-- Name: security_questions security_questions_user_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.security_questions
    ADD CONSTRAINT security_questions_user_id_fkey FOREIGN KEY (user_id) REFERENCES qastraschema.users(id) ON DELETE CASCADE;


--
-- TOC entry 5165 (class 2606 OID 211384)
-- Name: test_cases test_cases_created_by_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_cases
    ADD CONSTRAINT test_cases_created_by_fkey FOREIGN KEY (created_by) REFERENCES qastraschema.users(id);


--
-- TOC entry 5166 (class 2606 OID 211369)
-- Name: test_cases test_cases_project_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_cases
    ADD CONSTRAINT test_cases_project_id_fkey FOREIGN KEY (project_id) REFERENCES qastraschema.projects(id);


--
-- TOC entry 5167 (class 2606 OID 211374)
-- Name: test_cases test_cases_requirement_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_cases
    ADD CONSTRAINT test_cases_requirement_id_fkey FOREIGN KEY (requirement_id) REFERENCES qastraschema.requirements(id);


--
-- TOC entry 5168 (class 2606 OID 211379)
-- Name: test_cases test_cases_user_story_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_cases
    ADD CONSTRAINT test_cases_user_story_id_fkey FOREIGN KEY (user_story_id) REFERENCES qastraschema.user_stories(id);


--
-- TOC entry 5179 (class 2606 OID 211603)
-- Name: test_recommendation_runs test_recommendation_runs_created_by_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_recommendation_runs
    ADD CONSTRAINT test_recommendation_runs_created_by_fkey FOREIGN KEY (created_by) REFERENCES qastraschema.users(id) ON DELETE SET NULL;


--
-- TOC entry 5180 (class 2606 OID 211608)
-- Name: test_recommendation_runs test_recommendation_runs_project_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_recommendation_runs
    ADD CONSTRAINT test_recommendation_runs_project_id_fkey FOREIGN KEY (project_id) REFERENCES qastraschema.projects(id) ON DELETE CASCADE;


--
-- TOC entry 5181 (class 2606 OID 211613)
-- Name: test_recommendation_runs test_recommendation_runs_requirement_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_recommendation_runs
    ADD CONSTRAINT test_recommendation_runs_requirement_id_fkey FOREIGN KEY (requirement_id) REFERENCES qastraschema.requirements(id) ON DELETE CASCADE;


--
-- TOC entry 5172 (class 2606 OID 211470)
-- Name: test_results test_results_test_case_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_results
    ADD CONSTRAINT test_results_test_case_id_fkey FOREIGN KEY (test_case_id) REFERENCES qastraschema.test_cases(id);


--
-- TOC entry 5173 (class 2606 OID 211465)
-- Name: test_results test_results_test_run_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_results
    ADD CONSTRAINT test_results_test_run_id_fkey FOREIGN KEY (test_run_id) REFERENCES qastraschema.test_runs(id) ON DELETE CASCADE;


--
-- TOC entry 5170 (class 2606 OID 211437)
-- Name: test_runs test_runs_project_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_runs
    ADD CONSTRAINT test_runs_project_id_fkey FOREIGN KEY (project_id) REFERENCES qastraschema.projects(id);


--
-- TOC entry 5171 (class 2606 OID 211442)
-- Name: test_runs test_runs_triggered_by_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_runs
    ADD CONSTRAINT test_runs_triggered_by_fkey FOREIGN KEY (triggered_by) REFERENCES qastraschema.users(id);


--
-- TOC entry 5169 (class 2606 OID 211409)
-- Name: test_steps test_steps_test_case_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.test_steps
    ADD CONSTRAINT test_steps_test_case_id_fkey FOREIGN KEY (test_case_id) REFERENCES qastraschema.test_cases(id) ON DELETE CASCADE;


--
-- TOC entry 5162 (class 2606 OID 211314)
-- Name: user_stories user_stories_integration_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.user_stories
    ADD CONSTRAINT user_stories_integration_id_fkey FOREIGN KEY (integration_id) REFERENCES qastraschema.project_integrations(id) ON DELETE SET NULL;


--
-- TOC entry 5163 (class 2606 OID 211309)
-- Name: user_stories user_stories_project_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.user_stories
    ADD CONSTRAINT user_stories_project_id_fkey FOREIGN KEY (project_id) REFERENCES qastraschema.projects(id) ON DELETE CASCADE;


--
-- TOC entry 5157 (class 2606 OID 211211)
-- Name: users users_organization_id_fkey; Type: FK CONSTRAINT; Schema: qastraschema; Owner: qastra
--

ALTER TABLE ONLY qastraschema.users
    ADD CONSTRAINT users_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES qastraschema.organizations(id);


--
-- TOC entry 2184 (class 826 OID 210965)
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: qastraschema; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA qastraschema GRANT ALL ON SEQUENCES TO qastra;


--
-- TOC entry 2185 (class 826 OID 210966)
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: qastraschema; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA qastraschema GRANT ALL ON FUNCTIONS TO qastra;


--
-- TOC entry 2183 (class 826 OID 210964)
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: qastraschema; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA qastraschema GRANT ALL ON TABLES TO qastra;


-- Completed on 2026-05-19 12:10:29

--
-- PostgreSQL database dump complete
--

\unrestrict oS7EXPb1g91gGhpt1fps0UCYPcIrL9amxmIYwAfaUOtWoydmC773bPpmmZAUitJ

