-- Create KYA Agent Registry Schema
CREATE SCHEMA IF NOT EXISTS kya_registry;
SET search_path TO kya_registry, public;

-- Enable UUID/Crypto Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enum Types
CREATE TYPE agent_status_enum AS ENUM (
    'PENDING_VERIFICATION',
    'ACTIVE',
    'SUSPENDED',
    'REVOKED'
);

CREATE TYPE key_algorithm_enum AS ENUM (
    'ED25519',
    'ECDSA_P256',
    'RSA_4096',
    'SECP256K1'
);

-- 1. Agents Table
CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(36) PRIMARY KEY,
    owner_organization VARCHAR(255) NOT NULL,
    status agent_status_enum NOT NULL DEFAULT 'ACTIVE',
    manifest JSONB NOT NULL,
    manifest_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ NULL,
    
    CONSTRAINT chk_agent_id_prefix CHECK (id LIKE 'kya_agt_%')
);

-- 2. Public Keys Table (Strictly NO Private Keys stored)
CREATE TABLE IF NOT EXISTS public_keys (
    key_id VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(36) NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    algorithm key_algorithm_enum NOT NULL,
    pem_content TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NULL,

    CONSTRAINT chk_no_private_key CHECK (
        pem_content NOT LIKE '%PRIVATE KEY%' AND
        pem_content NOT LIKE '%RSA PRIVATE KEY%' AND
        pem_content NOT LIKE '%EC PRIVATE KEY%'
    )
);

-- Indexes for Ultra-Fast Retrieval
CREATE INDEX IF NOT EXISTS idx_agents_owner_org ON agents(owner_organization);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_created_at ON agents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agents_manifest_gin ON agents USING GIN (manifest);
CREATE INDEX IF NOT EXISTS idx_public_keys_agent_id ON public_keys(agent_id);
