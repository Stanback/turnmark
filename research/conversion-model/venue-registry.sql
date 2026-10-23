-- Local research sidecar. Physical pools, dated configurations and race mappings
-- are distinct; club locations and meet names never establish pool identity.
CREATE TABLE venue_sources (
    source_id VARCHAR PRIMARY KEY,
    source_url VARCHAR NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL,
    content_sha256 VARCHAR NOT NULL CHECK (length(content_sha256)=64),
    reuse_notes VARCHAR NOT NULL
);
CREATE TABLE facilities (
    facility_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    country VARCHAR,
    state VARCHAR,
    city VARCHAR,
    evidence_source_id VARCHAR NOT NULL REFERENCES venue_sources(source_id)
);
CREATE TABLE pools (
    pool_id VARCHAR PRIMARY KEY,
    facility_id VARCHAR NOT NULL REFERENCES facilities(facility_id),
    name VARCHAR NOT NULL,
    elevation_m DOUBLE,
    elevation_uncertainty_m DOUBLE,
    elevation_source_id VARCHAR REFERENCES venue_sources(source_id),
    evidence_source_id VARCHAR NOT NULL REFERENCES venue_sources(source_id),
    CHECK (elevation_m IS NULL OR isfinite(elevation_m)),
    CHECK (elevation_uncertainty_m IS NULL OR
           (isfinite(elevation_uncertainty_m) AND elevation_uncertainty_m>=0)),
    CHECK ((elevation_m IS NULL AND elevation_source_id IS NULL AND elevation_uncertainty_m IS NULL)
        OR (elevation_m IS NOT NULL AND elevation_source_id IS NOT NULL))
);
CREATE TABLE pool_configurations (
    configuration_id VARCHAR PRIMARY KEY,
    pool_id VARCHAR NOT NULL REFERENCES pools(pool_id),
    course VARCHAR NOT NULL CHECK (course IN ('SCY','SCM','LCM')),
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL,
    evidence_source_id VARCHAR NOT NULL REFERENCES venue_sources(source_id),
    CHECK (valid_to>=valid_from)
);
CREATE TABLE race_venues (
    source VARCHAR NOT NULL,
    race_id VARCHAR NOT NULL,
    configuration_id VARCHAR NOT NULL REFERENCES pool_configurations(configuration_id),
    time_basis VARCHAR NOT NULL CHECK (time_basis IN ('raw','altitude_adjusted','unknown')),
    evidence_source_id VARCHAR NOT NULL REFERENCES venue_sources(source_id),
    PRIMARY KEY (source,race_id)
);
