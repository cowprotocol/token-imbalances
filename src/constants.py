from web3 import Web3

SETTLEMENT_CONTRACT_ADDRESS = Web3.to_checksum_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41')
NATIVE_ETH_TOKEN_ADDRESS = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
WETH_TOKEN_ADDRESS = Web3.to_checksum_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
SDAI_TOKEN_ADDRESS = Web3.to_checksum_address('0x83F20F44975D03b1b09e64809B757c47f942BEeA')

EVENT_TOPICS = {
    'Transfer': 'Transfer(address,address,uint256)',
    'ERC20Transfer': 'ERC20Transfer(address,address,uint256)',
    'WithdrawalWETH': 'Withdrawal(address,uint256)',
    'DepositSDAI': 'Deposit(address,address,uint256,uint256)',
    'WithdrawSDAI': 'Withdraw(address,address,address,uint256,uint256)',
}