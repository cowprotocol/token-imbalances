CREATE TABLE token_info (
    token_address bytea PRIMARY KEY,
    symbol varchar NOT NULL,
    decimals int NOT NULL
);

CREATE TABLE token_times (
    time timestamp NOT NULL,
    token_address bytea NOT NULL,
    block_number bigint NOT NULL,
    tx_hash bytea NOT NULL,

    PRIMARY KEY (time, token_address, tx_hash)
);

CREATE TABLE prices (
    time timestamp NOT NULL,
    token_address bytea NOT NULL,
    price numeric(60, 18) NOT NULL,
    source varchar NOT NULL,

    PRIMARY KEY (time, token_address, source)
);
