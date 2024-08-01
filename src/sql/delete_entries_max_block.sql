DELETE FROM raw_token_imbalances
WHERE chain_name = :chain_name 
AND block_number = :block_number;
