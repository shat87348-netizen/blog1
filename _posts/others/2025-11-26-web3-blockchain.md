---
layout: post
title: "从零开始开发Web3 DApp：智能合约+前端完整实战"
date: 2025-11-26
categories: [others]
tags: [Web3, 智能合约, Solidity, Hardhat, 以太坊, 实战教程]
author: zhangshuming
---

# 从零开始开发Web3 DApp：智能合约+前端完整实战

本教程将带你从零开始，使用Solidity、Hardhat和React构建一个完整的去中心化应用（DApp）。我们将创建一个简单的投票系统，涵盖智能合约开发、测试、部署和前端集成。

## 项目目标

构建一个去中心化投票DApp，功能包括：
- 创建投票提案
- 投票功能
- 查看投票结果
- 使用MetaMask钱包连接
- 实时更新投票状态

## 第一步：环境准备（10分钟）

### 1. 安装Node.js和npm

```bash
# 检查版本
node --version  # 需要 v16+
npm --version
```

### 2. 安装Hardhat

```bash
mkdir voting-dapp
cd voting-dapp
npm init -y
npm install --save-dev hardhat
npx hardhat init
```

选择：
- Create a JavaScript project
- 安装所有依赖

### 3. 安装其他依赖

```bash
npm install --save-dev @nomicfoundation/hardhat-toolbox
npm install ethers
npm install dotenv
```

### 4. 安装前端依赖

```bash
# 创建前端目录
mkdir frontend
cd frontend
npx create-react-app . --template typescript
cd ..

# 安装Web3相关库
cd frontend
npm install ethers
npm install @metamask/detect-provider
cd ..
```

## 第二步：配置Hardhat（5分钟）

### 1. 更新hardhat.config.js

```javascript
require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.19",
  networks: {
    hardhat: {
      chainId: 1337
    },
    sepolia: {
      url: process.env.SEPOLIA_URL || "",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
    },
    localhost: {
      url: "http://127.0.0.1:8545"
    }
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  }
};
```

### 2. 创建.env文件

```bash
# .env
PRIVATE_KEY=your-private-key-here
SEPOLIA_URL=https://sepolia.infura.io/v3/your-project-id
```

## 第三步：编写智能合约（20分钟）

### 1. 创建投票合约

创建 `contracts/Voting.sol`：

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Voting {
    // 提案结构
    struct Proposal {
        string title;
        string description;
        uint256 yesVotes;
        uint256 noVotes;
        address creator;
        uint256 endTime;
        bool ended;
        mapping(address => bool) hasVoted;
    }

    // 提案数组
    Proposal[] public proposals;
    
    // 事件
    event ProposalCreated(uint256 indexed proposalId, address creator, string title);
    event VoteCast(uint256 indexed proposalId, address voter, bool support);
    event ProposalEnded(uint256 indexed proposalId, bool result);

    // 创建提案
    function createProposal(
        string memory _title,
        string memory _description,
        uint256 _durationHours
    ) public returns (uint256) {
        require(bytes(_title).length > 0, "Title cannot be empty");
        require(_durationHours > 0 && _durationHours <= 168, "Duration must be 1-168 hours");

        uint256 proposalId = proposals.length;
        Proposal storage newProposal = proposals.push();
        
        newProposal.title = _title;
        newProposal.description = _description;
        newProposal.creator = msg.sender;
        newProposal.endTime = block.timestamp + (_durationHours * 1 hours);
        newProposal.ended = false;

        emit ProposalCreated(proposalId, msg.sender, _title);
        return proposalId;
    }

    // 投票
    function vote(uint256 _proposalId, bool _support) public {
        require(_proposalId < proposals.length, "Proposal does not exist");
        Proposal storage proposal = proposals[_proposalId];
        require(!proposal.ended, "Proposal has ended");
        require(block.timestamp < proposal.endTime, "Voting period has ended");
        require(!proposal.hasVoted[msg.sender], "You have already voted");

        proposal.hasVoted[msg.sender] = true;
        
        if (_support) {
            proposal.yesVotes++;
        } else {
            proposal.noVotes++;
        }

        emit VoteCast(_proposalId, msg.sender, _support);
    }

    // 结束提案（任何人都可以调用）
    function endProposal(uint256 _proposalId) public {
        require(_proposalId < proposals.length, "Proposal does not exist");
        Proposal storage proposal = proposals[_proposalId];
        require(!proposal.ended, "Proposal already ended");
        require(block.timestamp >= proposal.endTime, "Voting period not ended");

        proposal.ended = true;
        bool result = proposal.yesVotes > proposal.noVotes;
        
        emit ProposalEnded(_proposalId, result);
    }

    // 获取提案数量
    function getProposalCount() public view returns (uint256) {
        return proposals.length;
    }

    // 获取提案详情
    function getProposal(uint256 _proposalId) public view returns (
        string memory title,
        string memory description,
        uint256 yesVotes,
        uint256 noVotes,
        address creator,
        uint256 endTime,
        bool ended
    ) {
        require(_proposalId < proposals.length, "Proposal does not exist");
        Proposal storage proposal = proposals[_proposalId];
        
        return (
            proposal.title,
            proposal.description,
            proposal.yesVotes,
            proposal.noVotes,
            proposal.creator,
            proposal.endTime,
            proposal.ended
        );
    }

    // 检查是否已投票
    function hasVoted(uint256 _proposalId, address _voter) public view returns (bool) {
        require(_proposalId < proposals.length, "Proposal does not exist");
        return proposals[_proposalId].hasVoted[_voter];
    }
}
```

## 第四步：编写测试（15分钟）

创建 `test/Voting.test.js`：

```javascript
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Voting Contract", function () {
  let voting;
  let owner;
  let addr1;
  let addr2;

  beforeEach(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();
    
    const Voting = await ethers.getContractFactory("Voting");
    voting = await Voting.deploy();
    await voting.deployed();
  });

  describe("Deployment", function () {
    it("Should deploy successfully", async function () {
      expect(await voting.getProposalCount()).to.equal(0);
    });
  });

  describe("Creating Proposals", function () {
    it("Should create a proposal", async function () {
      const tx = await voting.createProposal(
        "Test Proposal",
        "This is a test proposal",
        24
      );
      await tx.wait();

      expect(await voting.getProposalCount()).to.equal(1);
      
      const proposal = await voting.getProposal(0);
      expect(proposal.title).to.equal("Test Proposal");
      expect(proposal.creator).to.equal(owner.address);
    });

    it("Should reject empty title", async function () {
      await expect(
        voting.createProposal("", "Description", 24)
      ).to.be.revertedWith("Title cannot be empty");
    });

    it("Should reject invalid duration", async function () {
      await expect(
        voting.createProposal("Title", "Description", 0)
      ).to.be.revertedWith("Duration must be 1-168 hours");
    });
  });

  describe("Voting", function () {
    beforeEach(async function () {
      await voting.createProposal("Test", "Description", 24);
    });

    it("Should allow voting", async function () {
      await voting.vote(0, true);
      
      const proposal = await voting.getProposal(0);
      expect(proposal.yesVotes).to.equal(1);
      expect(await voting.hasVoted(0, owner.address)).to.be.true;
    });

    it("Should prevent double voting", async function () {
      await voting.vote(0, true);
      
      await expect(
        voting.vote(0, false)
      ).to.be.revertedWith("You have already voted");
    });

    it("Should allow multiple users to vote", async function () {
      await voting.connect(addr1).vote(0, true);
      await voting.connect(addr2).vote(0, false);
      
      const proposal = await voting.getProposal(0);
      expect(proposal.yesVotes).to.equal(1);
      expect(proposal.noVotes).to.equal(1);
    });
  });

  describe("Ending Proposals", function () {
    it("Should end proposal after duration", async function () {
      // 创建1小时提案
      await voting.createProposal("Test", "Description", 1);
      
      // 增加时间（需要hardhat网络配置）
      await ethers.provider.send("evm_increaseTime", [3600]);
      await ethers.provider.send("evm_mine");
      
      await voting.endProposal(0);
      const proposal = await voting.getProposal(0);
      expect(proposal.ended).to.be.true;
    });
  });
});
```

运行测试：

```bash
npx hardhat test
```

## 第五步：部署合约（10分钟）

### 1. 创建部署脚本

创建 `scripts/deploy.js`：

```javascript
const hre = require("hardhat");

async function main() {
  const Voting = await hre.ethers.getContractFactory("Voting");
  const voting = await Voting.deploy();

  await voting.deployed();

  console.log("Voting contract deployed to:", voting.address);
  
  // 保存部署信息
  const fs = require("fs");
  const deploymentInfo = {
    address: voting.address,
    network: hre.network.name,
    timestamp: new Date().toISOString()
  };
  
  fs.writeFileSync(
    "./deployment.json",
    JSON.stringify(deploymentInfo, null, 2)
  );
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
```

### 2. 启动本地节点

```bash
# 在一个终端启动Hardhat节点
npx hardhat node
```

### 3. 部署到本地网络

```bash
# 在另一个终端部署
npx hardhat run scripts/deploy.js --network localhost
```

### 4. 部署到测试网（可选）

```bash
# 确保.env文件配置正确
npx hardhat run scripts/deploy.js --network sepolia
```

## 第六步：创建前端应用（30分钟）

### 1. 创建Web3工具文件

创建 `frontend/src/utils/web3.js`：

```javascript
import { ethers } from 'ethers';

let provider = null;
let signer = null;

// 连接MetaMask
export async function connectWallet() {
  if (typeof window.ethereum !== 'undefined') {
    try {
      // 请求账户访问
      await window.ethereum.request({ method: 'eth_requestAccounts' });
      
      provider = new ethers.providers.Web3Provider(window.ethereum);
      signer = provider.getSigner();
      
      const address = await signer.getAddress();
      const network = await provider.getNetwork();
      
      return { address, network, provider, signer };
    } catch (error) {
      console.error('Error connecting wallet:', error);
      throw error;
    }
  } else {
    throw new Error('MetaMask is not installed');
  }
}

// 获取合约实例
export function getContract(contractAddress, abi) {
  if (!signer) {
    throw new Error('Wallet not connected');
  }
  return new ethers.Contract(contractAddress, abi, signer);
}

// 监听账户变化
export function onAccountsChanged(callback) {
  if (window.ethereum) {
    window.ethereum.on('accountsChanged', callback);
  }
}

// 监听网络变化
export function onChainChanged(callback) {
  if (window.ethereum) {
    window.ethereum.on('chainChanged', callback);
  }
}

export { provider, signer };
```

### 2. 创建合约ABI文件

部署后，复制 `artifacts/contracts/Voting.sol/Voting.json` 中的abi到 `frontend/src/contracts/Voting.json`。

### 3. 创建主应用组件

更新 `frontend/src/App.js`：

```javascript
import React, { useState, useEffect } from 'react';
import { connectWallet, getContract, onAccountsChanged } from './utils/web3';
import VotingABI from './contracts/Voting.json';
import './App.css';

const CONTRACT_ADDRESS = 'YOUR_CONTRACT_ADDRESS'; // 从deployment.json获取

function App() {
  const [account, setAccount] = useState('');
  const [contract, setContract] = useState(null);
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newProposal, setNewProposal] = useState({ title: '', description: '', duration: 24 });

  useEffect(() => {
    init();
  }, []);

  const init = async () => {
    try {
      const { address } = await connectWallet();
      setAccount(address);
      
      const votingContract = getContract(CONTRACT_ADDRESS, VotingABI.abi);
      setContract(votingContract);
      
      await loadProposals(votingContract);
      
      // 监听账户变化
      onAccountsChanged((accounts) => {
        if (accounts.length > 0) {
          setAccount(accounts[0]);
        } else {
          setAccount('');
        }
      });
    } catch (error) {
      console.error('Initialization error:', error);
      alert('请安装MetaMask并连接钱包');
    }
  };

  const loadProposals = async (contractInstance) => {
    try {
      const count = await contractInstance.getProposalCount();
      const proposalList = [];
      
      for (let i = 0; i < count; i++) {
        const proposal = await contractInstance.getProposal(i);
        const hasVoted = await contractInstance.hasVoted(i, account || '0x0');
        
        proposalList.push({
          id: i,
          title: proposal.title,
          description: proposal.description,
          yesVotes: proposal.yesVotes.toString(),
          noVotes: proposal.noVotes.toString(),
          creator: proposal.creator,
          endTime: new Date(proposal.endTime.toNumber() * 1000),
          ended: proposal.ended,
          hasVoted
        });
      }
      
      setProposals(proposalList);
    } catch (error) {
      console.error('Error loading proposals:', error);
    }
  };

  const createProposal = async () => {
    if (!contract || !newProposal.title || !newProposal.description) {
      alert('请填写所有字段');
      return;
    }

    setLoading(true);
    try {
      const tx = await contract.createProposal(
        newProposal.title,
        newProposal.description,
        newProposal.duration
      );
      await tx.wait();
      
      alert('提案创建成功！');
      setNewProposal({ title: '', description: '', duration: 24 });
      await loadProposals(contract);
    } catch (error) {
      console.error('Error creating proposal:', error);
      alert('创建提案失败：' + error.message);
    }
    setLoading(false);
  };

  const vote = async (proposalId, support) => {
    if (!contract) return;

    setLoading(true);
    try {
      const tx = await contract.vote(proposalId, support);
      await tx.wait();
      
      alert('投票成功！');
      await loadProposals(contract);
    } catch (error) {
      console.error('Error voting:', error);
      alert('投票失败：' + error.message);
    }
    setLoading(false);
  };

  const endProposal = async (proposalId) => {
    if (!contract) return;

    setLoading(true);
    try {
      const tx = await contract.endProposal(proposalId);
      await tx.wait();
      
      alert('提案已结束！');
      await loadProposals(contract);
    } catch (error) {
      console.error('Error ending proposal:', error);
      alert('结束提案失败：' + error.message);
    }
    setLoading(false);
  };

  if (!account) {
    return (
      <div className="App">
        <div className="container">
          <h1>去中心化投票系统</h1>
          <button onClick={init} className="connect-btn">
            连接MetaMask钱包
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <div className="container">
        <header>
          <h1>去中心化投票系统</h1>
          <p>已连接账户: {account}</p>
        </header>

        <section className="create-proposal">
          <h2>创建新提案</h2>
          <input
            type="text"
            placeholder="提案标题"
            value={newProposal.title}
            onChange={(e) => setNewProposal({ ...newProposal, title: e.target.value })}
          />
          <textarea
            placeholder="提案描述"
            value={newProposal.description}
            onChange={(e) => setNewProposal({ ...newProposal, description: e.target.value })}
          />
          <input
            type="number"
            placeholder="持续时间（小时）"
            value={newProposal.duration}
            onChange={(e) => setNewProposal({ ...newProposal, duration: parseInt(e.target.value) })}
          />
          <button onClick={createProposal} disabled={loading}>
            {loading ? '处理中...' : '创建提案'}
          </button>
        </section>

        <section className="proposals">
          <h2>提案列表</h2>
          {proposals.map((proposal) => (
            <div key={proposal.id} className="proposal-card">
              <h3>{proposal.title}</h3>
              <p>{proposal.description}</p>
              <div className="proposal-info">
                <p>创建者: {proposal.creator}</p>
                <p>结束时间: {proposal.endTime.toLocaleString()}</p>
                <p>状态: {proposal.ended ? '已结束' : '进行中'}</p>
              </div>
              <div className="votes">
                <p>赞成: {proposal.yesVotes}</p>
                <p>反对: {proposal.noVotes}</p>
              </div>
              {!proposal.ended && (
                <div className="actions">
                  {!proposal.hasVoted ? (
                    <>
                      <button onClick={() => vote(proposal.id, true)} disabled={loading}>
                        赞成
                      </button>
                      <button onClick={() => vote(proposal.id, false)} disabled={loading}>
                        反对
                      </button>
                    </>
                  ) : (
                    <p>您已投票</p>
                  )}
                </div>
              )}
              {!proposal.ended && new Date() >= proposal.endTime && (
                <button onClick={() => endProposal(proposal.id)} disabled={loading}>
                  结束提案
                </button>
              )}
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}

export default App;
```

### 4. 添加样式

更新 `frontend/src/App.css`：

```css
.App {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.container {
  background: #f5f5f5;
  border-radius: 10px;
  padding: 30px;
}

header {
  text-align: center;
  margin-bottom: 30px;
}

.create-proposal {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
}

.create-proposal input,
.create-proposal textarea {
  width: 100%;
  padding: 10px;
  margin: 10px 0;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.create-proposal button {
  background: #4CAF50;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.proposals {
  display: grid;
  gap: 20px;
}

.proposal-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.proposal-card h3 {
  margin-top: 0;
}

.actions {
  margin-top: 15px;
}

.actions button {
  margin-right: 10px;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.actions button:first-child {
  background: #4CAF50;
  color: white;
}

.actions button:last-child {
  background: #f44336;
  color: white;
}

.connect-btn {
  background: #2196F3;
  color: white;
  padding: 15px 30px;
  font-size: 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}
```

### 5. 运行前端

```bash
cd frontend
npm start
```

## 常见问题解决

### 问题1：MetaMask连接失败

```javascript
// 检查MetaMask是否安装
if (typeof window.ethereum === 'undefined') {
  alert('请安装MetaMask扩展');
}
```

### 问题2：合约调用失败

- 检查合约地址是否正确
- 确认网络匹配（本地/测试网）
- 检查账户余额（需要ETH支付Gas费）

### 问题3：交易被拒绝

- 用户可能在MetaMask中拒绝了交易
- Gas费设置过低
- 网络拥堵

## 部署到生产环境

### 1. 部署到测试网

```bash
# 配置.env文件
npx hardhat run scripts/deploy.js --network sepolia

# 更新前端合约地址
```

### 2. 使用IPFS部署前端

```bash
# 构建前端
cd frontend
npm run build

# 使用IPFS部署
# 或使用Vercel/Netlify等平台
```

## 总结

通过本教程，你已经掌握了：
- ✅ Solidity智能合约开发
- ✅ Hardhat开发和测试
- ✅ 合约部署
- ✅ React前端集成
- ✅ MetaMask钱包连接
- ✅ Web3交互

现在你可以基于这个项目，开发更复杂的DApp应用！

## 参考资源

- [Solidity文档](https://soliditylang.org/)
- [Hardhat文档](https://hardhat.org/docs)
- [ethers.js文档](https://docs.ethers.io/)
- [MetaMask文档](https://docs.metamask.io/)
