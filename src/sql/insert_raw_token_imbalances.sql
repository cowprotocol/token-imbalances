INSERT INTO raw_token_imbalances_temp
(auction_id, chain_name, block_number, tx_hash, token_address, imbalance)
VALUES 
(:auction_id, :chain_name, :block_number, :tx_hash, :token_address, :imbalance);
