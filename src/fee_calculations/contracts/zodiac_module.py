"""
Contract ABI of the Zodiac module that delegates the removeSolver call
"""

zodiac_module = [
    {
        "inputs": [
            {"internalType": "address", "name": "_owner", "type": "address"},
            {"internalType": "address", "name": "_avatar", "type": "address"},
            {"internalType": "address", "name": "_target", "type": "address"},
        ],
        "stateMutability": "nonpayable",
        "type": "constructor",
    },
    {"inputs": [], "name": "ArraysDifferentLength", "type": "error"},
    {"inputs": [], "name": "ModuleTransactionFailed", "type": "error"},
    {"inputs": [], "name": "NoMembership", "type": "error"},
    {"inputs": [], "name": "SetUpModulesAlreadyCalled", "type": "error"},
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address",
                "name": "module",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "uint16[]",
                "name": "roles",
                "type": "uint16[]",
            },
            {
                "indexed": False,
                "internalType": "bool[]",
                "name": "memberOf",
                "type": "bool[]",
            },
        ],
        "name": "AssignRoles",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "previousAvatar",
                "type": "address",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "newAvatar",
                "type": "address",
            },
        ],
        "name": "AvatarSet",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address",
                "name": "guard",
                "type": "address",
            }
        ],
        "name": "ChangedGuard",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address",
                "name": "module",
                "type": "address",
            }
        ],
        "name": "DisabledModule",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address",
                "name": "module",
                "type": "address",
            }
        ],
        "name": "EnabledModule",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "previousOwner",
                "type": "address",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "newOwner",
                "type": "address",
            },
        ],
        "name": "OwnershipTransferred",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "initiator",
                "type": "address",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "owner",
                "type": "address",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "avatar",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "address",
                "name": "target",
                "type": "address",
            },
        ],
        "name": "RolesModSetup",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address",
                "name": "module",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "uint16",
                "name": "defaultRole",
                "type": "uint16",
            },
        ],
        "name": "SetDefaultRole",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address",
                "name": "multisendAddress",
                "type": "address",
            }
        ],
        "name": "SetMultisendAddress",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "previousTarget",
                "type": "address",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "newTarget",
                "type": "address",
            },
        ],
        "name": "TargetSet",
        "type": "event",
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "role", "type": "uint16"},
            {"internalType": "address", "name": "targetAddress", "type": "address"},
            {
                "internalType": "enum ExecutionOptions",
                "name": "options",
                "type": "uint8",
            },
        ],
        "name": "allowTarget",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "module", "type": "address"},
            {"internalType": "uint16[]", "name": "_roles", "type": "uint16[]"},
            {"internalType": "bool[]", "name": "memberOf", "type": "bool[]"},
        ],
        "name": "assignRoles",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "avatar",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "defaultRoles",
        "outputs": [{"internalType": "uint16", "name": "", "type": "uint16"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "prevModule", "type": "address"},
            {"internalType": "address", "name": "module", "type": "address"},
        ],
        "name": "disableModule",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "module", "type": "address"}],
        "name": "enableModule",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "value", "type": "uint256"},
            {"internalType": "bytes", "name": "data", "type": "bytes"},
            {
                "internalType": "enum Enum.Operation",
                "name": "operation",
                "type": "uint8",
            },
        ],
        "name": "execTransactionFromModule",
        "outputs": [{"internalType": "bool", "name": "success", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "value", "type": "uint256"},
            {"internalType": "bytes", "name": "data", "type": "bytes"},
            {
                "internalType": "enum Enum.Operation",
                "name": "operation",
                "type": "uint8",
            },
        ],
        "name": "execTransactionFromModuleReturnData",
        "outputs": [
            {"internalType": "bool", "name": "", "type": "bool"},
            {"internalType": "bytes", "name": "", "type": "bytes"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "value", "type": "uint256"},
            {"internalType": "bytes", "name": "data", "type": "bytes"},
            {
                "internalType": "enum Enum.Operation",
                "name": "operation",
                "type": "uint8",
            },
            {"internalType": "uint16", "name": "role", "type": "uint16"},
            {"internalType": "bool", "name": "shouldRevert", "type": "bool"},
        ],
        "name": "execTransactionWithRole",
        "outputs": [{"internalType": "bool", "name": "success", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "value", "type": "uint256"},
            {"internalType": "bytes", "name": "data", "type": "bytes"},
            {
                "internalType": "enum Enum.Operation",
                "name": "operation",
                "type": "uint8",
            },
            {"internalType": "uint16", "name": "role", "type": "uint16"},
            {"internalType": "bool", "name": "shouldRevert", "type": "bool"},
        ],
        "name": "execTransactionWithRoleReturnData",
        "outputs": [
            {"internalType": "bool", "name": "success", "type": "bool"},
            {"internalType": "bytes", "name": "returnData", "type": "bytes"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getGuard",
        "outputs": [{"internalType": "address", "name": "_guard", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "start", "type": "address"},
            {"internalType": "uint256", "name": "pageSize", "type": "uint256"},
        ],
        "name": "getModulesPaginated",
        "outputs": [
            {"internalType": "address[]", "name": "array", "type": "address[]"},
            {"internalType": "address", "name": "next", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "guard",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "_module", "type": "address"}],
        "name": "isModuleEnabled",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "multisend",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "renounceOwnership",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "role", "type": "uint16"},
            {"internalType": "address", "name": "targetAddress", "type": "address"},
        ],
        "name": "revokeTarget",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "role", "type": "uint16"},
            {"internalType": "address", "name": "targetAddress", "type": "address"},
            {"internalType": "bytes4", "name": "functionSig", "type": "bytes4"},
            {
                "internalType": "enum ExecutionOptions",
                "name": "options",
                "type": "uint8",
            },
        ],
        "name": "scopeAllowFunction",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "role", "type": "uint16"},
            {"internalType": "address", "name": "targetAddress", "type": "address"},
            {"internalType": "bytes4", "name": "functionSig", "type": "bytes4"},
            {"internalType": "bool[]", "name": "isParamScoped", "type": "bool[]"},
            {
                "internalType": "enum ParameterType[]",
                "name": "paramType",
                "type": "uint8[]",
            },
            {
                "internalType": "enum Comparison[]",
                "name": "paramComp",
                "type": "uint8[]",
            },
            {"internalType": "bytes[]", "name": "compValue", "type": "bytes[]"},
            {
                "internalType": "enum ExecutionOptions",
                "name": "options",
                "type": "uint8",
            },
        ],
        "name": "scopeFunction",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "role", "type": "uint16"},
            {"internalType": "address", "name": "targetAddress", "type": "address"},
            {"internalType": "bytes4", "name": "functionSig", "type": "bytes4"},
            {
                "internalType": "enum ExecutionOptions",
                "name": "options",
                "type": "uint8",
            },
        ],
        "name": "scopeFunctionExecutionOptions",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "role", "type": "uint16"},
            {"internalType": "address", "name": "targetAddress", "type": "address"},
            {"internalType": "bytes4", "name": "functionSig", "type": "bytes4"},
            {"internalType": "uint256", "name": "paramIndex", "type": "uint256"},
            {
                "internalType": "enum ParameterType",
                "name": "paramType",
                "type": "uint8",
            },
            {"internalType": "enum Comparison", "name": "paramComp", "type": "uint8"},
            {"internalType": "bytes", "name": "compValue", "type": "bytes"},
        ],
        "name": "scopeParameter",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "role", "type": "uint16"},
            {"internalType": "address", "name": "targetAddress", "type": "address"},
            {"internalType": "bytes4", "name": "functionSig", "type": "bytes4"},
            {"internalType": "uint256", "name": "paramIndex", "type": "uint256"},
            {
                "internalType": "enum ParameterType",
                "name": "paramType",
                "type": "uint8",
            },
            {"internalType": "bytes[]", "name": "compValues", "type": "bytes[]"},
        ],
        "name": "scopeParameterAsOneOf",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "role", "type": "uint16"},
            {"internalType": "address", "name": "targetAddress", "type": "address"},
            {"internalType": "bytes4", "name": "functionSig", "type": "bytes4"},
        ],
        "name": "scopeRevokeFunction",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "role", "type": "uint16"},
            {"internalType": "address", "name": "targetAddress", "type": "address"},
        ],
        "name": "scopeTarget",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "_avatar", "type": "address"}],
        "name": "setAvatar",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "module", "type": "address"},
            {"internalType": "uint16", "name": "role", "type": "uint16"},
        ],
        "name": "setDefaultRole",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "_guard", "type": "address"}],
        "name": "setGuard",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "_multisend", "type": "address"}
        ],
        "name": "setMultisend",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "_target", "type": "address"}],
        "name": "setTarget",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes", "name": "initParams", "type": "bytes"}],
        "name": "setUp",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "target",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "newOwner", "type": "address"}],
        "name": "transferOwnership",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "role", "type": "uint16"},
            {"internalType": "address", "name": "targetAddress", "type": "address"},
            {"internalType": "bytes4", "name": "functionSig", "type": "bytes4"},
            {"internalType": "uint8", "name": "paramIndex", "type": "uint8"},
        ],
        "name": "unscopeParameter",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]
