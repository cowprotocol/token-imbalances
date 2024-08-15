"""Contract ABI of the CoW Protocol settlement contract
"""

gpv2_settlement_abi = [
    {
        "inputs": [
            {
                "internalType": "contract GPv2Authentication",
                "name": "authenticator_",
                "type": "address",
            },
            {"internalType": "contract IVault", "name": "vault_", "type": "address"},
        ],
        "stateMutability": "nonpayable",
        "type": "constructor",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "target",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "value",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "bytes4",
                "name": "selector",
                "type": "bytes4",
            },
        ],
        "name": "Interaction",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "owner",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "bytes",
                "name": "orderUid",
                "type": "bytes",
            },
        ],
        "name": "OrderInvalidated",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "owner",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "bytes",
                "name": "orderUid",
                "type": "bytes",
            },
            {
                "indexed": False,
                "internalType": "bool",
                "name": "signed",
                "type": "bool",
            },
        ],
        "name": "PreSignature",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "solver",
                "type": "address",
            }
        ],
        "name": "Settlement",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "owner",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "contract IERC20",
                "name": "sellToken",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "contract IERC20",
                "name": "buyToken",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "sellAmount",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "buyAmount",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "feeAmount",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "bytes",
                "name": "orderUid",
                "type": "bytes",
            },
        ],
        "name": "Trade",
        "type": "event",
    },
    {
        "inputs": [],
        "name": "authenticator",
        "outputs": [
            {
                "internalType": "contract GPv2Authentication",
                "name": "",
                "type": "address",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "domainSeparator",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes", "name": "", "type": "bytes"}],
        "name": "filledAmount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes[]", "name": "orderUids", "type": "bytes[]"}],
        "name": "freeFilledAmountStorage",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes[]", "name": "orderUids", "type": "bytes[]"}],
        "name": "freePreSignatureStorage",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "offset", "type": "uint256"},
            {"internalType": "uint256", "name": "length", "type": "uint256"},
        ],
        "name": "getStorageAt",
        "outputs": [{"internalType": "bytes", "name": "", "type": "bytes"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes", "name": "orderUid", "type": "bytes"}],
        "name": "invalidateOrder",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes", "name": "", "type": "bytes"}],
        "name": "preSignature",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes", "name": "orderUid", "type": "bytes"},
            {"internalType": "bool", "name": "signed", "type": "bool"},
        ],
        "name": "setPreSignature",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "internalType": "contract IERC20[]",
                "name": "tokens",
                "type": "address[]",
            },
            {
                "internalType": "uint256[]",
                "name": "clearingPrices",
                "type": "uint256[]",
            },
            {
                "components": [
                    {
                        "internalType": "uint256",
                        "name": "sellTokenIndex",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "buyTokenIndex",
                        "type": "uint256",
                    },
                    {"internalType": "address", "name": "receiver", "type": "address"},
                    {
                        "internalType": "uint256",
                        "name": "sellAmount",
                        "type": "uint256",
                    },
                    {"internalType": "uint256", "name": "buyAmount", "type": "uint256"},
                    {"internalType": "uint32", "name": "validTo", "type": "uint32"},
                    {"internalType": "bytes32", "name": "appData", "type": "bytes32"},
                    {"internalType": "uint256", "name": "feeAmount", "type": "uint256"},
                    {"internalType": "uint256", "name": "flags", "type": "uint256"},
                    {
                        "internalType": "uint256",
                        "name": "executedAmount",
                        "type": "uint256",
                    },
                    {"internalType": "bytes", "name": "signature", "type": "bytes"},
                ],
                "internalType": "struct GPv2Trade.Data[]",
                "name": "trades",
                "type": "tuple[]",
            },
            {
                "components": [
                    {"internalType": "address", "name": "target", "type": "address"},
                    {"internalType": "uint256", "name": "value", "type": "uint256"},
                    {"internalType": "bytes", "name": "callData", "type": "bytes"},
                ],
                "internalType": "struct GPv2Interaction.Data[][3]",
                "name": "interactions",
                "type": "tuple[][3]",
            },
        ],
        "name": "settle",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "targetContract", "type": "address"},
            {"internalType": "bytes", "name": "calldataPayload", "type": "bytes"},
        ],
        "name": "simulateDelegatecall",
        "outputs": [{"internalType": "bytes", "name": "response", "type": "bytes"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "targetContract", "type": "address"},
            {"internalType": "bytes", "name": "calldataPayload", "type": "bytes"},
        ],
        "name": "simulateDelegatecallInternal",
        "outputs": [{"internalType": "bytes", "name": "response", "type": "bytes"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "bytes32", "name": "poolId", "type": "bytes32"},
                    {
                        "internalType": "uint256",
                        "name": "assetInIndex",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "assetOutIndex",
                        "type": "uint256",
                    },
                    {"internalType": "uint256", "name": "amount", "type": "uint256"},
                    {"internalType": "bytes", "name": "userData", "type": "bytes"},
                ],
                "internalType": "struct IVault.BatchSwapStep[]",
                "name": "swaps",
                "type": "tuple[]",
            },
            {
                "internalType": "contract IERC20[]",
                "name": "tokens",
                "type": "address[]",
            },
            {
                "components": [
                    {
                        "internalType": "uint256",
                        "name": "sellTokenIndex",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "buyTokenIndex",
                        "type": "uint256",
                    },
                    {"internalType": "address", "name": "receiver", "type": "address"},
                    {
                        "internalType": "uint256",
                        "name": "sellAmount",
                        "type": "uint256",
                    },
                    {"internalType": "uint256", "name": "buyAmount", "type": "uint256"},
                    {"internalType": "uint32", "name": "validTo", "type": "uint32"},
                    {"internalType": "bytes32", "name": "appData", "type": "bytes32"},
                    {"internalType": "uint256", "name": "feeAmount", "type": "uint256"},
                    {"internalType": "uint256", "name": "flags", "type": "uint256"},
                    {
                        "internalType": "uint256",
                        "name": "executedAmount",
                        "type": "uint256",
                    },
                    {"internalType": "bytes", "name": "signature", "type": "bytes"},
                ],
                "internalType": "struct GPv2Trade.Data",
                "name": "trade",
                "type": "tuple",
            },
        ],
        "name": "swap",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "vault",
        "outputs": [{"internalType": "contract IVault", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "vaultRelayer",
        "outputs": [
            {"internalType": "contract GPv2VaultRelayer", "name": "", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {"stateMutability": "payable", "type": "receive"},
]