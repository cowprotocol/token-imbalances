INSERT INTO fees (
    chain_name, auction_id, block_number, tx_hash, token_address, fee_amount,fee_type
) VALUES ( :chain_name, :auction_id, :block_number, :tx_hash, :token_address, :fee_amount, :fee_type
);
