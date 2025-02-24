// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface ISoloMargin {
    struct ActionArgs {
        uint8 actionType;
        uint256 accountId;
        int128 amount;
        uint256 primaryMarketId;
        uint256 secondaryMarketId;
        address otherAddress;
        uint256 otherAccountId;
        bytes data;
    }
    struct AccountInfo {
        address owner;
        uint256 number;
    }
    function operate(AccountInfo[] calldata accounts, ActionArgs[] calldata actions) external;
}

interface IERC20 {
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
}

interface IUniswapV2Router {
    function swapExactTokensForTokensSupportingFeeOnTransferTokens(
        uint256 amountIn, uint256 amountOutMin, address[] calldata path, address to, uint256 deadline
    ) external returns (uint256[] memory amounts);
}

contract FlashLoanArbitrage {
    address public immutable owner;
    ISoloMargin public constant soloMargin = ISoloMargin(0x1E0447b19BB6EcFdAe1e4AE1694b0C3659614e4e); // dYdX Solo Margin
    mapping(address => uint256) public marketIdForToken;
    
    event ArbitrageExecuted(address indexed tokenBorrow, uint256 amountBorrow, uint256 profit);
    event MarketIdUpdated(address indexed token, uint256 marketId);

    constructor() {
        owner = msg.sender;
        // Ethereum Mainnet dYdX market IDs
        marketIdForToken[0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2] = 0; // WETH
        marketIdForToken[0x6B175474E89094C44Da98b954EedeAC495271d0F] = 2; // DAI
        marketIdForToken[0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48] = 3; // USDC
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    function updateMarketId(address token, uint256 marketId) external onlyOwner {
        marketIdForToken[token] = marketId;
        emit MarketIdUpdated(token, marketId);
    }

    function initiateArbitrage(
        address tokenBorrow,
        uint256 amountBorrow,
        address dex1, // e.g., Uniswap Router
        address dex2, // e.g., SushiSwap Router
        address[] calldata path1, // e.g., [tokenBorrow, tokenB]
        address[] calldata path2, // e.g., [tokenB, tokenBorrow]
        uint256 minProfit // Minimum profit in tokenBorrow units
    ) external onlyOwner {
        require(marketIdForToken[tokenBorrow] != 0, "Unsupported token");

        ISoloMargin.AccountInfo[] memory accounts = new ISoloMargin.AccountInfo[](1);
        accounts[0] = ISoloMargin.AccountInfo(address(this), 1);

        ISoloMargin.ActionArgs[] memory actions = new ISoloMargin.ActionArgs[](3);

        // Step 1: Borrow from dYdX
        actions[0] = ISoloMargin.ActionArgs({
            actionType: 1, // Withdraw
            accountId: 0,
            amount: int128(uint128(amountBorrow)),
            primaryMarketId: marketIdForToken[tokenBorrow],
            secondaryMarketId: 0,
            otherAddress: address(this),
            otherAccountId: 0,
            data: ""
        });

        // Step 2: Execute trades
        bytes memory callData = abi.encodeWithSelector(
            this.performTrades.selector, dex1, dex2, path1, path2, amountBorrow, minProfit
        );
        actions[1] = ISoloMargin.ActionArgs({
            actionType: 4, // Call
            accountId: 0,
            amount: int128(0),
            primaryMarketId: 0,
            secondaryMarketId: 0,
            otherAddress: address(this),
            otherAccountId: 0,
            data: callData
        });

        // Step 3: Repay dYdX
        actions[2] = ISoloMargin.ActionArgs({
            actionType: 0, // Deposit
            accountId: 0,
            amount: int128(uint128(amountBorrow)),
            primaryMarketId: marketIdForToken[tokenBorrow],
            secondaryMarketId: 0,
            otherAddress: address(this),
            otherAccountId: 0,
            data: ""
        });

        soloMargin.operate(accounts, actions);
    }

    function performTrades(
        address dex1,
        address dex2,
        address[] calldata path1,
        address[] calldata path2,
        uint256 amountBorrow,
        uint256 minProfit
    ) external {
        require(msg.sender == address(this), "Only self");

        IERC20 tokenBorrow = IERC20(path1[0]);
        require(tokenBorrow.approve(dex1, amountBorrow), "DEX1 approval failed");

        // Swap on DEX1 (e.g., tokenBorrow -> tokenB)
        IUniswapV2Router(dex1).swapExactTokensForTokensSupportingFeeOnTransferTokens(
            amountBorrow, 0, path1, address(this), block.timestamp + 60
        );

        IERC20 tokenB = IERC20(path2[0]);
        uint256 amountB = tokenB.balanceOf(address(this));
        require(tokenB.approve(dex2, amountB), "DEX2 approval failed");

        // Swap on DEX2 (e.g., tokenB -> tokenBorrow)
        IUniswapV2Router(dex2).swapExactTokensForTokensSupportingFeeOnTransferTokens(
            amountB, 0, path2, address(this), block.timestamp + 60
        );

        uint256 finalBalance = tokenBorrow.balanceOf(address(this));
        require(finalBalance >= amountBorrow, "Cannot repay loan");
        uint256 profit = finalBalance - amountBorrow;
        require(profit >= minProfit, "Profit too low");

        if (profit > 0) {
            require(tokenBorrow.transfer(owner, profit), "Profit transfer failed");
            emit ArbitrageExecuted(address(tokenBorrow), amountBorrow, profit);
        }
    }

    receive() external payable {}
}
