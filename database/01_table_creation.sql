CREATE TABLE transaction_timestamp (
    tx_hash bytea PRIMARY KEY,
    time timestamp NOT NULL
);

CREATE TABLE transaction_tokens (
    tx_hash bytea NOT NULL,
    token_address bytea NOT NULL,

    PRIMARY KEY (tx_hash, token_address)
);

CREATE TYPE PriceSource AS ENUM ('coingecko', 'moralis', 'dune', 'native');

CREATE TABLE prices (
    token_address bytea NOT NULL,
    time timestamp NOT NULL,
    price numeric(78, 18) NOT NULL,
    source PriceSource NOT NULL,

    PRIMARY KEY (token_address, time, source)
);

CREATE TABLE token_decimals (
    token_address bytea PRIMARY KEY,
    decimals int NOT NULL
);
