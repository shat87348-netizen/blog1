# zhangshuming技术博客

## 功能特性

### 文章分页功能
- 每页显示10篇文章
- 支持分类筛选和标签筛选
- 智能分页导航，最多显示5个页码按钮
- 响应式设计，支持移动端

### 分页控件特性
- 显示当前页信息（如：显示第1-10篇，共25篇）
- 上一页/下一页按钮
- 页码按钮（当前页高亮显示）
- 省略号显示（当页码过多时）
- 第一页和最后一页快速跳转

### 使用方法
1. 在文章列表页面选择全部文章或主题分类
2. 可选择标签进行进一步筛选
3. 使用分页控件浏览不同页面的文章
4. 点击页码按钮或上一页/下一页按钮进行导航

### 分类约定

分类用于主导航，一篇文章只选一个主分类；更具体的技术点使用标签表达。

| 分类 | 适用内容 |
| --- | --- |
| `articles` | 前端、后端、容器与工程实践等主体技术文章 |
| `tools` | 开发工具、效率工作流与资源整理 |
| `other` | AI、探索性主题与其他技术笔记 |

### 技术实现
- 使用JavaScript实现客户端分页
- 支持动态筛选和分页
- 响应式CSS样式
- 平滑滚动到文章列表顶部

## 开发说明
- 分页大小：`postsPerPage = 10`
- 最大显示页码：5个
- 支持分类和标签组合筛选
- 自动重置分页状态

## 文件结构
- `_layouts/post.html` - 主要布局文件，包含分页逻辑
- `_data/categories.yml` - 分类名称、顺序和说明
- `_posts/<category>/` - 按主分类存放的文章
- `css/style.scss` - 样式文件

文章目录、分类、标签和搜索数据均由 Jekyll 的 `site.posts` 在构建时自动生成，不需要额外运行 Python 脚本。

## 部署说明

### Cloudflare Pages 部署

项目使用 GitHub Actions 自动构建并部署到 Cloudflare Pages。

#### 前置准备

1. **获取 Cloudflare API Token**
   - 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
   - 进入 **My Profile** > **API Tokens** > **Create Token**
   - 使用 **Edit Cloudflare Workers** 模板或自定义权限（Account: Cloudflare Pages:Edit）

2. **获取 Account ID**
   - 在 Cloudflare Dashboard 右侧边栏可以看到 **Account ID**

3. **配置 GitHub Secrets**
   - 进入 GitHub 仓库 **Settings** > **Secrets and variables** > **Actions**
   - 添加以下 secrets：
     - `CLOUDFLARE_API_TOKEN`: Cloudflare API Token
     - `CLOUDFLARE_ACCOUNT_ID`: Cloudflare Account ID

#### 自动部署

- 推送代码到 `main` 分支会自动触发构建和部署
- 也可以在 GitHub Actions 中手动触发工作流

详细部署指南请参考 [cloudflare-pages.md](./cloudflare-pages.md)

### 本地开发

```bash
# 安装依赖
bundle install

# 启动带自动重载的本地服务器
npm run dev

# 构建静态站点
npm run build
```

### 新增文章

在对应分类目录中创建 `_posts/<category>/YYYY-MM-DD-slug.md`：

```yaml
---
layout: post
title: "文章标题"
date: 2026-08-18
categories: [articles]
tags: [JavaScript, 架构]
author: zhangshuming
excerpt: "一句话摘要，建议填写。"
---
```

保存后，Jekyll 会自动更新文章列表、分类计数、标签筛选和搜索数据。

如果是对已发布文章重新分类，请保留原 URL：在 front matter 中增加 `permalink`，避免历史链接失效。
