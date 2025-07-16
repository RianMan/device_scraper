#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GSMArena解密测试脚本
测试AES解密功能
"""

import requests
import re
import base64
from bs4 import BeautifulSoup

def install_crypto_library():
    """检查并安装加密库"""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        print("✅ cryptography库已安装")
        return True
    except ImportError:
        print("❌ cryptography库未安装")
        print("💡 请运行: pip install cryptography")
        return False

def decrypt_aes_cbc(encrypted_data, key, iv):
    """AES CBC解密"""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        
        # Base64解码
        encrypted_bytes = base64.b64decode(encrypted_data)
        key_bytes = base64.b64decode(key)
        iv_bytes = base64.b64decode(iv)
        
        print(f"🔑 密钥长度: {len(key_bytes)} 字节")
        print(f"🔑 IV长度: {len(iv_bytes)} 字节")
        print(f"🔑 加密数据长度: {len(encrypted_bytes)} 字节")
        
        # AES CBC解密
        cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_bytes = decryptor.update(encrypted_bytes) + decryptor.finalize()
        
        # 移除PKCS7填充
        padding_length = decrypted_bytes[-1]
        decrypted_text = decrypted_bytes[:-padding_length].decode('utf-8')
        
        print(f"✅ 解密成功，内容长度: {len(decrypted_text)} 字符")
        return decrypted_text
        
    except Exception as e:
        print(f"❌ 解密失败: {str(e)}")
        return None

def extract_crypto_data(html_content):
    """从HTML中提取加密数据"""
    try:
        # 查找KEY, IV, DATA
        key_match = re.search(r'const KEY\s*=\s*"([^"]+)"', html_content)
        iv_match = re.search(r'const IV\s*=\s*"([^"]+)"', html_content)
        data_match = re.search(r'const DATA\s*=\s*"([^"]+)"', html_content)
        
        if key_match and iv_match and data_match:
            print("✅ 找到加密数据")
            return {
                'key': key_match.group(1),
                'iv': iv_match.group(1),
                'data': data_match.group(1)
            }
        else:
            print("❌ 未找到加密数据")
            return None
            
    except Exception as e:
        print(f"❌ 提取加密数据失败: {str(e)}")
        return None

def test_gsmarena_decrypt():
    """测试GSMArena解密"""
    print("🧪 GSMArena解密测试")
    print("=" * 50)
    
    # 检查加密库
    if not install_crypto_library():
        return
    
    # 测试URL
    search_url = "https://www.gsmarena.com/res.php3?sSearch=SM-A525M"
    
    # 设置请求头
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cache-control': 'no-cache',
        'connection': 'keep-alive',
        'pragma': 'no-cache',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
    }
    
    try:
        print(f"🔍 请求: {search_url}")
        
        # 发送请求
        response = requests.get(search_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            print(f"✅ 页面加载成功，长度: {len(response.text)}")
            
            # 保存原始HTML
            with open('gsmarena_encrypted.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("💾 原始HTML已保存: gsmarena_encrypted.html")
            
            # 提取加密数据
            crypto_data = extract_crypto_data(response.text)
            
            if crypto_data:
                print(f"🔑 KEY: {crypto_data['key']}")
                print(f"🔑 IV: {crypto_data['iv']}")
                print(f"🔑 DATA前50字符: {crypto_data['data'][:50]}...")
                
                # 解密
                decrypted_html = decrypt_aes_cbc(
                    crypto_data['data'],
                    crypto_data['key'],
                    crypto_data['iv']
                )
                
                if decrypted_html:
                    # 保存解密结果
                    with open('gsmarena_decrypted.html', 'w', encoding='utf-8') as f:
                        f.write(decrypted_html)
                    print("💾 解密HTML已保存: gsmarena_decrypted.html")
                    
                    # 分析解密内容
                    soup = BeautifulSoup(decrypted_html, 'html.parser')
                    
                    # 查找链接
                    all_links = soup.find_all('a', href=True)
                    print(f"🔗 解密内容中找到 {len(all_links)} 个链接")
                    
                    # 查找设备链接
                    device_links = []
                    for link in all_links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        if '.php' in href and not any(skip in href for skip in ['res.php3', 'rss', 'news']):
                            device_links.append((href, text))
                    
                    print(f"📱 可能的设备链接:")
                    for i, (href, text) in enumerate(device_links[:5], 1):
                        print(f"  {i}. {href} ({text})")
                    
                    # 查找Samsung相关链接
                    samsung_links = [link for link in device_links if 'samsung' in link[0].lower() or 'galaxy' in link[1].lower()]
                    if samsung_links:
                        print(f"🎯 Samsung相关链接:")
                        for href, text in samsung_links[:3]:
                            print(f"  • {href} ({text})")
                    
                    print("✅ 解密测试完成!")
                    
            else:
                print("❌ 未找到加密数据")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

if __name__ == "__main__":
    test_gsmarena_decrypt()