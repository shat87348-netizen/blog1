---
layout: post
title: "Kubernetes实战：从Docker到生产部署完整指南"
date: 2025-09-14
categories: [others]
tags: [Kubernetes, Docker, 容器化, 部署, 实战教程]
author: zhangshuming
---

# Kubernetes实战：从Docker到生产部署完整指南

本教程将带你从零开始，学习如何将应用容器化、部署到Kubernetes集群，并实现自动化CI/CD流程。我们将构建一个完整的Node.js应用，并完成从开发到生产的全流程。

## 项目目标

- 将Node.js应用容器化
- 部署到本地Kubernetes集群
- 配置Service和Ingress
- 实现滚动更新
- 设置健康检查
- 配置资源限制

## 第一步：准备应用（10分钟）

### 1. 创建Node.js应用

```bash
mkdir k8s-demo-app
cd k8s-demo-app
npm init -y
npm install express
```

创建 `app.js`：

```javascript
const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// 健康检查端点
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// 就绪检查端点
app.get('/ready', (req, res) => {
  res.json({ status: 'ready' });
});

// API端点
app.get('/api/hello', (req, res) => {
  res.json({ 
    message: 'Hello from Kubernetes!',
    hostname: process.env.HOSTNAME || 'unknown',
    version: process.env.APP_VERSION || '1.0.0'
  });
});

app.get('/api/info', (req, res) => {
  res.json({
    nodeVersion: process.version,
    platform: process.platform,
    memory: process.memoryUsage(),
    uptime: process.uptime()
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running on port ${PORT}`);
});
```

创建 `package.json` 脚本：

```json
{
  "scripts": {
    "start": "node app.js",
    "dev": "nodemon app.js"
  }
}
```

### 2. 测试应用

```bash
node app.js
# 在另一个终端测试
curl http://localhost:3000/health
curl http://localhost:3000/api/hello
```

## 第二步：容器化应用（15分钟）

### 1. 创建Dockerfile

创建 `Dockerfile`：

```dockerfile
# 多阶段构建
FROM node:18-alpine AS builder

WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production

# 生产阶段
FROM node:18-alpine

WORKDIR /app

# 从builder阶段复制依赖
COPY --from=builder /app/node_modules ./node_modules

# 复制应用代码
COPY app.js ./
COPY package.json ./

# 创建非root用户
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

USER nodejs

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# 启动应用
CMD ["node", "app.js"]
```

### 2. 创建.dockerignore

```
node_modules
npm-debug.log
.git
.gitignore
README.md
.env
.nyc_output
coverage
```

### 3. 构建和测试镜像

```bash
# 构建镜像
docker build -t k8s-demo-app:1.0.0 .

# 测试运行
docker run -d -p 3000:3000 --name demo-app k8s-demo-app:1.0.0

# 测试
curl http://localhost:3000/health

# 查看日志
docker logs demo-app

# 停止容器
docker stop demo-app && docker rm demo-app
```

### 4. 推送到镜像仓库（可选）

```bash
# 登录Docker Hub
docker login

# 标记镜像
docker tag k8s-demo-app:1.0.0 yourusername/k8s-demo-app:1.0.0

# 推送镜像
docker push yourusername/k8s-demo-app:1.0.0
```

## 第三步：安装Kubernetes（10分钟）

### 选项1：使用Minikube（推荐用于本地开发）

```bash
# 安装Minikube
# macOS
brew install minikube

# Linux
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# 启动Minikube
minikube start

# 验证
kubectl get nodes
```

### 选项2：使用Docker Desktop（最简单）

Docker Desktop内置Kubernetes，只需在设置中启用即可。

### 选项3：使用Kind（Kubernetes in Docker）

```bash
# 安装kind
brew install kind  # macOS
# 或
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# 创建集群
kind create cluster --name demo-cluster

# 验证
kubectl cluster-info --context kind-demo-cluster
```

## 第四步：部署到Kubernetes（20分钟）

### 1. 创建Deployment

创建 `k8s/deployment.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: k8s-demo-app
  labels:
    app: k8s-demo-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: k8s-demo-app
  template:
    metadata:
      labels:
        app: k8s-demo-app
    spec:
      containers:
      - name: app
        image: k8s-demo-app:1.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 3000
          name: http
        env:
        - name: PORT
          value: "3000"
        - name: APP_VERSION
          value: "1.0.0"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
```

### 2. 创建Service

创建 `k8s/service.yaml`：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: k8s-demo-app-service
  labels:
    app: k8s-demo-app
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 3000
    protocol: TCP
    name: http
  selector:
    app: k8s-demo-app
```

### 3. 部署应用

```bash
# 如果使用Minikube，需要先加载镜像
minikube image load k8s-demo-app:1.0.0

# 或使用kind
kind load docker-image k8s-demo-app:1.0.0 --name demo-cluster

# 部署
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 查看状态
kubectl get pods
kubectl get deployments
kubectl get services

# 查看Pod详情
kubectl describe pod <pod-name>

# 查看日志
kubectl logs -f deployment/k8s-demo-app
```

### 4. 测试应用

```bash
# 端口转发
kubectl port-forward service/k8s-demo-app-service 8080:80

# 在另一个终端测试
curl http://localhost:8080/health
curl http://localhost:8080/api/hello
```

## 第五步：配置Ingress（10分钟）

### 1. 安装Ingress Controller

```bash
# 使用Minikube
minikube addons enable ingress

# 或使用Nginx Ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
```

### 2. 创建Ingress

创建 `k8s/ingress.yaml`：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: k8s-demo-app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: demo-app.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: k8s-demo-app-service
            port:
              number: 80
```

### 3. 应用Ingress

```bash
kubectl apply -f k8s/ingress.yaml

# 获取Ingress IP（Minikube）
minikube ip

# 或查看Ingress
kubectl get ingress

# 添加到hosts文件（可选）
echo "$(minikube ip) demo-app.local" | sudo tee -a /etc/hosts

# 测试
curl http://demo-app.local/api/hello
```

## 第六步：配置ConfigMap和Secret（10分钟）

### 1. 创建ConfigMap

创建 `k8s/configmap.yaml`：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_NAME: "K8s Demo App"
  LOG_LEVEL: "info"
  ENVIRONMENT: "production"
```

### 2. 创建Secret

```bash
# 创建Secret
kubectl create secret generic app-secret \
  --from-literal=database-url=postgresql://user:pass@localhost/db \
  --from-literal=api-key=your-api-key-here

# 或使用YAML文件
```

创建 `k8s/secret.yaml`：

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
type: Opaque
stringData:
  database-url: postgresql://user:password@localhost/db
  api-key: your-secret-api-key
```

### 3. 更新Deployment使用ConfigMap和Secret

更新 `k8s/deployment.yaml`：

```yaml
spec:
  template:
    spec:
      containers:
      - name: app
        env:
        - name: PORT
          value: "3000"
        - name: APP_VERSION
          value: "1.0.0"
        - name: APP_NAME
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: APP_NAME
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: LOG_LEVEL
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secret
              key: database-url
```

应用更新：

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
```

## 第七步：滚动更新和回滚（10分钟）

### 1. 构建新版本

```bash
# 构建新版本
docker build -t k8s-demo-app:2.0.0 .

# 加载到集群
minikube image load k8s-demo-app:2.0.0
```

### 2. 更新Deployment

```bash
# 方法1：使用kubectl set image
kubectl set image deployment/k8s-demo-app app=k8s-demo-app:2.0.0

# 方法2：编辑YAML文件
kubectl edit deployment k8s-demo-app
# 修改 image: k8s-demo-app:2.0.0

# 方法3：使用apply
# 修改deployment.yaml中的镜像版本，然后
kubectl apply -f k8s/deployment.yaml
```

### 3. 查看更新状态

```bash
# 查看滚动更新状态
kubectl rollout status deployment/k8s-demo-app

# 查看更新历史
kubectl rollout history deployment/k8s-demo-app

# 查看历史详情
kubectl rollout history deployment/k8s-demo-app --revision=2
```

### 4. 回滚

```bash
# 回滚到上一个版本
kubectl rollout undo deployment/k8s-demo-app

# 回滚到指定版本
kubectl rollout undo deployment/k8s-demo-app --to-revision=1
```

## 第八步：扩缩容（5分钟）

### 1. 手动扩缩容

```bash
# 扩展到5个副本
kubectl scale deployment k8s-demo-app --replicas=5

# 查看Pod
kubectl get pods

# 缩减到2个副本
kubectl scale deployment k8s-demo-app --replicas=2
```

### 2. 自动扩缩容（HPA）

```bash
# 安装metrics-server（如果未安装）
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 创建HPA
kubectl autoscale deployment k8s-demo-app \
  --cpu-percent=70 \
  --min=2 \
  --max=10

# 查看HPA
kubectl get hpa

# 测试：增加负载
kubectl run -i --tty load-generator --rm --image=busybox --restart=Never -- /bin/sh -c "while true; do wget -q -O- http://k8s-demo-app-service/api/hello; done"
```

## 第九步：监控和日志（10分钟）

### 1. 查看日志

```bash
# 查看Pod日志
kubectl logs <pod-name>

# 查看所有Pod日志
kubectl logs -l app=k8s-demo-app

# 实时跟踪日志
kubectl logs -f deployment/k8s-demo-app

# 查看最近100行
kubectl logs --tail=100 deployment/k8s-demo-app
```

### 2. 查看资源使用

```bash
# 查看Pod资源使用
kubectl top pods

# 查看节点资源使用
kubectl top nodes

# 查看详细信息
kubectl describe pod <pod-name>
```

## 常见问题解决

### 问题1：Pod无法启动

```bash
# 查看Pod状态
kubectl get pods
kubectl describe pod <pod-name>

# 查看日志
kubectl logs <pod-name>

# 常见原因：
# - 镜像拉取失败：检查镜像名称和仓库
# - 资源不足：检查节点资源
# - 配置错误：检查环境变量和ConfigMap
```

### 问题2：Service无法访问

```bash
# 检查Service
kubectl get svc
kubectl describe svc k8s-demo-app-service

# 检查Endpoints
kubectl get endpoints

# 测试从Pod内部访问
kubectl run -it --rm debug --image=busybox --restart=Never -- wget -q -O- http://k8s-demo-app-service/api/hello
```

### 问题3：镜像拉取失败

```bash
# 使用本地镜像（Minikube）
minikube image load k8s-demo-app:1.0.0

# 或设置imagePullPolicy为IfNotPresent
```

## 生产环境最佳实践

### 1. 资源限制

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "200m"
  limits:
    memory: "512Mi"
    cpu: "1000m"
```

### 2. 多副本部署

```yaml
replicas: 3
```

### 3. 健康检查

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 3000
readinessProbe:
  httpGet:
    path: /ready
    port: 3000
```

### 4. 安全配置

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  allowPrivilegeEscalation: false
```

## 总结

通过本教程，你已经掌握了：
- ✅ Docker容器化应用
- ✅ Kubernetes基础部署
- ✅ Service和Ingress配置
- ✅ ConfigMap和Secret使用
- ✅ 滚动更新和回滚
- ✅ 扩缩容操作
- ✅ 监控和日志查看

现在你可以将应用部署到生产环境的Kubernetes集群了！

## 参考资源

- [Kubernetes官方文档](https://kubernetes.io/zh-cn/docs/)
- [Docker文档](https://docs.docker.com/)
- [Minikube文档](https://minikube.sigs.k8s.io/docs/)
