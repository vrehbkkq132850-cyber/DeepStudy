#!/usr/bin/env python3
"""
测试知识图谱功能的完整流程
1. 登录获取JWT token
2. 发送聊天消息获取conversation_id
3. 使用conversation_id获取知识图谱数据
4. 验证整个流程是否正常工作
"""
import requests
import json
import time

# API配置
BASE_URL = "http://127.0.0.1:8000/api"

# 用户登录信息（请修改为你的实际账号）
USERNAME = "admin"
PASSWORD = "admin123"

print("测试知识图谱功能的完整流程...")
print("=" * 60)

# 1. 登录获取token
def login():
    print("\n1. 登录获取JWT token...")
    url = f"{BASE_URL}/auth/login"
    payload = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"登录响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            token = result.get("access_token")
            if token:
                print(f"登录成功！Token: {token[:20]}...")
                return token
            else:
                print("登录响应中没有token")
                return None
        else:
            print(f"登录失败: {response.text}")
            return None
    except Exception as e:
        print(f"登录请求失败: {str(e)}")
        return None

# 2. 发送聊天消息获取conversation_id
def send_message(token):
    print("\n2. 发送聊天消息获取conversation_id...")
    url = f"{BASE_URL}/chat"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": "什么是人工智能？",
        "parent_id": None,
        "ref_fragment_id": None,
        "session_id": f"test_session_{int(time.time())}"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"聊天响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 处理流式响应
            content = response.text
            lines = content.strip().split('\n')
            
            conversation_id = None
            for line in lines:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if data.get("type") == "meta" and data.get("conversation_id"):
                            conversation_id = data.get("conversation_id")
                            print(f"获取到conversation_id: {conversation_id}")
                        elif data.get("type") == "delta" and data.get("text"):
                            print(f"AI回答: {data.get('text')[:50]}...")
                    except json.JSONDecodeError:
                        pass
            
            return conversation_id
        else:
            print(f"发送消息失败: {response.text}")
            return None
    except Exception as e:
        print(f"发送消息请求失败: {str(e)}")
        return None

# 3. 获取知识图谱数据
def get_knowledge_graph(token, conversation_id):
    print("\n3. 获取知识图谱数据...")
    url = f"{BASE_URL}/mindmap/{conversation_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"知识图谱响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            nodes = result.get("nodes", [])
            edges = result.get("edges", [])
            
            print(f"知识图谱数据获取成功！")
            print(f"节点数量: {len(nodes)}")
            print(f"边数量: {len(edges)}")
            
            if nodes:
                print("\n节点信息:")
                for i, node in enumerate(nodes[:5]):  # 只显示前5个节点
                    label = node.get("data", {}).get("label", "未知")
                    print(f"  {i+1}. {label}")
                if len(nodes) > 5:
                    print(f"  ... 还有 {len(nodes) - 5} 个节点")
            
            if edges:
                print("\n边信息:")
                for i, edge in enumerate(edges[:5]):  # 只显示前5条边
                    source = edge.get("source", "未知")
                    target = edge.get("target", "未知")
                    print(f"  {i+1}. {source} -> {target}")
                if len(edges) > 5:
                    print(f"  ... 还有 {len(edges) - 5} 条边")
            
            return result
        else:
            print(f"获取知识图谱失败: {response.text}")
            return None
    except Exception as e:
        print(f"获取知识图谱请求失败: {str(e)}")
        return None

# 4. 测试完整流程
def test_full_flow():
    print("开始测试完整流程...")
    
    # 步骤1: 登录
    token = login()
    if not token:
        print("\n❌ 登录失败，测试终止")
        return False
    
    # 步骤2: 发送消息
    conversation_id = send_message(token)
    if not conversation_id:
        print("\n❌ 发送消息失败，测试终止")
        return False
    
    # 步骤3: 获取知识图谱
    graph_data = get_knowledge_graph(token, conversation_id)
    if not graph_data:
        print("\n❌ 获取知识图谱失败，测试终止")
        return False
    
    print("\n✅ 知识图谱功能测试成功！")
    print("=" * 60)
    print("测试结果总结:")
    print(f"- 登录状态: 成功")
    print(f"- 发送消息: 成功")
    print(f"- 获取知识图谱: 成功")
    print(f"- 节点数量: {len(graph_data.get('nodes', []))}")
    print(f"- 边数量: {len(graph_data.get('edges', []))}")
    print(f"- conversation_id: {conversation_id}")
    print("\n前端现在应该能够正常显示知识图谱了！")
    
    return True

if __name__ == "__main__":
    # 先检查后端服务器是否运行
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            print("后端服务器状态: 正常运行")
            test_full_flow()
        else:
            print("后端服务器状态: 异常")
            print(f"健康检查响应: {response.text}")
    except Exception as e:
        print("后端服务器未运行或无法访问:")
        print(f"错误: {str(e)}")
        print("请先启动后端服务器，然后再运行此测试脚本")
