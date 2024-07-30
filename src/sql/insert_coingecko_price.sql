INSERT INTO coingecko_prices 
(chain_name, block_number, tx_hash, token_address, coingecko_price)
VALUES 
(:chain_name, :block_number, :tx_hash, :token_address, :coingecko_price);
