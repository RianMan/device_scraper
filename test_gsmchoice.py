#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试GSMChoice爬虫
"""

from gsmchoice_scraper import GSMChoiceScraper
import json

def test_gsmchoice():
    """测试GSMChoice爬虫功能"""
    scraper = GSMChoiceScraper()
    
    # 测试用例
    test_cases = [
        ("Blackview", "BV4900 Pro"),
        ("OPPO", "CPH1931"),
        ("Samsung", "Galaxy S21"),
        ("Xiaomi", "Mi 11")
    ]
    
    print("🔍 测试GSMChoice爬虫")
    print("=" * 50)
    
    for manufacture, model in test_cases:
        print(f"\n测试: {manufacture} {model}")
        print("-" * 30)
        
        result = scraper.get_device_info(manufacture, model)
        
        if result['success']:
            data = result['data']
            print(f"✅ 成功找到设备")
            print(f"设备名称: {data['device_name']}")
            print(f"发布日期: {data['announced_date']}")
            print(f"价格: {data['price']}")
            print(f"规格数量: {len(data['specifications'])}")
            print(f"来源: {data['source_url']}")
        else:
            print(f"❌ 失败: {result['message']}")

if __name__ == "__main__":
    test_gsmchoice()