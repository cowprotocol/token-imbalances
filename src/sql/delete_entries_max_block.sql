BEGIN;

DELETE FROM raw_token_imbalances
WHERE chain_name = :chain_name 
AND block_number >= :block_number;

DELETE FROM slippage_prices
WHERE chain_name = :chain_name
AND block_number >= :block_number;

DELETE FROM fees
WHERE chain_name = :chain_name
AND block_number >= :block_number;
COMMIT;
