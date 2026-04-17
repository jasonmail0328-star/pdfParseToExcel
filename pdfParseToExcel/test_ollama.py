"""
测试 Ollama API
"""

import requests
import json
from config import OLLAMA_URL, MODEL

def test_ollama():
    """测试Ollama连接"""
    
    print("=" * 60)
    print("Ollama 连接测试")
    print("=" * 60)
    
    # 测试1: 检查服务
    print("\n1️⃣  测试 Ollama 服务连接...")
    try:
        response = requests.get(
            OLLAMA_URL.rsplit('/', 1)[0] + "/api/tags",
            timeout=5
        )
        
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ 服务连接成功")
            print(f"   已加载模型:")
            for model in models:
                print(f"   - {model['name']}")
        else:
            print(f"❌ 服务返回错误: {response.status_code}")
            return False
    
    except requests.ConnectionError:
        print(f"❌ 无法连接到 Ollama")
        print(f"   地址: {OLLAMA_URL}")
        print(f"   请启动: ollama serve")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    # 测试2: 检查模型
    print(f"\n2️⃣  检查模���: {MODEL}")
    model_names = [m['name'] for m in models]
    
    if MODEL in model_names:
        print(f"✅ 模型已加载")
    else:
        print(f"❌ 模型未加载: {MODEL}")
        print(f"   可用模型: {', '.join(model_names)}")
        print(f"   请运行: ollama pull {MODEL}")
        return False
    
    # 测试3: 测试API调用
    print(f"\n3️⃣  测试 API 调用...")
    
    test_prompt = "你好，请输出'成功'这个词。"
    
    payload = {
        "model": MODEL,
        "prompt": test_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 50,
        }
    }
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            output = result.get("response", "")
            
            print(f"✅ API 调用成功")
            print(f"   输入: {test_prompt}")
            print(f"   输出: {output}")
            return True
        else:
            print(f"❌ API 返回错误: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return False
    
    except requests.Timeout:
        print(f"❌ 请求超时 (30秒)")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    success = test_ollama()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！可以运行 python main.py")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 测试失败，请修复上述问题")
        print("=" * 60)