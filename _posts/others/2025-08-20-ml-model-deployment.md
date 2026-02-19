---
layout: post
title: "机器学习模型部署实战：从训练到生产环境完整流程"
date: 2025-08-20
categories: [others]
tags: [机器学习, 模型部署, Flask, Docker, 实战教程]
author: zhangshuming
---

# 机器学习模型部署实战：从训练到生产环境完整流程

本教程将带你完成一个完整的机器学习项目，从模型训练到生产部署。我们将构建一个图像分类API，使用Flask部署，并通过Docker容器化，最终部署到云服务器。

## 项目目标

构建一个完整的ML部署系统：
- **模型训练**：使用TensorFlow训练图像分类模型
- **API服务**：Flask RESTful API
- **模型版本管理**：支持多版本模型切换
- **容器化部署**：Docker部署
- **性能监控**：请求日志和性能指标

## 第一步：环境准备（10分钟）

### 1. 创建项目

```bash
mkdir ml-deployment
cd ml-deployment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 安装依赖

创建 `requirements.txt`：

```txt
tensorflow==2.15.0
flask==3.0.0
flask-cors==4.0.0
pillow==10.1.0
numpy==1.24.3
gunicorn==21.2.0
python-dotenv==1.0.0
```

安装：

```bash
pip install -r requirements.txt
```

### 3. 项目结构

```
ml-deployment/
├── app/
│   ├── __init__.py
│   ├── main.py           # Flask应用
│   ├── model_loader.py   # 模型加载
│   ├── predictor.py      # 预测逻辑
│   └── utils.py          # 工具函数
├── models/               # 模型存储目录
├── training/             # 训练脚本
│   └── train.py
├── tests/                # 测试文件
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

## 第二步：训练模型（20分钟）

### 1. 创建训练脚本

创建 `training/train.py`：

```python
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import numpy as np
import os

def create_model(input_shape=(224, 224, 3), num_classes=10):
    """创建简单的CNN模型"""
    model = keras.Sequential([
        layers.Conv2D(32, (3, 3), activation='relu', input_shape=input_shape),
        layers.MaxPooling2D(2, 2),
        layers.Conv2D(64, (3, 3), activation='relu'),
        layers.MaxPooling2D(2, 2),
        layers.Conv2D(64, (3, 3), activation='relu'),
        layers.Flatten(),
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.5),
        layers.Dense(num_classes, activation='softmax')
    ])
    
    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model

def generate_dummy_data(num_samples=1000, img_shape=(224, 224, 3), num_classes=10):
    """生成虚拟数据用于演示"""
    X = np.random.random((num_samples, *img_shape))
    y = keras.utils.to_categorical(
        np.random.randint(num_classes, size=num_samples),
        num_classes
    )
    return X, y

def train_model():
    """训练模型"""
    print("开始训练模型...")
    
    # 创建模型
    model = create_model()
    model.summary()
    
    # 生成虚拟数据（实际项目中应使用真实数据）
    print("生成训练数据...")
    X_train, y_train = generate_dummy_data(1000)
    X_val, y_val = generate_dummy_data(200)
    
    # 训练模型
    print("训练中...")
    history = model.fit(
        X_train, y_train,
        batch_size=32,
        epochs=5,
        validation_data=(X_val, y_val),
        verbose=1
    )
    
    # 保存模型
    model_dir = '../models'
    os.makedirs(model_dir, exist_ok=True)
    
    model_version = 'v1.0.0'
    model_path = os.path.join(model_dir, model_version)
    
    model.save(model_path)
    print(f"模型已保存到: {model_path}")
    
    # 保存模型元数据
    import json
    metadata = {
        'version': model_version,
        'input_shape': [224, 224, 3],
        'num_classes': 10,
        'accuracy': float(history.history['val_accuracy'][-1]),
        'loss': float(history.history['val_loss'][-1])
    }
    
    metadata_path = os.path.join(model_path, 'metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("训练完成！")
    return model_path

if __name__ == '__main__':
    train_model()
```

### 2. 运行训练

```bash
cd training
python train.py
```

训练完成后，模型会保存在 `models/v1.0.0/` 目录。

## 第三步：创建Flask API（25分钟）

### 1. 模型加载器

创建 `app/model_loader.py`：

```python
import tensorflow as tf
import json
import os
from pathlib import Path

class ModelLoader:
    def __init__(self, models_dir='models'):
        self.models_dir = models_dir
        self.current_model = None
        self.current_version = None
        self.metadata = None
    
    def load_model(self, version='v1.0.0'):
        """加载指定版本的模型"""
        model_path = os.path.join(self.models_dir, version)
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型版本 {version} 不存在")
        
        try:
            self.current_model = tf.keras.models.load_model(model_path)
            self.current_version = version
            
            # 加载元数据
            metadata_path = os.path.join(model_path, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
            
            print(f"模型 {version} 加载成功")
            return True
        except Exception as e:
            print(f"加载模型失败: {e}")
            raise
    
    def get_model(self):
        """获取当前模型"""
        if self.current_model is None:
            raise RuntimeError("模型未加载")
        return self.current_model
    
    def get_metadata(self):
        """获取模型元数据"""
        return self.metadata
    
    def list_versions(self):
        """列出所有可用版本"""
        if not os.path.exists(self.models_dir):
            return []
        
        versions = []
        for item in os.listdir(self.models_dir):
            item_path = os.path.join(self.models_dir, item)
            if os.path.isdir(item_path):
                versions.append(item)
        
        return sorted(versions)

# 全局模型加载器实例
model_loader = ModelLoader()
```

### 2. 预测器

创建 `app/predictor.py`：

```python
import numpy as np
from PIL import Image
import tensorflow as tf
from app.model_loader import model_loader

def preprocess_image(image, target_size=(224, 224)):
    """预处理图像"""
    # 调整大小
    if isinstance(image, Image.Image):
        image = image.resize(target_size)
    else:
        image = Image.fromarray(image).resize(target_size)
    
    # 转换为数组
    img_array = np.array(image)
    
    # 归一化
    if img_array.max() > 1:
        img_array = img_array / 255.0
    
    # 添加批次维度
    img_array = np.expand_dims(img_array, axis=0)
    
    return img_array

def predict(image, top_k=5):
    """进行预测"""
    try:
        # 预处理图像
        processed_image = preprocess_image(image)
        
        # 获取模型
        model = model_loader.get_model()
        
        # 预测
        predictions = model.predict(processed_image, verbose=0)
        
        # 获取top-k结果
        top_indices = np.argsort(predictions[0])[-top_k:][::-1]
        top_probs = predictions[0][top_indices]
        
        # 构建结果
        results = []
        for idx, prob in zip(top_indices, top_probs):
            results.append({
                'class_id': int(idx),
                'class_name': f'Class_{idx}',  # 实际项目中应使用真实类别名
                'probability': float(prob)
            })
        
        return {
            'success': True,
            'predictions': results,
            'model_version': model_loader.current_version
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def get_model_info():
    """获取模型信息"""
    try:
        metadata = model_loader.get_metadata()
        return {
            'version': model_loader.current_version,
            'metadata': metadata,
            'available_versions': model_loader.list_versions()
        }
    except Exception as e:
        return {
            'error': str(e)
        }
```

### 3. 工具函数

创建 `app/utils.py`：

```python
import time
from functools import wraps

def timing_decorator(func):
    """计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    return wrapper

def validate_image_file(file):
    """验证图像文件"""
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
    if not file.filename:
        return False, "文件名为空"
    
    extension = file.filename.rsplit('.', 1)[1].lower()
    if extension not in allowed_extensions:
        return False, f"不支持的文件格式。支持: {', '.join(allowed_extensions)}"
    
    return True, None
```

### 4. Flask应用

创建 `app/main.py`：

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
import logging
from app.model_loader import model_loader
from app.predictor import predict, get_model_info
from app.utils import validate_image_file, timing_decorator

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 启动时加载模型
@app.before_first_request
def load_initial_model():
    try:
        versions = model_loader.list_versions()
        if versions:
            model_loader.load_model(versions[-1])  # 加载最新版本
            logger.info(f"初始模型加载成功: {model_loader.current_version}")
        else:
            logger.warning("未找到模型文件")
    except Exception as e:
        logger.error(f"模型加载失败: {e}")

# 健康检查
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'model_loaded': model_loader.current_model is not None
    })

# 模型信息
@app.route('/api/model/info', methods=['GET'])
def model_info():
    info = get_model_info()
    return jsonify(info)

# 切换模型版本
@app.route('/api/model/switch', methods=['POST'])
def switch_model():
    data = request.get_json()
    version = data.get('version')
    
    if not version:
        return jsonify({'error': '缺少version参数'}), 400
    
    try:
        model_loader.load_model(version)
        return jsonify({
            'success': True,
            'message': f'已切换到模型版本 {version}',
            'version': version
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# 预测接口
@app.route('/api/predict', methods=['POST'])
def predict_endpoint():
    # 检查文件
    if 'image' not in request.files:
        return jsonify({'error': '未提供图像文件'}), 400
    
    file = request.files['image']
    is_valid, error_msg = validate_image_file(file)
    
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    try:
        # 读取图像
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # 获取top_k参数
        top_k = request.form.get('top_k', 5, type=int)
        
        # 预测
        result, execution_time = timing_decorator(predict)(image, top_k)
        
        if result['success']:
            result['execution_time'] = execution_time
            logger.info(f"预测成功，耗时: {execution_time:.3f}秒")
            return jsonify(result)
        else:
            return jsonify(result), 500
    
    except Exception as e:
        logger.error(f"预测错误: {e}")
        return jsonify({'error': str(e)}), 500

# 批量预测
@app.route('/api/predict/batch', methods=['POST'])
def predict_batch():
    if 'images' not in request.files:
        return jsonify({'error': '未提供图像文件'}), 400
    
    files = request.files.getlist('images')
    results = []
    
    for file in files:
        is_valid, error_msg = validate_image_file(file)
        if not is_valid:
            results.append({'error': error_msg})
            continue
        
        try:
            image_bytes = file.read()
            image = Image.open(io.BytesIO(image_bytes))
            result, _ = timing_decorator(predict)(image)
            results.append(result)
        except Exception as e:
            results.append({'error': str(e)})
    
    return jsonify({'results': results})

if __name__ == '__main__':
    # 加载模型
    try:
        versions = model_loader.list_versions()
        if versions:
            model_loader.load_model(versions[-1])
    except Exception as e:
        print(f"警告: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
```

### 5. 应用初始化

创建 `app/__init__.py`：

```python
from app.main import app

__all__ = ['app']
```

## 第四步：创建测试脚本（10分钟）

创建 `tests/test_api.py`：

```python
import requests
import numpy as np
from PIL import Image
import io

BASE_URL = 'http://localhost:5000'

def create_test_image():
    """创建测试图像"""
    img_array = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    img = Image.fromarray(img_array)
    return img

def test_health():
    """测试健康检查"""
    response = requests.get(f'{BASE_URL}/health')
    print("健康检查:", response.json())

def test_model_info():
    """测试模型信息"""
    response = requests.get(f'{BASE_URL}/api/model/info')
    print("模型信息:", response.json())

def test_predict():
    """测试预测"""
    img = create_test_image()
    
    # 转换为字节
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # 发送请求
    files = {'image': ('test.png', img_bytes, 'image/png')}
    response = requests.post(f'{BASE_URL}/api/predict', files=files)
    print("预测结果:", response.json())

if __name__ == '__main__':
    test_health()
    test_model_info()
    test_predict()
```

## 第五步：Docker化部署（15分钟）

### 1. 创建Dockerfile

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY models/ ./models/

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app.main:app"]
```

### 2. 创建docker-compose.yml

```yaml
version: '3.8'

services:
  ml-api:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./models:/app/models
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 3. 构建和运行

```bash
# 构建镜像
docker build -t ml-api:latest .

# 或使用docker-compose
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 第六步：测试和监控（10分钟）

### 1. 测试API

```bash
# 健康检查
curl http://localhost:5000/health

# 模型信息
curl http://localhost:5000/api/model/info

# 预测（需要准备图像文件）
curl -X POST http://localhost:5000/api/predict \
  -F "image=@test_image.jpg" \
  -F "top_k=5"
```

### 2. 添加监控

在 `app/main.py` 中添加请求日志：

```python
@app.after_request
def after_request(response):
    logger.info(f"{request.method} {request.path} - {response.status_code}")
    return response
```

## 常见问题解决

### 问题1：模型加载失败

```python
# 检查模型路径
# 确保模型文件完整
# 检查TensorFlow版本兼容性
```

### 问题2：内存不足

```dockerfile
# 在Dockerfile中限制内存
# 使用模型量化
# 减少worker数量
```

### 问题3：预测速度慢

```python
# 使用GPU加速
# 模型优化（TensorRT）
# 批量处理
```

## 生产环境优化

### 1. 使用GPU

```dockerfile
FROM tensorflow/tensorflow:2.15.0-gpu
# ... 其他配置
```

### 2. 模型缓存

```python
# 使用Redis缓存预测结果
# 实现模型预热
```

### 3. 负载均衡

```yaml
# docker-compose.yml
services:
  nginx:
    image: nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

## 总结

通过本教程，你已经掌握了：
- ✅ 模型训练和保存
- ✅ Flask API开发
- ✅ 模型版本管理
- ✅ Docker容器化
- ✅ 生产部署流程

现在你可以将机器学习模型部署到生产环境了！

## 参考资源

- [TensorFlow文档](https://www.tensorflow.org/)
- [Flask文档](https://flask.palletsprojects.com/)
- [Docker文档](https://docs.docker.com/)
