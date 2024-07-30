SELECT 1 FROM raw_token_imbalances
WHERE tx_hash = :tx_hash 
AND token_address = :token_address;
