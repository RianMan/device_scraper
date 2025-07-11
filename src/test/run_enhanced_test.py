#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行增强GSMChoice爬虫测试的脚本
"""

import os
import sys

def main():
    print("🚀 启动增强版GSMChoice爬虫测试")
    print("=" * 60)
    
    # 检查当前目录
    current_dir = os.getcwd()
    print(f"📁 当前目录: {current_dir}")
    
    # 检查需要的文件
    required_files = [
        'standalone_enhanced_scraper.py',  # 如果你保存了独立版本
        'enhanced_gsmchoice_scraper.py'    # 或者这个文件名
    ]
    
    script_file = None
    for file in required_files:
        if os.path.exists(file):
            script_file = file
            print(f"✅ 找到脚本文件: {file}")
            break
    
    if not script_file:
        print("❌ 未找到增强版爬虫脚本文件")
        print("\n请执行以下步骤:")
        print("1. 将我提供的独立版代码保存为 'standalone_enhanced_scraper.py'")
        print("2. 确保文件在当前目录中")
        print("3. 重新运行此脚本")
        return
    
    # 检查依赖
    print("\n🔍 检查依赖...")
    missing_deps = []
    
    try:
        import requests
        print("  ✅ requests")
    except ImportError:
        missing_deps.append("requests")
        print("  ❌ requests")
    
    try:
        from bs4 import BeautifulSoup
        print("  ✅ beautifulsoup4")
    except ImportError:
        missing_deps.append("beautifulsoup4")
        print("  ❌ beautifulsoup4")
    
    try:
        from selenium import webdriver
        print("  ✅ selenium (可选)")
    except ImportError:
        print("  ⚠️ selenium (不可用，将使用基础模式)")
    
    if missing_deps:
        print(f"\n❌ 缺少必要依赖: {', '.join(missing_deps)}")
        print(f"请运行: pip install {' '.join(missing_deps)}")
        return
    
    # 执行测试
    print(f"\n🔬 执行测试脚本: {script_file}")
    print("=" * 60)
    
    try:
        # 动态导入并执行
        import importlib.util
        spec = importlib.util.spec_from_file_location("enhanced_scraper", script_file)
        enhanced_scraper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(enhanced_scraper)
        
        # 如果模块有test函数，直接调用
        if hasattr(enhanced_scraper, 'test_enhanced_scraper'):
            enhanced_scraper.test_enhanced_scraper()
        else:
            print("⚠️ 脚本中未找到test_enhanced_scraper函数")
            
    except Exception as e:
        print(f"❌ 执行测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()