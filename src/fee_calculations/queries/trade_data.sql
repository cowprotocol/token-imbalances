WITH trade_data_raw AS MATERIALIZED (
    SELECT
        -- settlement
        s.auction_id,
        -- trade data
        concat('0x', encode(t.order_uid, 'hex')) as order_uid,
        t.sell_amount, -- the total amount the user sends
        t.buy_amount, -- the total amount the user receives
        -- quote data
        oq.sell_amount as quote_sell_amount,
        oq.buy_amount as quote_buy_amount,
        oq.gas_amount as quote_gas_amount,
        oq.gas_price as quote_gas_price,
        oq.sell_token_price as quote_sell_token_price,
        CASE WHEN oq.solver IS NULL THEN NULL
            ELSE concat('0x', encode(oq.solver, 'hex'))
        END AS quote_solver
    FROM
        settlements s
        JOIN settlement_scores ss -- this guarantees that prod and staging are distinguished
        ON ss.auction_id = s.auction_id AND ss.winner = s.solver
        JOIN trades t -- contains traded amounts
        ON s.block_number = t.block_number -- log_index cannot be checked, does not work correctly with multiple auctions on the same block
        LEFT OUTER JOIN order_quotes oq -- contains quote amounts
        ON t.order_uid = oq.order_uid
    WHERE
        s.auction_id = {{auction_id}} and concat('0x', encode(s.solver, 'hex')) = '{{solver}}'
),
trades_protocol_fee AS MATERIALIZED (
    SELECT
        auction_id,
        concat('0x', encode(order_uid, 'hex')) AS order_uid,
        array_agg(application_order) as application_order,
        array_agg(kind) as protocol_fee_kind,
        array_agg(surplus_factor) as surplus_factor,
        array_agg(surplus_max_volume_factor) as surplus_max_volume_factor,
        array_agg(volume_factor) as volume_factor,
        array_agg(price_improvement_factor) as price_improvement_factor,
        array_agg(price_improvement_max_volume_factor) as price_improvement_max_volume_factor
    FROM
        fee_policies
    WHERE auction_id = {{auction_id}}
    GROUP BY auction_id, order_uid
)

SELECT
    *
FROM
    trade_data_raw tdr
    LEFT OUTER JOIN trades_protocol_fee tpf
    USING (auction_id, order_uid)
