#!/usr/bin/env python3
"""
注册一个测试用户
"""
import requests
import json

# API配置
BASE_URL = "http://127.0.0.1:8000/api"

# 用户注册信息
USERNAME = "admin"
PASSWORD = "admin123"
EMAIL = "admin@example.com"

print("注册测试用户...")
print("=" * 40)

# 注册用户
def register_user():
    url = f"{BASE_URL}/auth/register"
    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "email": EMAIL
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"注册响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            token = result.get("access_token")
            if token:
                print("✅ 注册成功！")
                print(f"用户名: {USERNAME}")
                print(f"密码: {PASSWORD}")
                print(f"邮箱: {EMAIL}")
                print(f"Token: {token[:20]}...")
                return True
            else:
                print("注册响应中没有token")
                return False
        elif response.status_code == 400:
            result = response.json()
            print(f"⚠️  注册失败: {result.get('detail')}")
            print("用户可能已经存在，尝试直接登录")
            return True  # 继续测试，可能用户已经存在
        else:
            print(f"注册失败: {response.text}")
            return False
    except Exception as e:
        print(f"注册请求失败: {str(e)}")
        return False

if __name__ == "__main__":
    # 先检查后端服务器是否运行
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            print("后端服务器状态: 正常运行")
            register_user()
        else:
            print("后端服务器状态: 异常")
            print(f"健康检查响应: {response.text}")
    except Exception as e:
        print("后端服务器未运行或无法访问:")
        print(f"错误: {str(e)}")
        print("请先启动后端服务器，然后再运行此脚本")
