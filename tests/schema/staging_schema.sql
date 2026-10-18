-- Structure of ftd_lakehouse_staging (pg_dump --schema-only, 2026-10-18). No data.
-- Used only to build the throwaway Postgres for db_integration tests (tests/schema/setup_test_db.sh).
-- Refresh: pg_dump --schema-only on ftd-staging-api with the ftd-api service's PG env, then drop the \restrict lines.
--
-- PostgreSQL database dump
--


-- Dumped from database version 15.19 (Debian 15.19-0+deb12u1)
-- Dumped by pg_dump version 15.19 (Debian 15.19-0+deb12u1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: update_alert_subscriptions_updated_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_alert_subscriptions_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_alert_subscriptions_updated_at() OWNER TO postgres;

--
-- Name: update_users_updated_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_users_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_users_updated_at() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alert_subscription_state; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alert_subscription_state (
    subscription_id integer NOT NULL,
    last_observed_value text,
    last_observed_label text,
    last_evaluated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_alerted_at timestamp with time zone
);


ALTER TABLE public.alert_subscription_state OWNER TO postgres;

--
-- Name: alert_subscriptions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alert_subscriptions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    ticker text NOT NULL,
    alert_type text NOT NULL,
    threshold numeric,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.alert_subscriptions OWNER TO postgres;

--
-- Name: alert_subscriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.alert_subscriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.alert_subscriptions_id_seq OWNER TO postgres;

--
-- Name: alert_subscriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.alert_subscriptions_id_seq OWNED BY public.alert_subscriptions.id;


--
-- Name: alerts; Type: TABLE; Schema: public; Owner: ftd_app
--

CREATE TABLE public.alerts (
    id integer NOT NULL,
    user_id integer,
    ticker text,
    type text NOT NULL,
    message text NOT NULL,
    read boolean DEFAULT false,
    severity text DEFAULT 'medium'::text,
    created_at timestamp without time zone DEFAULT now(),
    subscription_id integer
);


ALTER TABLE public.alerts OWNER TO ftd_app;

--
-- Name: alerts_id_seq; Type: SEQUENCE; Schema: public; Owner: ftd_app
--

CREATE SEQUENCE public.alerts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.alerts_id_seq OWNER TO ftd_app;

--
-- Name: alerts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ftd_app
--

ALTER SEQUENCE public.alerts_id_seq OWNED BY public.alerts.id;


--
-- Name: api_usage_log; Type: TABLE; Schema: public; Owner: ftd_app
--

CREATE TABLE public.api_usage_log (
    id integer NOT NULL,
    user_key text NOT NULL,
    auth_method text NOT NULL,
    endpoint text NOT NULL,
    http_method text NOT NULL,
    query_params jsonb,
    path_params jsonb,
    request_body jsonb,
    response_status integer NOT NULL,
    response_time_ms integer,
    requested_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.api_usage_log OWNER TO ftd_app;

--
-- Name: TABLE api_usage_log; Type: COMMENT; Schema: public; Owner: ftd_app
--

COMMENT ON TABLE public.api_usage_log IS 'Audit log for authenticated API requests (Layer 10)';


--
-- Name: api_usage_log_id_seq; Type: SEQUENCE; Schema: public; Owner: ftd_app
--

CREATE SEQUENCE public.api_usage_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.api_usage_log_id_seq OWNER TO ftd_app;

--
-- Name: api_usage_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ftd_app
--

ALTER SEQUENCE public.api_usage_log_id_seq OWNED BY public.api_usage_log.id;


--
-- Name: fiscal_parameters; Type: TABLE; Schema: public; Owner: ftd_app
--

CREATE TABLE public.fiscal_parameters (
    target_cik text,
    fiscal_year_end_date text,
    source_accession text,
    extracted_at text
);


ALTER TABLE public.fiscal_parameters OWNER TO ftd_app;

--
-- Name: permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.permissions (
    id integer NOT NULL,
    name text NOT NULL,
    description text
);


ALTER TABLE public.permissions OWNER TO postgres;

--
-- Name: permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.permissions_id_seq OWNER TO postgres;

--
-- Name: permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.permissions_id_seq OWNED BY public.permissions.id;


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.schema_migrations (
    migration_id character varying(10) NOT NULL,
    applied_at timestamp with time zone DEFAULT now() NOT NULL,
    success boolean DEFAULT true NOT NULL
);


ALTER TABLE public.schema_migrations OWNER TO postgres;

--
-- Name: sec_vectorized_chunks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sec_vectorized_chunks (
    id bigint NOT NULL,
    ticker text,
    cik text,
    accession_number text,
    form_type text,
    filing_date date,
    chunk_index integer NOT NULL,
    text_preview text,
    vector jsonb,
    source_bucket text,
    source_object text,
    vectorized_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.sec_vectorized_chunks OWNER TO postgres;

--
-- Name: sec_vectorized_chunks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.sec_vectorized_chunks_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sec_vectorized_chunks_id_seq OWNER TO postgres;

--
-- Name: sec_vectorized_chunks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.sec_vectorized_chunks_id_seq OWNED BY public.sec_vectorized_chunks.id;


--
-- Name: staging_finnhub; Type: TABLE; Schema: public; Owner: ftd_app
--

CREATE TABLE public.staging_finnhub (
    target_ticker text,
    target_cik text,
    element_type text,
    content_body text,
    normalized_calendar_date timestamp without time zone,
    ingest_date timestamp without time zone,
    symbol text,
    "timestamp" timestamp without time zone,
    current numeric,
    change numeric,
    percent_change numeric,
    high numeric,
    low numeric,
    open numeric,
    previous_close numeric
);


ALTER TABLE public.staging_finnhub OWNER TO ftd_app;

--
-- Name: staging_finnhub_cik_backup_20261016; Type: TABLE; Schema: public; Owner: ftd_app
--

CREATE TABLE public.staging_finnhub_cik_backup_20261016 (
    target_ticker text,
    target_cik text,
    element_type text,
    content_body text,
    normalized_calendar_date timestamp without time zone,
    ingest_date timestamp without time zone,
    symbol text,
    "timestamp" timestamp without time zone,
    current numeric,
    change numeric,
    percent_change numeric,
    high numeric,
    low numeric,
    open numeric,
    previous_close numeric
);


ALTER TABLE public.staging_finnhub_cik_backup_20261016 OWNER TO ftd_app;

--
-- Name: staging_gnews; Type: TABLE; Schema: public; Owner: ftd_app
--

CREATE TABLE public.staging_gnews (
    target_ticker text,
    target_cik text,
    element_type text,
    content_body text,
    normalized_calendar_date timestamp without time zone,
    ingest_date timestamp without time zone,
    url text
);


ALTER TABLE public.staging_gnews OWNER TO ftd_app;

--
-- Name: staging_gnews_cik_backup_20261016; Type: TABLE; Schema: public; Owner: ftd_app
--

CREATE TABLE public.staging_gnews_cik_backup_20261016 (
    target_ticker text,
    target_cik text,
    element_type text,
    content_body text,
    normalized_calendar_date timestamp without time zone,
    ingest_date timestamp without time zone,
    url text
);


ALTER TABLE public.staging_gnews_cik_backup_20261016 OWNER TO ftd_app;

--
-- Name: staging_gnews_dupes_backup_20261016; Type: TABLE; Schema: public; Owner: ftd_app
--

CREATE TABLE public.staging_gnews_dupes_backup_20261016 (
    target_ticker text,
    target_cik text,
    element_type text,
    content_body text,
    normalized_calendar_date timestamp without time zone,
    ingest_date timestamp without time zone,
    url text
);


ALTER TABLE public.staging_gnews_dupes_backup_20261016 OWNER TO ftd_app;

--
-- Name: staging_sec_archive; Type: TABLE; Schema: public; Owner: ftd_app
--

CREATE TABLE public.staging_sec_archive (
    target_ticker text,
    target_cik text,
    element_type text,
    content_body text,
    normalized_calendar_date timestamp without time zone,
    ingest_date timestamp without time zone,
    element_id text,
    accession_number text,
    form_type text,
    item_number text,
    content_type text,
    raw_text_string text,
    period_of_report text,
    filing_date timestamp without time zone,
    date_precision text
);


ALTER TABLE public.staging_sec_archive OWNER TO ftd_app;

--
-- Name: TABLE staging_sec_archive; Type: COMMENT; Schema: public; Owner: ftd_app
--

COMMENT ON TABLE public.staging_sec_archive IS 'Renamed from staging_sec during Layer 11 decommission (2026-10-12)';


--
-- Name: staging_sec; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.staging_sec AS
 SELECT staging_sec_archive.target_ticker,
    staging_sec_archive.target_cik,
    staging_sec_archive.element_type,
    staging_sec_archive.content_body,
    staging_sec_archive.normalized_calendar_date,
    staging_sec_archive.ingest_date,
    staging_sec_archive.element_id,
    staging_sec_archive.accession_number,
    staging_sec_archive.form_type,
    staging_sec_archive.item_number,
    staging_sec_archive.content_type,
    staging_sec_archive.raw_text_string,
    staging_sec_archive.period_of_report,
    staging_sec_archive.filing_date,
    staging_sec_archive.date_precision
   FROM public.staging_sec_archive
  WHERE false;


ALTER TABLE public.staging_sec OWNER TO postgres;

--
-- Name: tickers; Type: TABLE; Schema: public; Owner: ftd_app
--

CREATE TABLE public.tickers (
    symbol text NOT NULL,
    name text NOT NULL,
    sector text,
    current_price numeric(12,2),
    evidence_score numeric(5,2),
    hype_score numeric(5,2),
    change_percent numeric(6,2),
    updated_at timestamp without time zone DEFAULT now(),
    price_as_of timestamp without time zone
);


ALTER TABLE public.tickers OWNER TO ftd_app;

--
-- Name: unified_staging_archive; Type: TABLE; Schema: public; Owner: ftd_app
--

CREATE TABLE public.unified_staging_archive (
    target_ticker text,
    target_cik text,
    element_type text,
    content_body text,
    normalized_calendar_date timestamp without time zone,
    ingest_date timestamp without time zone,
    symbol text,
    "timestamp" timestamp without time zone,
    current numeric,
    change numeric,
    percent_change numeric,
    high numeric,
    low numeric,
    open numeric,
    previous_close numeric,
    source text,
    form_type text,
    element_id text,
    accession_number text,
    item_number text,
    content_type text,
    raw_text_string text,
    period_of_report text,
    filing_date timestamp without time zone,
    date_precision text
);


ALTER TABLE public.unified_staging_archive OWNER TO ftd_app;

--
-- Name: TABLE unified_staging_archive; Type: COMMENT; Schema: public; Owner: ftd_app
--

COMMENT ON TABLE public.unified_staging_archive IS 'Renamed from unified_staging during Layer 11 decommission (2026-10-12)';


--
-- Name: unified_staging; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.unified_staging AS
 SELECT unified_staging_archive.target_ticker,
    unified_staging_archive.target_cik,
    unified_staging_archive.element_type,
    unified_staging_archive.content_body,
    unified_staging_archive.normalized_calendar_date,
    unified_staging_archive.ingest_date,
    unified_staging_archive.symbol,
    unified_staging_archive."timestamp",
    unified_staging_archive.current,
    unified_staging_archive.change,
    unified_staging_archive.percent_change,
    unified_staging_archive.high,
    unified_staging_archive.low,
    unified_staging_archive.open,
    unified_staging_archive.previous_close,
    unified_staging_archive.source,
    unified_staging_archive.form_type,
    unified_staging_archive.element_id,
    unified_staging_archive.accession_number,
    unified_staging_archive.item_number,
    unified_staging_archive.content_type,
    unified_staging_archive.raw_text_string,
    unified_staging_archive.period_of_report,
    unified_staging_archive.filing_date,
    unified_staging_archive.date_precision
   FROM public.unified_staging_archive
  WHERE false;


ALTER TABLE public.unified_staging OWNER TO postgres;

--
-- Name: user_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_permissions (
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.user_permissions OWNER TO postgres;

--
-- Name: user_permissions_index; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_permissions_index (
    user_id integer NOT NULL,
    permission_name text NOT NULL
);


ALTER TABLE public.user_permissions_index OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email text NOT NULL,
    password_hash text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    firebase_uid text,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: workspace_tickers; Type: TABLE; Schema: public; Owner: ftd_app
--

CREATE TABLE public.workspace_tickers (
    workspace_id integer NOT NULL,
    ticker_symbol text NOT NULL
);


ALTER TABLE public.workspace_tickers OWNER TO ftd_app;

--
-- Name: workspaces; Type: TABLE; Schema: public; Owner: ftd_app
--

CREATE TABLE public.workspaces (
    id integer NOT NULL,
    user_id integer,
    name text NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.workspaces OWNER TO ftd_app;

--
-- Name: workspaces_id_seq; Type: SEQUENCE; Schema: public; Owner: ftd_app
--

CREATE SEQUENCE public.workspaces_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.workspaces_id_seq OWNER TO ftd_app;

--
-- Name: workspaces_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ftd_app
--

ALTER SEQUENCE public.workspaces_id_seq OWNED BY public.workspaces.id;


--
-- Name: alert_subscriptions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alert_subscriptions ALTER COLUMN id SET DEFAULT nextval('public.alert_subscriptions_id_seq'::regclass);


--
-- Name: alerts id; Type: DEFAULT; Schema: public; Owner: ftd_app
--

ALTER TABLE ONLY public.alerts ALTER COLUMN id SET DEFAULT nextval('public.alerts_id_seq'::regclass);


--
-- Name: api_usage_log id; Type: DEFAULT; Schema: public; Owner: ftd_app
--

ALTER TABLE ONLY public.api_usage_log ALTER COLUMN id SET DEFAULT nextval('public.api_usage_log_id_seq'::regclass);


--
-- Name: permissions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions ALTER COLUMN id SET DEFAULT nextval('public.permissions_id_seq'::regclass);


--
-- Name: sec_vectorized_chunks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sec_vectorized_chunks ALTER COLUMN id SET DEFAULT nextval('public.sec_vectorized_chunks_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: workspaces id; Type: DEFAULT; Schema: public; Owner: ftd_app
--

ALTER TABLE ONLY public.workspaces ALTER COLUMN id SET DEFAULT nextval('public.workspaces_id_seq'::regclass);


--
-- Name: alert_subscription_state alert_subscription_state_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alert_subscription_state
    ADD CONSTRAINT alert_subscription_state_pkey PRIMARY KEY (subscription_id);


--
-- Name: alert_subscriptions alert_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alert_subscriptions
    ADD CONSTRAINT alert_subscriptions_pkey PRIMARY KEY (id);


--
-- Name: alerts alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: ftd_app
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);


--
-- Name: api_usage_log api_usage_log_pkey; Type: CONSTRAINT; Schema: public; Owner: ftd_app
--

ALTER TABLE ONLY public.api_usage_log
    ADD CONSTRAINT api_usage_log_pkey PRIMARY KEY (id);


--
-- Name: permissions permissions_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_name_key UNIQUE (name);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (migration_id);


--
-- Name: sec_vectorized_chunks sec_vectorized_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sec_vectorized_chunks
    ADD CONSTRAINT sec_vectorized_chunks_pkey PRIMARY KEY (id);


--
-- Name: sec_vectorized_chunks sec_vectorized_chunks_source_object_chunk_index_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sec_vectorized_chunks
    ADD CONSTRAINT sec_vectorized_chunks_source_object_chunk_index_key UNIQUE (source_object, chunk_index);


--
-- Name: tickers tickers_pkey; Type: CONSTRAINT; Schema: public; Owner: ftd_app
--

ALTER TABLE ONLY public.tickers
    ADD CONSTRAINT tickers_pkey PRIMARY KEY (symbol);


--
-- Name: user_permissions user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_permissions
    ADD CONSTRAINT user_permissions_pkey PRIMARY KEY (user_id, permission_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_firebase_uid_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_firebase_uid_key UNIQUE (firebase_uid);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: workspace_tickers workspace_tickers_pkey; Type: CONSTRAINT; Schema: public; Owner: ftd_app
--

ALTER TABLE ONLY public.workspace_tickers
    ADD CONSTRAINT workspace_tickers_pkey PRIMARY KEY (workspace_id, ticker_symbol);


--
-- Name: workspaces workspaces_pkey; Type: CONSTRAINT; Schema: public; Owner: ftd_app
--

ALTER TABLE ONLY public.workspaces
    ADD CONSTRAINT workspaces_pkey PRIMARY KEY (id);


--
-- Name: idx_alert_subscriptions_ticker; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alert_subscriptions_ticker ON public.alert_subscriptions USING btree (ticker);


--
-- Name: idx_alert_subscriptions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alert_subscriptions_user_id ON public.alert_subscriptions USING btree (user_id);


--
-- Name: idx_alert_subscriptions_user_ticker_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_alert_subscriptions_user_ticker_type ON public.alert_subscriptions USING btree (user_id, ticker, alert_type);


--
-- Name: idx_alerts_created_at; Type: INDEX; Schema: public; Owner: ftd_app
--

CREATE INDEX idx_alerts_created_at ON public.alerts USING btree (created_at DESC);


--
-- Name: idx_alerts_subscription_id; Type: INDEX; Schema: public; Owner: ftd_app
--

CREATE INDEX idx_alerts_subscription_id ON public.alerts USING btree (subscription_id);


--
-- Name: idx_alerts_user_id; Type: INDEX; Schema: public; Owner: ftd_app
--

CREATE INDEX idx_alerts_user_id ON public.alerts USING btree (user_id);


--
-- Name: idx_api_usage_log_endpoint; Type: INDEX; Schema: public; Owner: ftd_app
--

CREATE INDEX idx_api_usage_log_endpoint ON public.api_usage_log USING btree (endpoint);


--
-- Name: idx_api_usage_log_requested_at; Type: INDEX; Schema: public; Owner: ftd_app
--

CREATE INDEX idx_api_usage_log_requested_at ON public.api_usage_log USING btree (requested_at);


--
-- Name: idx_api_usage_log_user_key; Type: INDEX; Schema: public; Owner: ftd_app
--

CREATE INDEX idx_api_usage_log_user_key ON public.api_usage_log USING btree (user_key);


--
-- Name: idx_sec_vectorized_chunks_accession; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sec_vectorized_chunks_accession ON public.sec_vectorized_chunks USING btree (accession_number);


--
-- Name: idx_sec_vectorized_chunks_cik; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sec_vectorized_chunks_cik ON public.sec_vectorized_chunks USING btree (cik);


--
-- Name: idx_sec_vectorized_chunks_source_object; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sec_vectorized_chunks_source_object ON public.sec_vectorized_chunks USING btree (source_object);


--
-- Name: idx_sec_vectorized_chunks_ticker; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sec_vectorized_chunks_ticker ON public.sec_vectorized_chunks USING btree (ticker);


--
-- Name: idx_tickers_sector; Type: INDEX; Schema: public; Owner: ftd_app
--

CREATE INDEX idx_tickers_sector ON public.tickers USING btree (sector);


--
-- Name: idx_unified_staging_target_ticker; Type: INDEX; Schema: public; Owner: ftd_app
--

CREATE INDEX idx_unified_staging_target_ticker ON public.unified_staging_archive USING btree (target_ticker);


--
-- Name: idx_unified_staging_target_ticker_trgm; Type: INDEX; Schema: public; Owner: ftd_app
--

CREATE INDEX idx_unified_staging_target_ticker_trgm ON public.unified_staging_archive USING gin (target_ticker public.gin_trgm_ops);


--
-- Name: idx_user_permissions_index_composite; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_permissions_index_composite ON public.user_permissions_index USING btree (user_id, permission_name);


--
-- Name: idx_user_permissions_index_permission_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_permissions_index_permission_name ON public.user_permissions_index USING btree (permission_name);


--
-- Name: idx_user_permissions_index_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_permissions_index_user_id ON public.user_permissions_index USING btree (user_id);


--
-- Name: idx_workspaces_user_id; Type: INDEX; Schema: public; Owner: ftd_app
--

CREATE INDEX idx_workspaces_user_id ON public.workspaces USING btree (user_id);


--
-- Name: alert_subscriptions trg_update_alert_subscriptions_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_update_alert_subscriptions_updated_at BEFORE UPDATE ON public.alert_subscriptions FOR EACH ROW EXECUTE FUNCTION public.update_alert_subscriptions_updated_at();


--
-- Name: users trg_update_users_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_users_updated_at();


--
-- Name: alert_subscription_state alert_subscription_state_subscription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alert_subscription_state
    ADD CONSTRAINT alert_subscription_state_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES public.alert_subscriptions(id);


--
-- Name: alert_subscriptions alert_subscriptions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alert_subscriptions
    ADD CONSTRAINT alert_subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: alerts alerts_subscription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ftd_app
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES public.alert_subscriptions(id);


--
-- Name: alerts alerts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ftd_app
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_permissions user_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_permissions
    ADD CONSTRAINT user_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(id) ON DELETE CASCADE;


--
-- Name: user_permissions user_permissions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_permissions
    ADD CONSTRAINT user_permissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: workspace_tickers workspace_tickers_ticker_symbol_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ftd_app
--

ALTER TABLE ONLY public.workspace_tickers
    ADD CONSTRAINT workspace_tickers_ticker_symbol_fkey FOREIGN KEY (ticker_symbol) REFERENCES public.tickers(symbol) ON DELETE CASCADE;


--
-- Name: workspace_tickers workspace_tickers_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ftd_app
--

ALTER TABLE ONLY public.workspace_tickers
    ADD CONSTRAINT workspace_tickers_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE CASCADE;


--
-- Name: workspaces workspaces_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ftd_app
--

ALTER TABLE ONLY public.workspaces
    ADD CONSTRAINT workspaces_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: FUNCTION update_alert_subscriptions_updated_at(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.update_alert_subscriptions_updated_at() TO ftd_app;


--
-- Name: TABLE alert_subscription_state; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.alert_subscription_state TO ftd_app;


--
-- Name: TABLE alert_subscriptions; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.alert_subscriptions TO ftd_app;


--
-- Name: SEQUENCE alert_subscriptions_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.alert_subscriptions_id_seq TO ftd_app;


--
-- Name: TABLE permissions; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.permissions TO ftd_app;


--
-- Name: SEQUENCE permissions_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.permissions_id_seq TO ftd_app;


--
-- Name: TABLE schema_migrations; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.schema_migrations TO ftd_app;


--
-- Name: TABLE sec_vectorized_chunks; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.sec_vectorized_chunks TO ftd_app;


--
-- Name: SEQUENCE sec_vectorized_chunks_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.sec_vectorized_chunks_id_seq TO ftd_app;


--
-- Name: TABLE staging_sec; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.staging_sec TO ftd_app;


--
-- Name: TABLE unified_staging; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.unified_staging TO ftd_app;


--
-- Name: TABLE user_permissions; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_permissions TO ftd_app;


--
-- Name: TABLE user_permissions_index; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_permissions_index TO ftd_app;


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.users TO ftd_app;


--
-- Name: SEQUENCE users_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.users_id_seq TO ftd_app;


--
-- PostgreSQL database dump complete
--


