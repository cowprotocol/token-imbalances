INSERT INTO fees_per_trade (
    chain_name, auction_id, block_number, tx_hash, order_uid, token_address, fee_amount, fee_type, fee_recipient
) VALUES ( :chain_name, :auction_id, :block_number, :tx_hash, :order_uid, :token_address, :fee_amount, :fee_type, :fee_recipient
);
