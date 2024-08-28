-- Database Schema for Token Imbalances and Slippage

-- Table: raw_token_imbalances (for storing raw token imbalances)
CREATE TABLE raw_token_imbalances (
    auction_id BIGINT NOT NULL,
    chain_name VARCHAR(50) NOT NULL,
    block_number BIGINT NOT NULL,
    tx_hash BYTEA NOT NULL,
    token_address BYTEA NOT NULL,
    imbalance NUMERIC(78,0)
);

-- Table: slippage_prices (for storing per unit token prices in ETH)
CREATE TABLE slippage_prices (
    chain_name VARCHAR(50) NOT NULL,
    source VARCHAR(50) NOT NULL,
    block_number BIGINT NOT NULL,
    tx_hash BYTEA NOT NULL,
    token_address BYTEA NOT NULL,
    price NUMERIC(42,18),
    PRIMARY KEY (tx_hash, token_address)
);

-- Table: Stores fees (i.e. protocol fee, network fee on per token basis)
CREATE TABLE fees_new (
    chain_name VARCHAR(50) NOT NULL,
    auction_id BIGINT NOT NULL,
    block_number BIGINT NOT NULL,
    tx_hash BYTEA NOT NULL,
    order_uid BYTEA NOT NULL,
    token_address BYTEA NOT NULL,
    fee_amount NUMERIC(78,0) NOT NULL,
    fee_type VARCHAR(50) NOT NULL, -- e.g. "protocol" or "network"
    PRIMARY KEY (tx_hash, order_uid, token_address, fee_type)
);

