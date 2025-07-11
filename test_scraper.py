#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试爬虫类初始化
"""

try:
    from device_scraper_core import DeviceInfoScraper
    print("✅ 成功导入 DeviceInfoScraper 类")
    
    # 测试初始化
    scraper = DeviceInfoScraper(max_workers=5, timeout=30)
    print("✅ 成功创建爬虫实例")
    print(f"  - 最大线程数: {scraper.max_workers}")
    print(f"  - 超时时间: {scraper.timeout}")
    print(f"  - WebDriver池大小: {scraper.driver_pool.qsize()}")
    
    # 关闭爬虫
    scraper.close()
    print("✅ 成功关闭爬虫")
    
except Exception as e:
    print(f"❌ 错误: {str(e)}")
    import traceback
    traceback.print_exc()