-- Six table definitions from the shipped TACTIC seed; login licensing column omitted.
CREATE TABLE search_object (
    id integer PRIMARY KEY AUTOINCREMENT,
    code character varying(256),
    search_type character varying(100) NOT NULL,
    namespace character varying(200) NOT NULL,
    description text,
    "database" character varying(100) NOT NULL,
    table_name character varying(100) NOT NULL,
    class_name character varying(100) NOT NULL,
    title character varying(100),
    "schema" character varying(100),
    color character varying(256),
    CONSTRAINT "search_object_code_idx" UNIQUE (code),
    CONSTRAINT "search_object_search_type_idx" UNIQUE (search_type)
);

CREATE TABLE project (
    id integer PRIMARY KEY AUTOINCREMENT,
    code character varying(30) NOT NULL,
    title character varying(100),
    sobject_mapping_cls character varying(100),
    dir_naming_cls character varying(200),
    code_naming_cls character varying(200),
    pipeline character varying(30),
    snapshot text,
    "type" character varying(30),
    last_db_update timestamp without time zone,
    description text,
    initials character varying(30),
    file_naming_cls character varying(200),
    reg_hours numeric,
    node_naming_cls character varying(200),
    s_status character varying(30),
    status character varying(256),
    last_version_update character varying(256),
    palette character varying(256),
    category character varying(256),
    is_template boolean,
    db_resource text,
    CONSTRAINT "project_code_idx" UNIQUE (code)
);

CREATE TABLE "login" (
    id integer PRIMARY KEY AUTOINCREMENT,
    code character varying(512),
    "login" character varying(100) NOT NULL,
    "password" character varying(255),
    login_groups text,
    first_name character varying(100),
    last_name character varying(100),
    email character varying(200),
    phone_number character varying(32),
    department character varying(256),
    namespace character varying(255),
    snapshot text,
    s_status character varying(30),
    project_code text,
    hourly_wage float,
    CONSTRAINT "login_code_idx" UNIQUE (code)
);

CREATE TABLE login_group (
    id integer PRIMARY KEY AUTOINCREMENT,
    code character varying(256),
    login_group character varying(100) NOT NULL,
    sub_groups text,
    access_rules text,
    redirect_url text,
    namespace character varying(255),
    description text,
    project_code text,
    s_status character varying(256),
    start_link text,
    access_level varchar(32),
    CONSTRAINT "login_group_code_idx" UNIQUE (code)
);

CREATE TABLE login_in_group (
    id integer PRIMARY KEY AUTOINCREMENT,
    code character varying(256),
    "login" character varying(100) NOT NULL,
    login_group character varying(100) NOT NULL
);

CREATE TABLE ticket (
    id integer PRIMARY KEY AUTOINCREMENT,
    code character varying(256),
    ticket character varying(100) NOT NULL,
    "login" character varying(100),
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    expiry timestamp without time zone,
    category character varying(256),
    CONSTRAINT "ticket_code_idx" UNIQUE (code),
    CONSTRAINT "ticket_ticket_idx" UNIQUE (ticket)
);
