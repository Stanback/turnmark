-- Local DuckDB registry. Organizational metadata only; no athlete/coach roster.
-- A source observation is not automatically a verified current program.
CREATE TABLE registry_sources (
    source_id VARCHAR PRIMARY KEY,
    source_url VARCHAR NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    content_sha256 VARCHAR NOT NULL CHECK (length(content_sha256) = 64),
    reuse_notes VARCHAR NOT NULL
);

CREATE TABLE organizations (
    organization_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    organization_kind VARCHAR NOT NULL CHECK (
        organization_kind IN ('club', 'school', 'association', 'league', 'other', 'unknown')
    ),
    country VARCHAR NOT NULL,
    state VARCHAR,
    city VARCHAR,
    website VARCHAR,
    evidence_source_id VARCHAR NOT NULL REFERENCES registry_sources(source_id)
);

CREATE TABLE programs (
    program_id VARCHAR PRIMARY KEY,
    organization_id VARCHAR NOT NULL REFERENCES organizations(organization_id),
    name VARCHAR NOT NULL,
    program_kind VARCHAR NOT NULL CHECK (program_kind IN (
        'age_group', 'masters', 'collegiate_varsity', 'collegiate_club',
        'high_school', 'summer_league', 'learn_to_swim', 'other', 'unknown'
    )),
    discipline VARCHAR NOT NULL CHECK (discipline IN (
        'pool_swimming', 'open_water', 'swimming_and_diving', 'other', 'unknown'
    )),
    category VARCHAR NOT NULL CHECK (category IN ('women', 'men', 'mixed', 'unknown')),
    status VARCHAR NOT NULL CHECK (status IN ('active', 'inactive', 'unknown')),
    valid_from DATE,
    valid_to DATE,
    last_verified DATE NOT NULL,
    evidence_source_id VARCHAR NOT NULL REFERENCES registry_sources(source_id),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);

CREATE TABLE program_affiliations (
    affiliation_id VARCHAR PRIMARY KEY,
    program_id VARCHAR NOT NULL REFERENCES programs(program_id),
    authority VARCHAR NOT NULL,
    authority_id VARCHAR NOT NULL,
    jurisdiction VARCHAR,
    valid_from DATE,
    valid_to DATE,
    evidence_source_id VARCHAR NOT NULL REFERENCES registry_sources(source_id),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);

CREATE TABLE organization_aliases (
    organization_id VARCHAR NOT NULL REFERENCES organizations(organization_id),
    alias VARCHAR NOT NULL,
    valid_from DATE,
    valid_to DATE,
    evidence_source_id VARCHAR NOT NULL REFERENCES registry_sources(source_id)
);

CREATE TABLE team_observations (
    observation_id VARCHAR PRIMARY KEY,
    source_id VARCHAR NOT NULL REFERENCES registry_sources(source_id),
    source_team_code VARCHAR NOT NULL,
    observed_name VARCHAR NOT NULL,
    observed_abbreviation VARCHAR,
    observed_city VARCHAR,
    observed_state VARCHAR,
    observed_country VARCHAR,
    observed_on DATE,
    mapped_program_id VARCHAR REFERENCES programs(program_id),
    -- Keep unverified meet-file appearances distinct from directory membership.
    verification_status VARCHAR NOT NULL CHECK (
        verification_status IN ('observed_only', 'verified', 'rejected')
    ),
    CHECK (verification_status <> 'verified' OR mapped_program_id IS NOT NULL)
);

CREATE VIEW team_directory AS
SELECT p.program_id, o.organization_id, o.name AS organization_name,
       p.name AS program_name, p.program_kind, p.discipline, p.category,
       p.status, o.country, o.state, o.city, o.website, p.last_verified,
       p.valid_from, p.valid_to, s.source_url AS verification_url
FROM programs p
JOIN organizations o USING (organization_id)
JOIN registry_sources s ON s.source_id = p.evidence_source_id;

-- Optional graph projections, with stable namespaced node/edge keys. A graph
-- engine can read these relations without becoming the authoritative store.
CREATE VIEW registry_vertices AS
SELECT 'organization:' || organization_id AS vertex_id,
       'organization' AS label, name FROM organizations
UNION ALL
SELECT 'program:' || program_id, 'program', name FROM programs
UNION ALL
SELECT DISTINCT 'authority:' || authority, 'authority', authority FROM program_affiliations;

CREATE VIEW registry_edges AS
SELECT 'operates:' || program_id AS edge_id, 'operates' AS label,
       'organization:' || organization_id AS source_vertex,
       'program:' || program_id AS target_vertex,
       valid_from, valid_to FROM programs
UNION ALL
SELECT 'affiliation:' || affiliation_id, 'affiliated_with',
       'program:' || program_id, 'authority:' || authority,
       valid_from, valid_to FROM program_affiliations;
