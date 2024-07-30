SELECT tx_hash, auction_id, block_number
FROM settlements
WHERE block_number >= :start_block
AND block_number <= :end_block;
