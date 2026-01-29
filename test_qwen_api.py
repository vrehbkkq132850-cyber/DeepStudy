#!/usr/bin/env python3
"""
测试千问API连接脚本
"""
import requests
import json

# 从.env文件读取配置
with open('backend/.env', 'r', encoding='utf-8') as f:
    config = {}
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            config[key] = value

# 获取API配置
api_key = config.get('MODELSCOPE_API_KEY')
api_base = config.get('MODELSCOPE_API_BASE', 'https://api-inference.modelscope.cn/v1')
model_name = config.get('MODEL_NAME', 'Qwen/Qwen3-32B')

print(f"测试千问API连接...")
print(f"API Key: {api_key[:10]}...")
print(f"API Base: {api_base}")
print(f"Model: {model_name}")
print()

# 测试API连接
def test_qwen_api():
    # 使用更简单的模型和API端点
    simple_model = "Qwen/Qwen2.5-7B-Instruct"
    url = f"{api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": simple_model,
        "messages": [
            {
                "role": "user",
                "content": "你好"
            }
        ],
        "max_tokens": 50
    }
    
    try:
        print(f"使用模型: {simple_model}")
        print(f"请求URL: {url}")
        print("发送测试请求...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"响应状态码: {response.status_code}")
        print()
        
        print("完整响应内容:")
        print(response.text)
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("API响应成功!")
            print("\n助手回答:")
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print(content)
                return True
            else:
                print("响应格式不正确:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return False
        else:
            print("API响应失败:")
            return False
    except Exception as e:
        print(f"连接错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_qwen_api()
    if success:
        print("\n✅ 千问API测试成功!")
    else:
        print("\n❌ 千问API测试失败，请检查配置!")
