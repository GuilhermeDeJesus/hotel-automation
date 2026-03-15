BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 5fa085db2e97

CREATE TABLE customers (
    id VARCHAR NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    phone VARCHAR(20), 
    email VARCHAR(255), 
    document VARCHAR(20), 
    status VARCHAR(20) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    UNIQUE (document)
);

CREATE INDEX ix_customers_name ON customers (name);

CREATE INDEX ix_customers_phone ON customers (phone);

CREATE INDEX ix_customers_email ON customers (email);

CREATE TABLE reservations (
    id VARCHAR NOT NULL, 
    guest_name VARCHAR(255) NOT NULL, 
    guest_phone VARCHAR(20) NOT NULL, 
    customer_id VARCHAR, 
    status VARCHAR(20) NOT NULL, 
    check_in_date DATE, 
    check_out_date DATE, 
    room_number VARCHAR(10), 
    total_amount FLOAT NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    checked_in_at TIMESTAMP WITHOUT TIME ZONE, 
    checked_out_at TIMESTAMP WITHOUT TIME ZONE, 
    updated_at TIMESTAMP WITHOUT TIME ZONE, 
    notes TEXT, 
    PRIMARY KEY (id), 
    FOREIGN KEY(customer_id) REFERENCES customers (id)
);

CREATE INDEX ix_reservations_guest_phone ON reservations (guest_phone);

CREATE INDEX ix_reservations_status ON reservations (status);

CREATE TABLE payments (
    id VARCHAR NOT NULL, 
    reservation_id VARCHAR NOT NULL, 
    amount FLOAT NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    payment_method VARCHAR(50), 
    transaction_id VARCHAR(255), 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    approved_at TIMESTAMP WITHOUT TIME ZONE, 
    expires_at TIMESTAMP WITHOUT TIME ZONE, 
    updated_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(reservation_id) REFERENCES reservations (id), 
    UNIQUE (transaction_id)
);

CREATE INDEX ix_payments_reservation_id ON payments (reservation_id);

CREATE INDEX ix_payments_status ON payments (status);

CREATE TABLE hotels (
    id VARCHAR NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    address VARCHAR(255) NOT NULL, 
    contact_phone VARCHAR(30) NOT NULL, 
    checkin_time VARCHAR(10) NOT NULL, 
    checkout_time VARCHAR(10) NOT NULL, 
    cancellation_policy TEXT NOT NULL, 
    pet_policy TEXT NOT NULL, 
    child_policy TEXT NOT NULL, 
    amenities TEXT NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id)
);

CREATE TABLE conversation_cache (
    id SERIAL NOT NULL, 
    phone_number VARCHAR(20) NOT NULL, 
    context_data TEXT, 
    last_message TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_conversation_cache_phone_number ON conversation_cache (phone_number);

INSERT INTO alembic_version (version_num) VALUES ('5fa085db2e97') RETURNING alembic_version.version_num;

-- Running upgrade 5fa085db2e97 -> 8b3c2e1f9c4a

CREATE TABLE saas_leads (
    id VARCHAR NOT NULL, 
    phone_number VARCHAR(20) NOT NULL, 
    source VARCHAR(20) NOT NULL, 
    stage VARCHAR(40) NOT NULL, 
    message_count INTEGER DEFAULT '0' NOT NULL, 
    first_seen_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    last_seen_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_saas_leads_phone_number ON saas_leads (phone_number);

CREATE INDEX ix_saas_leads_source ON saas_leads (source);

CREATE INDEX ix_saas_leads_stage ON saas_leads (stage);

CREATE INDEX ix_saas_leads_first_seen_at ON saas_leads (first_seen_at);

CREATE INDEX ix_saas_leads_last_seen_at ON saas_leads (last_seen_at);

CREATE TABLE saas_analytics_events (
    id SERIAL NOT NULL, 
    phone_number VARCHAR(20) NOT NULL, 
    source VARCHAR(20) NOT NULL, 
    event_type VARCHAR(50) NOT NULL, 
    success BOOLEAN DEFAULT true NOT NULL, 
    response_time_ms INTEGER, 
    details TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_saas_analytics_events_phone_number ON saas_analytics_events (phone_number);

CREATE INDEX ix_saas_analytics_events_source ON saas_analytics_events (source);

CREATE INDEX ix_saas_analytics_events_event_type ON saas_analytics_events (event_type);

CREATE INDEX ix_saas_analytics_events_created_at ON saas_analytics_events (created_at);

UPDATE alembic_version SET version_num='8b3c2e1f9c4a' WHERE alembic_version.version_num = '5fa085db2e97';

-- Running upgrade 8b3c2e1f9c4a -> 4e7b9c1a2f10

CREATE TABLE saas_admin_audit_events (
    id SERIAL NOT NULL, 
    event_type VARCHAR(80) NOT NULL, 
    client_ip VARCHAR(80) NOT NULL, 
    outcome VARCHAR(40) NOT NULL, 
    deleted_keys INTEGER, 
    retry_after INTEGER, 
    reason VARCHAR(120), 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_saas_admin_audit_events_event_type ON saas_admin_audit_events (event_type);

CREATE INDEX ix_saas_admin_audit_events_client_ip ON saas_admin_audit_events (client_ip);

CREATE INDEX ix_saas_admin_audit_events_outcome ON saas_admin_audit_events (outcome);

CREATE INDEX ix_saas_admin_audit_events_created_at ON saas_admin_audit_events (created_at);

UPDATE alembic_version SET version_num='4e7b9c1a2f10' WHERE alembic_version.version_num = '8b3c2e1f9c4a';

-- Running upgrade 4e7b9c1a2f10 -> 9a1c2d3e4f50

CREATE TABLE saas_audit_metrics_snapshots (
    id SERIAL NOT NULL, 
    snapshot_date DATE NOT NULL, 
    total_attempts INTEGER DEFAULT '0' NOT NULL, 
    rate_limited_count INTEGER DEFAULT '0' NOT NULL, 
    rate_limited_ratio FLOAT DEFAULT '0' NOT NULL, 
    alert_status VARCHAR(20) DEFAULT 'healthy' NOT NULL, 
    warning_threshold FLOAT DEFAULT '0.2' NOT NULL, 
    critical_threshold FLOAT DEFAULT '0.5' NOT NULL, 
    by_outcome_json TEXT DEFAULT '{}' NOT NULL, 
    top_ips_json TEXT DEFAULT '[]' NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_saas_audit_metrics_snapshots_snapshot_date ON saas_audit_metrics_snapshots (snapshot_date);

CREATE INDEX ix_saas_audit_metrics_snapshots_created_at ON saas_audit_metrics_snapshots (created_at);

UPDATE alembic_version SET version_num='9a1c2d3e4f50' WHERE alembic_version.version_num = '4e7b9c1a2f10';

-- Running upgrade 9a1c2d3e4f50 -> a1b2c3d4e5f6

ALTER TABLE hotels ADD COLUMN requires_payment_for_confirmation BOOLEAN DEFAULT false NOT NULL;

ALTER TABLE hotels ADD COLUMN allows_reservation_without_payment BOOLEAN DEFAULT true NOT NULL;

UPDATE alembic_version SET version_num='a1b2c3d4e5f6' WHERE alembic_version.version_num = '9a1c2d3e4f50';

-- Running upgrade a1b2c3d4e5f6 -> b2c3d4e5f6a1

