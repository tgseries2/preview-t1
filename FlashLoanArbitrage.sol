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
    function swapExactTokensForTokens(uint256 amountIn, uint256 amountOutMin, address[] calldata path, address to, uint256 deadline) external returns (uint256[] memory amounts);
}

contract FlashLoanArbitrage {
    address public owner;
    ISoloMargin public soloMargin = ISoloMargin(0x1E0447b19BB6EcFdAe1e4AE1694b0C3659614e4e);
    mapping(address => uint256) public marketIdForToken;

    constructor() {
        owner = msg.sender;
        marketIdForToken[0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2] = 0; // WETH
    }

    function initiateArbitrage(
        address tokenBorrow,
        uint256 amountBorrow,
        address dex1,
        address dex2,
        address tokenA,
        address tokenB
    ) external {
        require(msg.sender == owner, "Only owner");
        ISoloMargin.ActionArgs[] memory actions = new ISoloMargin.ActionArgs[](3);
        ISoloMargin.AccountInfo[] memory accounts = new ISoloMargin.AccountInfo[](1);
        accounts[0] = ISoloMargin.AccountInfo(address(this), 1);

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

        bytes memory callData = abi.encodeWithSelector(this.performTrades.selector, tokenA, tokenB, dex1, dex2, amountBorrow);
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

    function performTrades(address tokenA, address tokenB, address dex1, address dex2, uint256 amountBorrow) external {
        IERC20(tokenA).approve(dex1, amountBorrow);
        address[] memory path = new address[](2);
        path[0] = tokenA;
        path[1] = tokenB;
        IUniswapV2Router(dex1).swapExactTokensForTokens(amountBorrow, 0, path, address(this), block.timestamp + 60);

        uint256 amountB = IERC20(tokenB).balanceOf(address(this));
        IERC20(tokenB).approve(dex2, amountB);
        path[0] = tokenB;
        path[1] = tokenA;
        IUniswapV2Router(dex2).swapExactTokensForTokens(amountB, 0, path, address(this), block.timestamp + 60);

        uint256 finalA = IERC20(tokenA).balanceOf(address(this));
        require(finalA >= amountBorrow, "Not profitable");
        if (finalA > amountBorrow) {
            IERC20(tokenA).transfer(owner, finalA - amountBorrow);
        }
    }
}
