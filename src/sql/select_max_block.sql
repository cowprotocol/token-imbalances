SELECT 
    MIN(max_block_number) AS min_max_block_number
FROM (
    SELECT MAX(block_number) AS max_block_number 
    FROM raw_token_imbalances
    WHERE chain_name = :chain_name
    UNION ALL
    SELECT MAX(block_number) AS max_block_number 
    FROM slippage_prices
    WHERE chain_name = :chain_name
) AS max_blocks;
