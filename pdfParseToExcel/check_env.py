"""
环境检查脚本
"""

import sys
import requests
from config import OLLAMA_URL, MODEL

def check_import(package_name, import_name=None):
    """检查包是否安装"""
    
    if import_name is None:
        import_name = package_name
    
    try:
        module = __import__(import_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"✅ {package_name:<25} - {version}")
        return True
    except ImportError:
        print(f"❌ {package_name:<25} - 未安装")
        return False

def check_ollama():
    """检查Ollama服务"""
    
    try:
        print(f"\n检查Ollama服务...")
        base_url = OLLAMA_URL.rsplit('/api/', 1)[0] + "/api"  # 获取基础 URL
        response = requests.get(f"{base_url}/tags", timeout=5)
        
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name") for m in models]
            
            print(f"✅ Ollama服务运行中")
            print(f"   地址: {OLLAMA_URL}")
            print(f"   已加载模型: {', '.join(model_names) if model_names else '无'}")
            
            if MODEL not in model_names:
                print(f"⚠️  警告: 未找到模型 '{MODEL}'")
                print(f"   请运行: ollama pull {MODEL}")
                return False
            
            return True
        else:
            print(f"❌ Ollama返回错误: {response.status_code}")
            return False
    
    except requests.ConnectionError:
        print(f"❌ 无法连接Ollama")
        print(f"   地址: {OLLAMA_URL}")
        print(f"   请确保Ollama服务正在运行")
        print(f"   运行: ollama serve")
        return False
    
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("PDF 提取系统 - 环境检查")
    print("=" * 70)
    print(f"Python版本: {sys.version}\n")
    
    packages = [
        ("numpy", "numpy"),
        ("Pillow", "PIL"),
        ("PyMuPDF", "fitz"),
        ("pandas", "pandas"),
        ("openpyxl", "openpyxl"),
        ("requests", "requests"),
        ("paddleocr", "paddleocr"),
        ("paddlepaddle", "paddle"),
        ("opencv-python", "cv2"),
    ]
    
    print("检查Python依赖:")
    results = []
    for package_name, import_name in packages:
        results.append(check_import(package_name, import_name))
    
    print("\n" + "-" * 70)
    
    ollama_ok = check_ollama()
    
    print("\n" + "=" * 70)
    
    if all(results) and ollama_ok:
        print("✅ 所有环境配置正确！可以运行: python main.py")
        sys.exit(0)
    else:
        print("❌ 请修复上述问题后重试")
        sys.exit(1)