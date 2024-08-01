SELECT MAX(block_number) FROM raw_token_imbalances
WHERE chain_name = :chain_name;
