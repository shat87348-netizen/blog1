---
layout: post
title: "微前端架构实战：使用Module Federation构建可扩展应用"
date: 2025-04-10
categories: [articles]
permalink: /frontend/2025/04/10/micro-frontend-practice.html
tags: [微前端, Module Federation, Webpack, 架构, 实战教程]
author: zhangshuming
---

# 微前端架构实战：使用Module Federation构建可扩展应用

本教程将带你使用Webpack 5的Module Federation功能，从零开始构建一个完整的微前端应用。我们将创建一个主应用和多个子应用，实现独立开发、独立部署的微前端架构。

## 项目目标

构建一个包含以下模块的微前端应用：
- **主应用（Host）**：应用入口和路由管理
- **用户模块（Remote）**：用户管理功能
- **商品模块（Remote）**：商品展示功能
- **订单模块（Remote）**：订单管理功能

每个模块可以独立开发、测试和部署。

## 第一步：项目初始化（10分钟）

### 1. 创建项目结构

```bash
mkdir micro-frontend-demo
cd micro-frontend-demo

# 创建主应用
mkdir host-app
# 创建子应用
mkdir user-app product-app order-app
```

### 2. 初始化主应用

```bash
cd host-app
npm init -y
npm install --save-dev webpack webpack-cli webpack-dev-server html-webpack-plugin
npm install react react-dom react-router-dom
npm install --save-dev @babel/core @babel/preset-react @babel/preset-env babel-loader
npm install --save-dev css-loader style-loader
```

创建 `host-app/package.json` 脚本：

```json
{
  "name": "host-app",
  "version": "1.0.0",
  "scripts": {
    "start": "webpack serve --config webpack.config.js",
    "build": "webpack --config webpack.config.js"
  }
}
```

### 3. 配置Webpack Module Federation

创建 `host-app/webpack.config.js`：

```javascript
const ModuleFederationPlugin = require('webpack/lib/container/ModuleFederationPlugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  mode: 'development',
  devServer: {
    port: 3000,
    historyApiFallback: true,
  },
  module: {
    rules: [
      {
        test: /\.jsx?$/,
        loader: 'babel-loader',
        exclude: /node_modules/,
        options: {
          presets: ['@babel/preset-react', '@babel/preset-env'],
        },
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
    ],
  },
  plugins: [
    new ModuleFederationPlugin({
      name: 'host',
      remotes: {
        userApp: 'userApp@http://localhost:3001/remoteEntry.js',
        productApp: 'productApp@http://localhost:3002/remoteEntry.js',
        orderApp: 'orderApp@http://localhost:3003/remoteEntry.js',
      },
      shared: {
        react: { singleton: true, requiredVersion: '^18.0.0' },
        'react-dom': { singleton: true, requiredVersion: '^18.0.0' },
        'react-router-dom': { singleton: true, requiredVersion: '^6.0.0' },
      },
    }),
    new HtmlWebpackPlugin({
      template: './public/index.html',
    }),
  ],
};
```

## 第二步：创建主应用（15分钟）

### 1. 创建主应用入口

创建 `host-app/public/index.html`：

```html
<!DOCTYPE html>
<html>
<head>
  <title>微前端主应用</title>
</head>
<body>
  <div id="root"></div>
</body>
</html>
```

创建 `host-app/src/index.js`：

```javascript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
```

创建 `host-app/src/App.js`：

```javascript
import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom';
import './App.css';

// 懒加载远程模块
const UserApp = lazy(() => import('userApp/UserApp'));
const ProductApp = lazy(() => import('productApp/ProductApp'));
const OrderApp = lazy(() => import('orderApp/OrderApp'));

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <nav className="navbar">
          <div className="nav-brand">微前端应用</div>
          <div className="nav-links">
            <Link to="/users">用户管理</Link>
            <Link to="/products">商品管理</Link>
            <Link to="/orders">订单管理</Link>
          </div>
        </nav>

        <main className="main-content">
          <Suspense fallback={<div className="loading">加载中...</div>}>
            <Routes>
              <Route path="/" element={<Navigate to="/users" replace />} />
              <Route path="/users/*" element={<UserApp />} />
              <Route path="/products/*" element={<ProductApp />} />
              <Route path="/orders/*" element={<OrderApp />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
```

创建 `host-app/src/App.css`：

```css
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.navbar {
  background: #2c3e50;
  color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.nav-brand {
  font-size: 1.5rem;
  font-weight: bold;
}

.nav-links {
  display: flex;
  gap: 2rem;
}

.nav-links a {
  color: white;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background 0.3s;
}

.nav-links a:hover {
  background: rgba(255,255,255,0.1);
}

.main-content {
  flex: 1;
  padding: 2rem;
  background: #f5f5f5;
}

.loading {
  text-align: center;
  padding: 2rem;
  font-size: 1.2rem;
  color: #666;
}
```

## 第三步：创建用户模块（20分钟）

### 1. 初始化用户应用

```bash
cd ../user-app
npm init -y
npm install --save-dev webpack webpack-cli webpack-dev-server html-webpack-plugin
npm install react react-dom react-router-dom
npm install --save-dev @babel/core @babel/preset-react @babel/preset-env babel-loader
npm install --save-dev css-loader style-loader
```

### 2. 配置Webpack

创建 `user-app/webpack.config.js`：

```javascript
const ModuleFederationPlugin = require('webpack/lib/container/ModuleFederationPlugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  mode: 'development',
  devServer: {
    port: 3001,
    historyApiFallback: true,
  },
  module: {
    rules: [
      {
        test: /\.jsx?$/,
        loader: 'babel-loader',
        exclude: /node_modules/,
        options: {
          presets: ['@babel/preset-react', '@babel/preset-env'],
        },
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
    ],
  },
  plugins: [
    new ModuleFederationPlugin({
      name: 'userApp',
      filename: 'remoteEntry.js',
      exposes: {
        './UserApp': './src/App',
      },
      shared: {
        react: { singleton: true, requiredVersion: '^18.0.0' },
        'react-dom': { singleton: true, requiredVersion: '^18.0.0' },
        'react-router-dom': { singleton: true, requiredVersion: '^6.0.0' },
      },
    }),
    new HtmlWebpackPlugin({
      template: './public/index.html',
    }),
  ],
};
```

### 3. 创建用户应用组件

创建 `user-app/src/App.js`：

```javascript
import React, { useState } from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import UserList from './components/UserList';
import UserDetail from './components/UserDetail';
import './App.css';

function UserApp() {
  return (
    <div className="user-app">
      <div className="user-header">
        <h1>用户管理模块</h1>
        <nav className="user-nav">
          <Link to="/users">用户列表</Link>
        </nav>
      </div>
      
      <div className="user-content">
        <Routes>
          <Route path="/" element={<UserList />} />
          <Route path="/:id" element={<UserDetail />} />
        </Routes>
      </div>
    </div>
  );
}

export default UserApp;
```

创建 `user-app/src/components/UserList.js`：

```javascript
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './UserList.css';

function UserList() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    // 模拟API调用
    setTimeout(() => {
      setUsers([
        { id: 1, name: '张三', email: 'zhangsan@example.com', role: '管理员' },
        { id: 2, name: '李四', email: 'lisi@example.com', role: '用户' },
        { id: 3, name: '王五', email: 'wangwu@example.com', role: '用户' },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  if (loading) {
    return <div className="loading">加载用户数据...</div>;
  }

  return (
    <div className="user-list">
      <div className="user-list-header">
        <h2>用户列表</h2>
        <button className="btn-primary">添加用户</button>
      </div>
      
      <table className="user-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>姓名</th>
            <th>邮箱</th>
            <th>角色</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {users.map(user => (
            <tr key={user.id}>
              <td>{user.id}</td>
              <td>{user.name}</td>
              <td>{user.email}</td>
              <td>{user.role}</td>
              <td>
                <button 
                  className="btn-link"
                  onClick={() => navigate(`/users/${user.id}`)}
                >
                  查看详情
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default UserList;
```

创建 `user-app/src/components/UserDetail.js`：

```javascript
import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './UserDetail.css';

function UserDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  
  // 模拟数据
  const user = {
    id: parseInt(id),
    name: '张三',
    email: 'zhangsan@example.com',
    role: '管理员',
    createdAt: '2024-01-01',
  };

  return (
    <div className="user-detail">
      <button className="btn-back" onClick={() => navigate('/users')}>
        ← 返回列表
      </button>
      
      <div className="detail-card">
        <h2>用户详情</h2>
        <div className="detail-item">
          <label>ID:</label>
          <span>{user.id}</span>
        </div>
        <div className="detail-item">
          <label>姓名:</label>
          <span>{user.name}</span>
        </div>
        <div className="detail-item">
          <label>邮箱:</label>
          <span>{user.email}</span>
        </div>
        <div className="detail-item">
          <label>角色:</label>
          <span>{user.role}</span>
        </div>
        <div className="detail-item">
          <label>创建时间:</label>
          <span>{user.createdAt}</span>
        </div>
      </div>
    </div>
  );
}

export default UserDetail;
```

创建 `user-app/src/App.css`：

```css
.user-app {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.user-header {
  border-bottom: 2px solid #eee;
  padding-bottom: 1rem;
  margin-bottom: 2rem;
}

.user-header h1 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.user-nav a {
  color: #3498db;
  text-decoration: none;
  margin-right: 1rem;
}

.user-content {
  min-height: 400px;
}
```

## 第四步：创建商品模块（15分钟）

按照相同方式创建商品应用：

```bash
cd ../product-app
# 安装相同依赖，配置webpack.config.js（端口3002）
```

创建 `product-app/src/App.js`：

```javascript
import React, { useState } from 'react';
import './App.css';

function ProductApp() {
  const [products] = useState([
    { id: 1, name: '商品A', price: 99.99, stock: 100 },
    { id: 2, name: '商品B', price: 199.99, stock: 50 },
    { id: 3, name: '商品C', price: 299.99, stock: 30 },
  ]);

  return (
    <div className="product-app">
      <h1>商品管理模块</h1>
      <div className="product-grid">
        {products.map(product => (
          <div key={product.id} className="product-card">
            <h3>{product.name}</h3>
            <p className="price">¥{product.price}</p>
            <p className="stock">库存: {product.stock}</p>
            <button className="btn-primary">添加到购物车</button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ProductApp;
```

## 第五步：创建订单模块（15分钟）

创建 `order-app/src/App.js`：

```javascript
import React, { useState } from 'react';
import './App.css';

function OrderApp() {
  const [orders] = useState([
    { id: 1, orderNo: 'ORD001', total: 299.99, status: '已完成', date: '2024-01-15' },
    { id: 2, orderNo: 'ORD002', total: 199.99, status: '处理中', date: '2024-01-16' },
    { id: 3, orderNo: 'ORD003', total: 399.99, status: '待支付', date: '2024-01-17' },
  ]);

  return (
    <div className="order-app">
      <h1>订单管理模块</h1>
      <table className="order-table">
        <thead>
          <tr>
            <th>订单号</th>
            <th>金额</th>
            <th>状态</th>
            <th>日期</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {orders.map(order => (
            <tr key={order.id}>
              <td>{order.orderNo}</td>
              <td>¥{order.total}</td>
              <td>
                <span className={`status status-${order.status}`}>
                  {order.status}
                </span>
              </td>
              <td>{order.date}</td>
              <td>
                <button className="btn-link">查看详情</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default OrderApp;
```

## 第六步：运行和测试（10分钟）

### 1. 启动所有应用

```bash
# 终端1：启动主应用
cd host-app
npm start

# 终端2：启动用户应用
cd user-app
npm start

# 终端3：启动商品应用
cd product-app
npm start

# 终端4：启动订单应用
cd order-app
npm start
```

### 2. 访问应用

打开浏览器访问 `http://localhost:3000`，你应该能看到：
- 顶部导航栏
- 点击不同链接加载不同的微前端模块
- 每个模块独立运行在不同端口

## 第七步：优化和最佳实践（10分钟）

### 1. 共享状态管理

创建共享状态管理工具：

```javascript
// shared/state.js
class SharedState {
  constructor() {
    this.listeners = [];
    this.state = {};
  }

  setState(newState) {
    this.state = { ...this.state, ...newState };
    this.notifyListeners();
  }

  getState() {
    return this.state;
  }

  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  notifyListeners() {
    this.listeners.forEach(listener => listener(this.state));
  }
}

export default new SharedState();
```

### 2. 错误边界

```javascript
// shared/ErrorBoundary.js
import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('微前端错误:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return <div className="error-fallback">模块加载失败，请刷新重试</div>;
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
```

### 3. 性能优化

```javascript
// 使用React.lazy和Suspense
const UserApp = lazy(() => 
  import('userApp/UserApp').catch(() => ({ 
    default: () => <div>模块加载失败</div> 
  }))
);
```

## 常见问题解决

### 问题1：模块加载失败

```javascript
// 检查remoteEntry.js是否可访问
// 确保所有应用都已启动
// 检查webpack配置中的URL是否正确
```

### 问题2：共享依赖冲突

```javascript
// 确保所有应用使用相同版本的共享依赖
shared: {
  react: { singleton: true, requiredVersion: '^18.0.0' },
}
```

### 问题3：路由冲突

```javascript
// 使用不同的路由前缀
<Route path="/users/*" element={<UserApp />} />
```

## 部署到生产环境

### 1. 构建所有应用

```bash
# 构建主应用
cd host-app
npm run build

# 构建子应用
cd ../user-app && npm run build
cd ../product-app && npm run build
cd ../order-app && npm run build
```

### 2. 配置生产环境URL

```javascript
// webpack.config.js
const isProduction = process.env.NODE_ENV === 'production';
const userAppUrl = isProduction 
  ? 'https://user-app.example.com/remoteEntry.js'
  : 'http://localhost:3001/remoteEntry.js';
```

### 3. 使用CDN部署

将每个应用的构建产物部署到CDN，然后在主应用中引用CDN地址。

## 总结

通过本教程，你已经掌握了：
- ✅ Module Federation配置
- ✅ 微前端架构设计
- ✅ 独立开发和部署
- ✅ 共享依赖管理
- ✅ 路由集成
- ✅ 错误处理

现在你可以基于这个架构，构建更大规模的微前端应用！

## 参考资源

- [Webpack Module Federation](https://webpack.js.org/concepts/module-federation/)
- [微前端架构指南](https://micro-frontends.org/)
- [Single-SPA框架](https://single-spa.js.org/)
