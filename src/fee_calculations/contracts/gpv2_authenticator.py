"""Contract ABI of the CoW Protocol allow list authenticator
"""

# pylint: disable=duplicate-code

gpv2_authenticator = [
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address",
                "name": "newManager",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "address",
                "name": "oldManager",
                "type": "address",
            },
        ],
        "name": "ManagerChanged",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address",
                "name": "solver",
                "type": "address",
            }
        ],
        "name": "SolverAdded",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address",
                "name": "solver",
                "type": "address",
            }
        ],
        "name": "SolverRemoved",
        "type": "event",
    },
    {
        "inputs": [{"internalType": "address", "name": "solver", "type": "address"}],
        "name": "addSolver",
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
        "inputs": [{"internalType": "address", "name": "manager_", "type": "address"}],
        "name": "initializeManager",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "prospectiveSolver", "type": "address"}
        ],
        "name": "isSolver",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "manager",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "solver", "type": "address"}],
        "name": "removeSolver",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "manager_", "type": "address"}],
        "name": "setManager",
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
]
