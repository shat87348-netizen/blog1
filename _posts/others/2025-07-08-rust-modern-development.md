---
layout: post
title: "用Rust构建高性能Web API：从零到部署实战"
date: 2025-07-08
categories: [others]
tags: [Rust, Web开发, Actix-web, 实战教程]
author: zhangshuming
---

# 用Rust构建高性能Web API：从零到部署实战

本教程将带你使用Rust和Actix-web框架，从零开始构建一个完整的RESTful API服务，包括数据库集成、认证授权、错误处理等生产级功能。

## 项目目标

构建一个待办事项（Todo）API，功能包括：
- 用户注册和登录
- JWT认证
- CRUD操作（创建、读取、更新、删除）
- 数据库持久化
- 输入验证
- 错误处理

## 第一步：环境准备（5分钟）

### 1. 安装Rust

```bash
# 安装Rust（如果未安装）
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 验证安装
rustc --version
cargo --version
```

### 2. 创建项目

```bash
cargo new todo-api
cd todo-api
```

### 3. 配置依赖

编辑 `Cargo.toml`：

```toml
[package]
name = "todo-api"
version = "0.1.0"
edition = "2021"

[dependencies]
actix-web = "4.4"
actix-rt = "2.9"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tokio = { version = "1", features = ["full"] }
sqlx = { version = "0.7", features = ["runtime-tokio-native-tls", "postgres", "chrono", "uuid"] }
chrono = { version = "0.4", features = ["serde"] }
uuid = { version = "1.6", features = ["v4", "serde"] }
jsonwebtoken = "9.2"
bcrypt = "0.15"
dotenv = "0.15"
validator = { version = "0.18", features = ["derive"] }
```

## 第二步：项目结构（5分钟）

创建以下目录和文件：

```
todo-api/
├── src/
│   ├── main.rs
│   ├── handlers/
│   │   ├── mod.rs
│   │   ├── auth.rs
│   │   └── todos.rs
│   ├── models/
│   │   ├── mod.rs
│   │   ├── user.rs
│   │   └── todo.rs
│   ├── db.rs
│   ├── auth.rs
│   └── errors.rs
├── migrations/
│   └── 001_initial.sql
├── Cargo.toml
└── .env
```

## 第三步：数据库设置（10分钟）

### 1. 创建数据库

```bash
# 安装PostgreSQL（如果未安装）
# macOS: brew install postgresql
# Ubuntu: sudo apt-get install postgresql

# 创建数据库
createdb todo_db

# 或使用Docker
docker run --name postgres-todo \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=todo_db \
  -p 5432:5432 \
  -d postgres:15
```

### 2. 创建迁移文件

创建 `migrations/001_initial.sql`：

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 待办事项表
CREATE TABLE todos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_todos_user_id ON todos(user_id);
CREATE INDEX idx_todos_completed ON todos(completed);
```

### 3. 执行迁移

```bash
# 安装sqlx-cli
cargo install sqlx-cli

# 配置数据库URL
echo "DATABASE_URL=postgresql://postgres:password@localhost/todo_db" > .env

# 运行迁移
sqlx migrate run
```

## 第四步：实现核心代码（30分钟）

### 1. 错误处理模块

创建 `src/errors.rs`：

```rust
use actix_web::{HttpResponse, ResponseError};
use serde_json::json;

#[derive(Debug)]
pub enum AppError {
    DatabaseError(sqlx::Error),
    NotFound(String),
    Unauthorized(String),
    ValidationError(String),
    InternalError(String),
}

impl std::fmt::Display for AppError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            AppError::DatabaseError(e) => write!(f, "数据库错误: {}", e),
            AppError::NotFound(msg) => write!(f, "未找到: {}", msg),
            AppError::Unauthorized(msg) => write!(f, "未授权: {}", msg),
            AppError::ValidationError(msg) => write!(f, "验证错误: {}", msg),
            AppError::InternalError(msg) => write!(f, "内部错误: {}", msg),
        }
    }
}

impl ResponseError for AppError {
    fn error_response(&self) -> HttpResponse {
        match self {
            AppError::DatabaseError(_) => {
                HttpResponse::InternalServerError().json(json!({
                    "error": "数据库操作失败"
                }))
            }
            AppError::NotFound(msg) => {
                HttpResponse::NotFound().json(json!({
                    "error": msg
                }))
            }
            AppError::Unauthorized(msg) => {
                HttpResponse::Unauthorized().json(json!({
                    "error": msg
                }))
            }
            AppError::ValidationError(msg) => {
                HttpResponse::BadRequest().json(json!({
                    "error": msg
                }))
            }
            AppError::InternalError(msg) => {
                HttpResponse::InternalServerError().json(json!({
                    "error": msg
                }))
            }
        }
    }
}

impl From<sqlx::Error> for AppError {
    fn from(err: sqlx::Error) -> Self {
        AppError::DatabaseError(err)
    }
}
```

### 2. 数据库连接

创建 `src/db.rs`：

```rust
use sqlx::{PgPool, Pool, Postgres};

pub type DbPool = Pool<Postgres>;

pub async fn create_pool(database_url: &str) -> Result<PgPool, sqlx::Error> {
    PgPool::connect(database_url).await
}
```

### 3. 用户模型

创建 `src/models/user.rs`：

```rust
use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;
use chrono::{DateTime, Utc};
use validator::Validate;

#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct User {
    pub id: Uuid,
    pub username: String,
    pub email: String,
    #[serde(skip_serializing)]
    pub password_hash: String,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize, Validate)]
pub struct RegisterRequest {
    #[validate(length(min = 3, max = 50))]
    pub username: String,
    #[validate(email)]
    pub email: String,
    #[validate(length(min = 6))]
    pub password: String,
}

#[derive(Debug, Deserialize)]
pub struct LoginRequest {
    pub email: String,
    pub password: String,
}

#[derive(Debug, Serialize)]
pub struct AuthResponse {
    pub token: String,
    pub user: UserResponse,
}

#[derive(Debug, Serialize)]
pub struct UserResponse {
    pub id: Uuid,
    pub username: String,
    pub email: String,
    pub created_at: DateTime<Utc>,
}

impl From<User> for UserResponse {
    fn from(user: User) -> Self {
        UserResponse {
            id: user.id,
            username: user.username,
            email: user.email,
            created_at: user.created_at,
        }
    }
}
```

创建 `src/models/mod.rs`：

```rust
pub mod user;
pub mod todo;

pub use user::*;
pub use todo::*;
```

### 4. 认证模块

创建 `src/auth.rs`：

```rust
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use serde::{Deserialize, Serialize};
use chrono::{Duration, Utc};
use uuid::Uuid;
use bcrypt::{hash, verify, DEFAULT_COST};

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String, // user id
    pub exp: i64,
    pub iat: i64,
}

pub fn hash_password(password: &str) -> Result<String, bcrypt::BcryptError> {
    hash(password, DEFAULT_COST)
}

pub fn verify_password(password: &str, hash: &str) -> Result<bool, bcrypt::BcryptError> {
    verify(password, hash)
}

pub fn create_token(user_id: Uuid) -> Result<String, jsonwebtoken::errors::Error> {
    let secret = std::env::var("JWT_SECRET")
        .unwrap_or_else(|_| "your-secret-key-change-in-production".to_string());
    
    let now = Utc::now();
    let exp = (now + Duration::hours(24)).timestamp();
    
    let claims = Claims {
        sub: user_id.to_string(),
        exp,
        iat: now.timestamp(),
    };
    
    encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(secret.as_ref()),
    )
}

pub fn verify_token(token: &str) -> Result<Uuid, jsonwebtoken::errors::Error> {
    let secret = std::env::var("JWT_SECRET")
        .unwrap_or_else(|_| "your-secret-key-change-in-production".to_string());
    
    let validation = Validation::default();
    let token_data = decode::<Claims>(
        token,
        &DecodingKey::from_secret(secret.as_ref()),
        &validation,
    )?;
    
    Ok(Uuid::parse_str(&token_data.claims.sub)
        .map_err(|_| jsonwebtoken::errors::Error::from(jsonwebtoken::errors::ErrorKind::InvalidToken))?)
}
```

### 5. 认证处理器

创建 `src/handlers/auth.rs`：

```rust
use actix_web::{web, HttpResponse, Result};
use sqlx::PgPool;
use crate::errors::AppError;
use crate::models::{RegisterRequest, LoginRequest, AuthResponse, User, UserResponse};
use crate::auth::{hash_password, verify_password, create_token};

pub async fn register(
    pool: web::Data<PgPool>,
    req: web::Json<RegisterRequest>,
) -> Result<HttpResponse, AppError> {
    // 验证输入
    req.validate()
        .map_err(|e| AppError::ValidationError(e.to_string()))?;
    
    // 检查用户是否已存在
    let existing = sqlx::query_as::<_, User>(
        "SELECT * FROM users WHERE email = $1 OR username = $2"
    )
    .bind(&req.email)
    .bind(&req.username)
    .fetch_optional(pool.get_ref())
    .await?;
    
    if existing.is_some() {
        return Err(AppError::ValidationError("用户已存在".to_string()));
    }
    
    // 哈希密码
    let password_hash = hash_password(&req.password)
        .map_err(|_| AppError::InternalError("密码加密失败".to_string()))?;
    
    // 创建用户
    let user = sqlx::query_as::<_, User>(
        "INSERT INTO users (username, email, password_hash) 
         VALUES ($1, $2, $3) 
         RETURNING *"
    )
    .bind(&req.username)
    .bind(&req.email)
    .bind(&password_hash)
    .fetch_one(pool.get_ref())
    .await?;
    
    // 生成token
    let token = create_token(user.id)
        .map_err(|_| AppError::InternalError("Token生成失败".to_string()))?;
    
    Ok(HttpResponse::Ok().json(AuthResponse {
        token,
        user: UserResponse::from(user),
    }))
}

pub async fn login(
    pool: web::Data<PgPool>,
    req: web::Json<LoginRequest>,
) -> Result<HttpResponse, AppError> {
    // 查找用户
    let user = sqlx::query_as::<_, User>(
        "SELECT * FROM users WHERE email = $1"
    )
    .bind(&req.email)
    .fetch_optional(pool.get_ref())
    .await?
    .ok_or_else(|| AppError::Unauthorized("邮箱或密码错误".to_string()))?;
    
    // 验证密码
    if !verify_password(&req.password, &user.password_hash)
        .map_err(|_| AppError::InternalError("密码验证失败".to_string()))? {
        return Err(AppError::Unauthorized("邮箱或密码错误".to_string()));
    }
    
    // 生成token
    let token = create_token(user.id)
        .map_err(|_| AppError::InternalError("Token生成失败".to_string()))?;
    
    Ok(HttpResponse::Ok().json(AuthResponse {
        token,
        user: UserResponse::from(user),
    }))
}
```

### 6. Todo模型和处理器

创建 `src/models/todo.rs`：

```rust
use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;
use chrono::{DateTime, Utc};
use validator::Validate;

#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct Todo {
    pub id: Uuid,
    pub user_id: Uuid,
    pub title: String,
    pub description: Option<String>,
    pub completed: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize, Validate)]
pub struct CreateTodoRequest {
    #[validate(length(min = 1, max = 200))]
    pub title: String,
    pub description: Option<String>,
}

#[derive(Debug, Deserialize, Validate)]
pub struct UpdateTodoRequest {
    #[validate(length(min = 1, max = 200))]
    pub title: Option<String>,
    pub description: Option<String>,
    pub completed: Option<bool>,
}
```

创建 `src/handlers/todos.rs`：

```rust
use actix_web::{web, HttpResponse};
use sqlx::PgPool;
use uuid::Uuid;
use crate::errors::AppError;
use crate::models::{Todo, CreateTodoRequest, UpdateTodoRequest};
use crate::auth::verify_token;

// 从请求头提取用户ID的辅助函数
fn get_user_id_from_token(req: &actix_web::HttpRequest) -> Result<Uuid, AppError> {
    let auth_header = req.headers()
        .get("Authorization")
        .and_then(|h| h.to_str().ok())
        .ok_or_else(|| AppError::Unauthorized("缺少认证头".to_string()))?;
    
    let token = auth_header.strip_prefix("Bearer ")
        .ok_or_else(|| AppError::Unauthorized("无效的认证格式".to_string()))?;
    
    verify_token(token)
        .map_err(|_| AppError::Unauthorized("无效的Token".to_string()))
}

pub async fn create_todo(
    pool: web::Data<PgPool>,
    req: web::Json<CreateTodoRequest>,
    http_req: actix_web::HttpRequest,
) -> Result<HttpResponse, AppError> {
    req.validate()
        .map_err(|e| AppError::ValidationError(e.to_string()))?;
    
    let user_id = get_user_id_from_token(&http_req)?;
    
    let todo = sqlx::query_as::<_, Todo>(
        "INSERT INTO todos (user_id, title, description) 
         VALUES ($1, $2, $3) 
         RETURNING *"
    )
    .bind(user_id)
    .bind(&req.title)
    .bind(&req.description)
    .fetch_one(pool.get_ref())
    .await?;
    
    Ok(HttpResponse::Created().json(todo))
}

pub async fn get_todos(
    pool: web::Data<PgPool>,
    http_req: actix_web::HttpRequest,
) -> Result<HttpResponse, AppError> {
    let user_id = get_user_id_from_token(&http_req)?;
    
    let todos = sqlx::query_as::<_, Todo>(
        "SELECT * FROM todos WHERE user_id = $1 ORDER BY created_at DESC"
    )
    .bind(user_id)
    .fetch_all(pool.get_ref())
    .await?;
    
    Ok(HttpResponse::Ok().json(todos))
}

pub async fn get_todo(
    pool: web::Data<PgPool>,
    path: web::Path<Uuid>,
    http_req: actix_web::HttpRequest,
) -> Result<HttpResponse, AppError> {
    let user_id = get_user_id_from_token(&http_req)?;
    let todo_id = path.into_inner();
    
    let todo = sqlx::query_as::<_, Todo>(
        "SELECT * FROM todos WHERE id = $1 AND user_id = $2"
    )
    .bind(todo_id)
    .bind(user_id)
    .fetch_optional(pool.get_ref())
    .await?
    .ok_or_else(|| AppError::NotFound("待办事项不存在".to_string()))?;
    
    Ok(HttpResponse::Ok().json(todo))
}

pub async fn update_todo(
    pool: web::Data<PgPool>,
    path: web::Path<Uuid>,
    req: web::Json<UpdateTodoRequest>,
    http_req: actix_web::HttpRequest,
) -> Result<HttpResponse, AppError> {
    req.validate()
        .map_err(|e| AppError::ValidationError(e.to_string()))?;
    
    let user_id = get_user_id_from_token(&http_req)?;
    let todo_id = path.into_inner();
    
    // 检查todo是否存在且属于该用户
    let existing = sqlx::query_as::<_, Todo>(
        "SELECT * FROM todos WHERE id = $1 AND user_id = $2"
    )
    .bind(todo_id)
    .bind(user_id)
    .fetch_optional(pool.get_ref())
    .await?
    .ok_or_else(|| AppError::NotFound("待办事项不存在".to_string()))?;
    
    let title = req.title.as_ref().unwrap_or(&existing.title);
    let description = req.description.as_ref().or(existing.description.as_ref());
    let completed = req.completed.unwrap_or(existing.completed);
    
    let todo = sqlx::query_as::<_, Todo>(
        "UPDATE todos 
         SET title = $1, description = $2, completed = $3, updated_at = CURRENT_TIMESTAMP
         WHERE id = $4 AND user_id = $5
         RETURNING *"
    )
    .bind(title)
    .bind(description)
    .bind(completed)
    .bind(todo_id)
    .bind(user_id)
    .fetch_one(pool.get_ref())
    .await?;
    
    Ok(HttpResponse::Ok().json(todo))
}

pub async fn delete_todo(
    pool: web::Data<PgPool>,
    path: web::Path<Uuid>,
    http_req: actix_web::HttpRequest,
) -> Result<HttpResponse, AppError> {
    let user_id = get_user_id_from_token(&http_req)?;
    let todo_id = path.into_inner();
    
    let rows_affected = sqlx::query(
        "DELETE FROM todos WHERE id = $1 AND user_id = $2"
    )
    .bind(todo_id)
    .bind(user_id)
    .execute(pool.get_ref())
    .await?
    .rows_affected();
    
    if rows_affected == 0 {
        return Err(AppError::NotFound("待办事项不存在".to_string()));
    }
    
    Ok(HttpResponse::NoContent().finish())
}
```

创建 `src/handlers/mod.rs`：

```rust
pub mod auth;
pub mod todos;
```

### 7. 主程序

编辑 `src/main.rs`：

```rust
use actix_web::{web, App, HttpServer};
use dotenv::dotenv;
use std::env;

mod db;
mod models;
mod handlers;
mod auth;
mod errors;

use db::create_pool;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    dotenv().ok();
    
    let database_url = env::var("DATABASE_URL")
        .expect("DATABASE_URL must be set");
    
    let pool = create_pool(&database_url)
        .await
        .expect("Failed to create database pool");
    
    println!("🚀 服务器启动在 http://127.0.0.1:8080");
    
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .service(
                web::scope("/api")
                    .route("/register", web::post().to(handlers::auth::register))
                    .route("/login", web::post().to(handlers::auth::login))
                    .service(
                        web::scope("/todos")
                            .route("", web::get().to(handlers::todos::get_todos))
                            .route("", web::post().to(handlers::todos::create_todo))
                            .route("/{id}", web::get().to(handlers::todos::get_todo))
                            .route("/{id}", web::put().to(handlers::todos::update_todo))
                            .route("/{id}", web::delete().to(handlers::todos::delete_todo))
                    )
            )
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
```

## 第五步：运行和测试（10分钟）

### 1. 配置环境变量

创建 `.env` 文件：

```bash
DATABASE_URL=postgresql://postgres:password@localhost/todo_db
JWT_SECRET=your-super-secret-key-change-in-production
```

### 2. 运行服务器

```bash
cargo run
```

### 3. 测试API

```bash
# 注册用户
curl -X POST http://localhost:8080/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'

# 登录
curl -X POST http://localhost:8080/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'

# 创建待办事项（使用返回的token）
curl -X POST http://localhost:8080/api/todos \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "学习Rust",
    "description": "完成Web API教程"
  }'

# 获取所有待办事项
curl -X GET http://localhost:8080/api/todos \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 常见问题解决

### 问题1：编译错误 - 缺少依赖

```bash
# 确保所有依赖都在Cargo.toml中
cargo build
```

### 问题2：数据库连接失败

```bash
# 检查PostgreSQL是否运行
pg_isready

# 检查DATABASE_URL是否正确
echo $DATABASE_URL
```

### 问题3：迁移失败

```bash
# 手动执行SQL
psql -d todo_db -f migrations/001_initial.sql
```

## 部署到生产环境

### 使用Docker

创建 `Dockerfile`：

```dockerfile
FROM rust:1.75 as builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/todo-api /usr/local/bin/
CMD ["todo-api"]
```

### 使用Docker Compose

创建 `docker-compose.yml`：

```yaml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: todo_db
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      DATABASE_URL: postgresql://postgres:password@db/todo_db
      JWT_SECRET: your-secret-key
    depends_on:
      - db

volumes:
  postgres_data:
```

## 总结

通过本教程，你已经掌握了：
- ✅ 使用Rust和Actix-web构建Web API
- ✅ 数据库集成和迁移
- ✅ JWT认证实现
- ✅ 错误处理和输入验证
- ✅ RESTful API设计

现在你可以基于这个项目，扩展更多功能，构建生产级的Rust Web应用！

## 参考资源

- [Actix-web文档](https://actix.rs/)
- [SQLx文档](https://docs.rs/sqlx/)
- [Rust Book](https://doc.rust-lang.org/book/)
