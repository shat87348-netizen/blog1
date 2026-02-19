---
layout: post
title: "实时通信实战：WebSocket + Server-Sent Events完整实现"
date: 2025-06-15
categories: [backend]
tags: [WebSocket, SSE, 实时通信, Node.js, 实战教程]
author: zhangshuming
---

# 实时通信实战：WebSocket + Server-Sent Events完整实现

本教程将带你构建一个完整的实时通信系统，包括WebSocket聊天室和Server-Sent Events实时数据推送。我们将使用Node.js、Socket.io和原生SSE实现双向和单向实时通信。

## 项目目标

构建一个实时通信应用，包含：
- **WebSocket聊天室**：多用户实时聊天
- **SSE数据推送**：实时股票价格推送
- **房间管理**：创建和加入聊天室
- **用户管理**：用户登录和状态
- **消息历史**：保存和加载聊天记录

## 第一步：项目初始化（10分钟）

### 1. 创建项目

```bash
mkdir realtime-app
cd realtime-app
npm init -y
```

### 2. 安装依赖

```bash
npm install express socket.io cors dotenv
npm install --save-dev nodemon
```

### 3. 项目结构

```
realtime-app/
├── server/
│   ├── index.js          # 主服务器文件
│   ├── websocket.js      # WebSocket处理
│   ├── sse.js           # SSE处理
│   └── storage.js       # 数据存储
├── public/
│   ├── index.html        # 主页面
│   ├── chat.html         # 聊天页面
│   ├── sse.html          # SSE演示页面
│   └── js/
│       ├── chat.js       # 聊天客户端
│       └── sse.js        # SSE客户端
├── package.json
└── .env
```

## 第二步：创建WebSocket服务器（20分钟）

### 1. 主服务器文件

创建 `server/index.js`：

```javascript
const express = require('express');
const http = require('http');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const app = express();
const server = http.createServer(app);

// 中间件
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// 路由
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

app.get('/chat', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/chat.html'));
});

app.get('/sse', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/sse.html'));
});

// 初始化WebSocket和SSE
require('./websocket')(server);
require('./sse')(app);

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`🚀 服务器运行在 http://localhost:${PORT}`);
});
```

### 2. WebSocket处理

创建 `server/websocket.js`：

```javascript
const { Server } = require('socket.io');
const storage = require('./storage');

function initWebSocket(server) {
  const io = new Server(server, {
    cors: {
      origin: '*',
      methods: ['GET', 'POST']
    }
  });

  // 用户管理
  const users = new Map();
  const rooms = new Map();

  io.on('connection', (socket) => {
    console.log(`用户连接: ${socket.id}`);

    // 用户加入
    socket.on('user:join', (data) => {
      const { username, room } = data;
      
      if (!username || !room) {
        socket.emit('error', { message: '用户名和房间名不能为空' });
        return;
      }

      // 保存用户信息
      users.set(socket.id, { username, room, socketId: socket.id });
      
      // 加入房间
      socket.join(room);
      
      // 管理房间用户列表
      if (!rooms.has(room)) {
        rooms.set(room, new Set());
      }
      rooms.get(room).add(socket.id);

      // 通知房间内其他用户
      socket.to(room).emit('user:joined', {
        username,
        message: `${username} 加入了房间`,
        timestamp: new Date().toISOString()
      });

      // 发送房间用户列表
      const roomUsers = Array.from(rooms.get(room))
        .map(id => users.get(id))
        .filter(Boolean);
      
      io.to(room).emit('room:users', roomUsers);

      // 发送欢迎消息
      socket.emit('welcome', {
        message: `欢迎 ${username} 加入 ${room} 房间`,
        roomUsers
      });

      // 加载历史消息
      const history = storage.getMessages(room, 50);
      socket.emit('messages:history', history);
    });

    // 发送消息
    socket.on('message:send', (data) => {
      const user = users.get(socket.id);
      
      if (!user) {
        socket.emit('error', { message: '请先加入房间' });
        return;
      }

      const message = {
        id: Date.now().toString(),
        username: user.username,
        room: user.room,
        text: data.text,
        timestamp: new Date().toISOString(),
        type: 'message'
      };

      // 保存消息
      storage.saveMessage(message);

      // 广播到房间
      io.to(user.room).emit('message:new', message);
    });

    // 正在输入
    socket.on('typing:start', () => {
      const user = users.get(socket.id);
      if (user) {
        socket.to(user.room).emit('typing:start', { username: user.username });
      }
    });

    socket.on('typing:stop', () => {
      const user = users.get(socket.id);
      if (user) {
        socket.to(user.room).emit('typing:stop', { username: user.username });
      }
    });

    // 用户离开
    socket.on('disconnect', () => {
      const user = users.get(socket.id);
      
      if (user) {
        const { username, room } = user;
        
        // 从房间移除
        if (rooms.has(room)) {
          rooms.get(room).delete(socket.id);
          if (rooms.get(room).size === 0) {
            rooms.delete(room);
          }
        }

        // 通知房间内其他用户
        socket.to(room).emit('user:left', {
          username,
          message: `${username} 离开了房间`,
          timestamp: new Date().toISOString()
        });

        // 更新用户列表
        const roomUsers = Array.from(rooms.get(room) || [])
          .map(id => users.get(id))
          .filter(Boolean);
        
        io.to(room).emit('room:users', roomUsers);

        // 移除用户
        users.delete(socket.id);
      }

      console.log(`用户断开: ${socket.id}`);
    });
  });

  return io;
}

module.exports = initWebSocket;
```

### 3. 数据存储

创建 `server/storage.js`：

```javascript
// 简单的内存存储（生产环境应使用数据库）
const messages = new Map(); // room -> messages[]
const maxMessagesPerRoom = 100;

function saveMessage(message) {
  const { room } = message;
  
  if (!messages.has(room)) {
    messages.set(room, []);
  }
  
  const roomMessages = messages.get(room);
  roomMessages.push(message);
  
  // 限制消息数量
  if (roomMessages.length > maxMessagesPerRoom) {
    roomMessages.shift();
  }
}

function getMessages(room, limit = 50) {
  if (!messages.has(room)) {
    return [];
  }
  
  const roomMessages = messages.get(room);
  return roomMessages.slice(-limit);
}

function getRooms() {
  return Array.from(messages.keys());
}

module.exports = {
  saveMessage,
  getMessages,
  getRooms
};
```

## 第三步：创建SSE服务器（15分钟）

创建 `server/sse.js`：

```javascript
function initSSE(app) {
  // 股票价格模拟数据
  const stocks = {
    'AAPL': { price: 150.25, change: 2.5 },
    'GOOGL': { price: 2800.50, change: -15.3 },
    'MSFT': { price: 350.75, change: 5.2 },
    'TSLA': { price: 850.00, change: -25.5 },
  };

  // SSE端点
  app.get('/api/sse/stocks', (req, res) => {
    // 设置SSE响应头
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('Access-Control-Allow-Origin', '*');

    // 发送初始数据
    res.write(`data: ${JSON.stringify({ type: 'init', stocks })}\n\n`);

    // 定期更新价格
    const interval = setInterval(() => {
      // 模拟价格变化
      Object.keys(stocks).forEach(symbol => {
        const change = (Math.random() - 0.5) * 10;
        stocks[symbol].price = Math.max(0, stocks[symbol].price + change);
        stocks[symbol].change = change;
      });

      // 发送更新
      res.write(`data: ${JSON.stringify({ type: 'update', stocks, timestamp: new Date().toISOString() })}\n\n`);
    }, 2000); // 每2秒更新一次

    // 客户端断开连接
    req.on('close', () => {
      clearInterval(interval);
      res.end();
    });
  });

  // 通知推送
  app.get('/api/sse/notifications', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('Access-Control-Allow-Origin', '*');

    // 模拟通知
    const notifications = [
      '新用户注册',
      '系统维护通知',
      '产品更新发布',
      '安全提醒',
    ];

    let index = 0;
    const interval = setInterval(() => {
      if (index < notifications.length) {
        const notification = {
          id: Date.now(),
          message: notifications[index],
          type: 'info',
          timestamp: new Date().toISOString()
        };

        res.write(`data: ${JSON.stringify(notification)}\n\n`);
        index++;
      } else {
        clearInterval(interval);
        res.write(`data: ${JSON.stringify({ type: 'end' })}\n\n`);
      }
    }, 5000); // 每5秒发送一条通知

    req.on('close', () => {
      clearInterval(interval);
      res.end();
    });
  });
}

module.exports = initSSE;
```

## 第四步：创建前端页面（25分钟）

### 1. 主页面

创建 `public/index.html`：

```html
<!DOCTYPE html>
<html>
<head>
  <title>实时通信演示</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
      background: #f5f5f5;
    }
    .container {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }
    .card {
      background: white;
      padding: 30px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .card h2 {
      margin-top: 0;
      color: #333;
    }
    .card p {
      color: #666;
      line-height: 1.6;
    }
    .btn {
      display: inline-block;
      padding: 12px 24px;
      background: #007bff;
      color: white;
      text-decoration: none;
      border-radius: 4px;
      margin-top: 15px;
      transition: background 0.3s;
    }
    .btn:hover {
      background: #0056b3;
    }
  </style>
</head>
<body>
  <h1>实时通信演示</h1>
  <div class="container">
    <div class="card">
      <h2>WebSocket 聊天室</h2>
      <p>使用WebSocket实现多用户实时聊天功能。支持房间管理、消息历史、用户状态等。</p>
      <a href="/chat" class="btn">进入聊天室</a>
    </div>
    <div class="card">
      <h2>Server-Sent Events</h2>
      <p>使用SSE实现服务器到客户端的单向实时数据推送。演示股票价格和通知推送。</p>
      <a href="/sse" class="btn">查看SSE演示</a>
    </div>
  </div>
</body>
</html>
```

### 2. 聊天页面

创建 `public/chat.html`：

```html
<!DOCTYPE html>
<html>
<head>
  <title>WebSocket 聊天室</title>
  <link rel="stylesheet" href="/css/chat.css">
</head>
<body>
  <div class="chat-container">
    <div class="sidebar">
      <h2>聊天室</h2>
      <div id="join-form">
        <input type="text" id="username" placeholder="用户名" required>
        <input type="text" id="room" placeholder="房间名" required>
        <button id="join-btn">加入房间</button>
      </div>
      <div id="room-info" style="display: none;">
        <h3 id="room-name"></h3>
        <div id="users-list"></div>
        <button id="leave-btn">离开房间</button>
      </div>
    </div>

    <div class="main">
      <div id="messages" class="messages"></div>
      <div id="typing-indicator"></div>
      <div class="input-area" style="display: none;">
        <input type="text" id="message-input" placeholder="输入消息...">
        <button id="send-btn">发送</button>
      </div>
    </div>
  </div>

  <script src="/socket.io/socket.io.js"></script>
  <script src="/js/chat.js"></script>
</body>
</html>
```

创建 `public/js/chat.js`：

```javascript
const socket = io();

let currentRoom = null;
let currentUsername = null;

// DOM元素
const joinForm = document.getElementById('join-form');
const roomInfo = document.getElementById('room-info');
const usernameInput = document.getElementById('username');
const roomInput = document.getElementById('room');
const joinBtn = document.getElementById('join-btn');
const leaveBtn = document.getElementById('leave-btn');
const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const inputArea = document.querySelector('.input-area');
const typingIndicator = document.getElementById('typing-indicator');
const usersList = document.getElementById('users-list');
const roomName = document.getElementById('room-name');

let typingTimeout;

// 加入房间
joinBtn.addEventListener('click', () => {
  const username = usernameInput.value.trim();
  const room = roomInput.value.trim();
  
  if (!username || !room) {
    alert('请输入用户名和房间名');
    return;
  }

  currentUsername = username;
  currentRoom = room;
  
  socket.emit('user:join', { username, room });
});

// 离开房间
leaveBtn.addEventListener('click', () => {
  socket.disconnect();
  socket.connect();
  resetUI();
});

// 发送消息
sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    sendMessage();
  }
});

function sendMessage() {
  const text = messageInput.value.trim();
  if (!text) return;

  socket.emit('message:send', { text });
  messageInput.value = '';
  socket.emit('typing:stop');
}

// 输入监听
messageInput.addEventListener('input', () => {
  socket.emit('typing:start');
  clearTimeout(typingTimeout);
  typingTimeout = setTimeout(() => {
    socket.emit('typing:stop');
  }, 1000);
});

// Socket事件监听
socket.on('welcome', (data) => {
  showSystemMessage(data.message);
  updateUsersList(data.roomUsers);
  joinForm.style.display = 'none';
  roomInfo.style.display = 'block';
  inputArea.style.display = 'flex';
  roomName.textContent = `房间: ${currentRoom}`;
});

socket.on('messages:history', (messages) => {
  messages.forEach(msg => displayMessage(msg));
});

socket.on('message:new', (message) => {
  displayMessage(message);
});

socket.on('user:joined', (data) => {
  showSystemMessage(data.message);
});

socket.on('user:left', (data) => {
  showSystemMessage(data.message);
});

socket.on('room:users', (users) => {
  updateUsersList(users);
});

socket.on('typing:start', (data) => {
  if (data.username !== currentUsername) {
    typingIndicator.textContent = `${data.username} 正在输入...`;
  }
});

socket.on('typing:stop', () => {
  typingIndicator.textContent = '';
});

socket.on('error', (data) => {
  alert(data.message);
});

// 显示消息
function displayMessage(message) {
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message';
  
  if (message.username === currentUsername) {
    messageDiv.classList.add('own-message');
  }
  
  messageDiv.innerHTML = `
    <div class="message-header">
      <span class="username">${message.username}</span>
      <span class="timestamp">${formatTime(message.timestamp)}</span>
    </div>
    <div class="message-text">${escapeHtml(message.text)}</div>
  `;
  
  messagesDiv.appendChild(messageDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function showSystemMessage(message) {
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message system-message';
  messageDiv.textContent = message;
  messagesDiv.appendChild(messageDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function updateUsersList(users) {
  usersList.innerHTML = '<h4>在线用户:</h4>';
  users.forEach(user => {
    const userDiv = document.createElement('div');
    userDiv.className = 'user-item';
    userDiv.textContent = user.username;
    usersList.appendChild(userDiv);
  });
}

function resetUI() {
  joinForm.style.display = 'block';
  roomInfo.style.display = 'none';
  inputArea.style.display = 'none';
  messagesDiv.innerHTML = '';
  currentRoom = null;
  currentUsername = null;
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString();
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
```

### 3. SSE演示页面

创建 `public/sse.html`：

```html
<!DOCTYPE html>
<html>
<head>
  <title>Server-Sent Events 演示</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      max-width: 1000px;
      margin: 0 auto;
      padding: 20px;
    }
    .section {
      background: white;
      padding: 20px;
      margin: 20px 0;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .stock-item {
      display: flex;
      justify-content: space-between;
      padding: 10px;
      border-bottom: 1px solid #eee;
    }
    .price {
      font-weight: bold;
    }
    .positive { color: green; }
    .negative { color: red; }
    .notification {
      padding: 10px;
      margin: 5px 0;
      background: #e3f2fd;
      border-left: 4px solid #2196f3;
      border-radius: 4px;
    }
    button {
      padding: 10px 20px;
      background: #007bff;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <h1>Server-Sent Events 演示</h1>
  
  <div class="section">
    <h2>实时股票价格</h2>
    <div id="stocks"></div>
    <button onclick="connectStocks()">连接股票推送</button>
    <button onclick="disconnectStocks()">断开连接</button>
  </div>

  <div class="section">
    <h2>实时通知</h2>
    <div id="notifications"></div>
    <button onclick="connectNotifications()">连接通知推送</button>
    <button onclick="disconnectNotifications()">断开连接</button>
  </div>

  <script>
    let stocksEventSource = null;
    let notificationsEventSource = null;

    function connectStocks() {
      if (stocksEventSource) return;

      stocksEventSource = new EventSource('/api/sse/stocks');
      
      stocksEventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'init' || data.type === 'update') {
          updateStocks(data.stocks);
        }
      };

      stocksEventSource.onerror = (error) => {
        console.error('SSE错误:', error);
      };
    }

    function disconnectStocks() {
      if (stocksEventSource) {
        stocksEventSource.close();
        stocksEventSource = null;
      }
    }

    function connectNotifications() {
      if (notificationsEventSource) return;

      notificationsEventSource = new EventSource('/api/sse/notifications');
      
      notificationsEventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'end') {
          disconnectNotifications();
          return;
        }

        addNotification(data);
      };

      notificationsEventSource.onerror = (error) => {
        console.error('SSE错误:', error);
      };
    }

    function disconnectNotifications() {
      if (notificationsEventSource) {
        notificationsEventSource.close();
        notificationsEventSource = null;
      }
    }

    function updateStocks(stocks) {
      const container = document.getElementById('stocks');
      container.innerHTML = '';
      
      Object.entries(stocks).forEach(([symbol, data]) => {
        const div = document.createElement('div');
        div.className = 'stock-item';
        div.innerHTML = `
          <span><strong>${symbol}</strong></span>
          <span class="price ${data.change >= 0 ? 'positive' : 'negative'}">
            $${data.price.toFixed(2)} 
            (${data.change >= 0 ? '+' : ''}${data.change.toFixed(2)})
          </span>
        `;
        container.appendChild(div);
      });
    }

    function addNotification(notification) {
      const container = document.getElementById('notifications');
      const div = document.createElement('div');
      div.className = 'notification';
      div.innerHTML = `
        <strong>${new Date(notification.timestamp).toLocaleTimeString()}</strong>
        <p>${notification.message}</p>
      `;
      container.insertBefore(div, container.firstChild);
    }
  </script>
</body>
</html>
```

## 第五步：运行和测试（5分钟）

### 1. 启动服务器

```bash
npm start
# 或
node server/index.js
```

### 2. 测试应用

1. 访问 `http://localhost:3000`
2. 点击"进入聊天室"，打开多个标签页测试多用户聊天
3. 点击"查看SSE演示"，观察实时数据推送

## 常见问题解决

### 问题1：WebSocket连接失败

```javascript
// 检查服务器是否运行
// 检查端口是否正确
// 检查CORS配置
```

### 问题2：SSE连接断开

```javascript
// SSE需要保持连接
// 检查服务器是否正常发送数据
// 检查网络代理设置
```

## 总结

通过本教程，你已经掌握了：
- ✅ WebSocket双向通信实现
- ✅ Server-Sent Events单向推送
- ✅ 房间和用户管理
- ✅ 消息历史存储
- ✅ 实时状态更新

现在你可以基于这个系统，构建更复杂的实时应用！

## 参考资源

- [Socket.io文档](https://socket.io/docs/)
- [MDN Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
