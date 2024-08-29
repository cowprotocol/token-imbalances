INSERT INTO fees_new (
    chain_name, auction_id, block_number, tx_hash, order_uid, token_address, fee_amount,fee_type
) VALUES ( :chain_name, :auction_id, :block_number, :tx_hash, :order_uid, :token_address, :fee_amount, :fee_type
);
