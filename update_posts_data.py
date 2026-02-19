#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
from datetime import datetime
import glob

def extract_front_matter(content):
    """提取YAML front matter"""
    if not content.startswith('---'):
        return None
    
    end_index = content.find('---', 3)
    if end_index == -1:
        return None
    
    front_matter = content[3:end_index].strip()
    result = {}
    
    for line in front_matter.split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # 处理数组类型的值
            if value.startswith('[') and value.endswith(']'):
                # 移除方括号并分割
                value = value[1:-1].strip()
                if value:
                    # 分割并清理每个标签
                    items = [item.strip().strip('"\'') for item in value.split(',')]
                    result[key] = items
                else:
                    result[key] = []
            else:
                # 移除引号
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                result[key] = value
    
    return result

def extract_excerpt(content, max_length=200):
    """提取文章摘要"""
    # 移除front matter
    if content.startswith('---'):
        end_index = content.find('---', 3)
        if end_index != -1:
            content = content[end_index + 3:].strip()
    
    # 移除标题行（以#开头的行）
    lines = content.split('\n')
    content_lines = []
    for line in lines:
        if not line.strip().startswith('#'):
            content_lines.append(line)
    
    content = '\n'.join(content_lines)
    
    # 移除代码块
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    
    # 移除HTML标签
    content = re.sub(r'<[^>]+>', '', content)
    
    # 移除Markdown语法
    content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)  # 链接
    content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # 粗体
    content = re.sub(r'\*([^*]+)\*', r'\1', content)  # 斜体
    content = re.sub(r'`([^`]+)`', r'\1', content)  # 行内代码
    
    # 清理空白字符
    content = re.sub(r'\s+', ' ', content).strip()
    
    # 截取指定长度
    if len(content) > max_length:
        content = content[:max_length] + '...'
    
    return content

def generate_url(filename, date_str, categories):
    """生成文章URL"""
    # 从文件名提取日期和文章名
    # 格式: YYYY-MM-DD-文章名.md
    date_match = re.match(r'(\d{4})-(\d{2})-(\d{2})-(.+)', filename)
    if date_match:
        year, month, day, article_name = date_match.groups()
        # 移除.md扩展名
        article_name = article_name.replace('.md', '')
        
        # 使用文章中的分类，如果没有则根据文件名判断
        if categories and len(categories) > 0:
            category = categories[0]
        else:
            # 根据文件名判断分类
            category = "others"  # 默认分类
            
            if 'frontend' in article_name.lower() or 'react' in article_name.lower() or 'nextjs' in article_name.lower() or 'threejs' in article_name.lower() or 'openlayers' in article_name.lower():
                category = "frontend"
            elif 'backend' in article_name.lower() or 'docker' in article_name.lower() or 'pm2' in article_name.lower() or 'ubuntu' in article_name.lower():
                category = "backend"
            elif 'tools' in article_name.lower() or 'maven' in article_name.lower() or 'mysql' in article_name.lower():
                category = "tools"
        
        return f"/{category}/{year}/{month:0>2}/{day:0>2}/{article_name}.html"
    
    # 如果没有匹配到日期格式，返回原始文件名
    return f"/{filename.replace('.md', '.html')}"

def process_posts():
    """处理所有博客文章"""
    posts = []
    post_files = []
    
    # 分类文件夹（英文）
    category_folders = ['frontend', 'backend', 'tools', 'others']
    
    # 处理分类文件夹下的文章
    for folder in category_folders:
        folder_files = glob.glob(f'_posts/{folder}/*.md')
        post_files.extend(folder_files)
    
    # 处理web子目录下的文章
    web_post_files = glob.glob('_posts/web/*.md')
    post_files.extend(web_post_files)
    
    for file_path in post_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取front matter
            front_matter = extract_front_matter(content)
            if not front_matter:
                continue
            
            # 获取基本信息
            title = front_matter.get('title', '')
            date = front_matter.get('date', '')
            categories = front_matter.get('categories', ['others'])
            tags = front_matter.get('tags', [])
            
            # 如果categories是字符串，转换为列表
            if isinstance(categories, str):
                categories = [categories]
            
            # 如果tags是字符串，转换为列表
            if isinstance(tags, str):
                tags = [tags]
            
            # 分类已经是英文，无需映射
            
            # 提取摘要
            excerpt = extract_excerpt(content)
            
            # 生成URL
            filename = os.path.basename(file_path)
            url = generate_url(filename, date, categories)
            
            # 格式化日期
            if isinstance(date, str):
                try:
                    # 尝试解析日期
                    parsed_date = datetime.strptime(date, '%Y-%m-%d')
                    formatted_date = parsed_date.strftime('%Y-%m-%d')
                except:
                    formatted_date = date
            else:
                formatted_date = str(date)
            
            post_data = {
                "title": title,
                "excerpt": excerpt,
                "url": url,
                "date": formatted_date,
                "categories": categories,
                "tags": tags
            }
            
            posts.append(post_data)
            
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
    
    # 按日期排序（最新的在前）
    posts.sort(key=lambda x: x['date'], reverse=True)
    
    return posts

def main():
    """主函数"""
    print("开始扫描博客文章...")
    posts = process_posts()
    
    # 生成JSON数据
    data = {
        "posts": posts
    }
    
    # 写入文件
    with open('posts-data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"成功处理 {len(posts)} 篇文章")
    print("posts-data.json 已更新")

if __name__ == "__main__":
    main()
