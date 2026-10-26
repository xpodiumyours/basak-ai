CREATE SCHEMA IF NOT EXISTS basak_gateway;
REVOKE ALL ON SCHEMA basak_gateway FROM PUBLIC;

CREATE TABLE IF NOT EXISTS basak_gateway.encrypted_backup (
    name TEXT PRIMARY KEY CHECK (name = 'freellmapi-v1'),
    payload BYTEA NOT NULL CHECK (octet_length(payload) <= 4194304),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
REVOKE ALL ON TABLE basak_gateway.encrypted_backup FROM PUBLIC;
