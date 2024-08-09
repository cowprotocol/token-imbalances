INSERT INTO slippage_prices 
(chain_name, source, block_number, tx_hash, token_address, price)
VALUES 
(:chain_name, :source, :block_number, :tx_hash, :token_address, :price);
