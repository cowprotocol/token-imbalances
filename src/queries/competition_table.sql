SELECT
    id AS auction_id,
    sol.value AS solution,
    json->'auction' AS auction
FROM solver_competitions,
     jsonb_array_elements(json->'solutions') sol(value)
WHERE id = {{auction_id}}
    AND sol.value->>'solverAddress' = '{{solver}}'
    AND CAST(sol.value->>'ranking' AS INTEGER) = 1
