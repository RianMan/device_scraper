#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强的GSMChoice爬虫
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_enhanced_gsmchoice():
    """测试增强的GSMChoice爬虫"""
    
    try:
        # 导入增强的爬虫类
        from enhanced_gsmchoice_scraper import EnhancedGSMChoiceScraper
        
        # 创建爬虫实例（启用Selenium）
        scraper = EnhancedGSMChoiceScraper(request_delay=3, use_selenium=True)
        
        print("🔍 测试增强的GSMChoice爬虫")
        print("=" * 60)
        
        # 测试用例
        test_cases = [
            ("Blackview", "BV4900 Pro"),
            ("OPPO", "A57"),
            ("Samsung", "Galaxy A24"),
            ("Xiaomi", "Redmi Note 13")
        ]
        
        for i, (manufacture, model) in enumerate(test_cases, 1):
            print(f"\n📱 测试 {i}/{len(test_cases)}: {manufacture} {model}")
            print("-" * 50)
            
            try:
                result = scraper.get_device_info(manufacture, model)
                
                if result['success']:
                    data = result['data']
                    print(f"✅ 成功找到设备")
                    print(f"   设备名称: {data['device_name']}")
                    print(f"   品牌: {data['brand']}")
                    print(f"   发布日期: {data['announced_date']}")
                    print(f"   价格: {data['price']}")
                    print(f"   规格数量: {len(data['specifications'])}")
                    print(f"   来源: {data['source_url']}")
                    
                    # 显示一些关键规格
                    specs = data['specifications']
                    important_keys = ['Display', 'Processor', 'Standard battery', 'Operating system']
                    for key in important_keys:
                        if key in specs:
                            print(f"   {key}: {specs[key]}")
                else:
                    print(f"❌ 失败: {result['message']}")
                    
            except Exception as e:
                print(f"❌ 异常: {str(e)}")
        
        print(f"\n🔚 测试完成")
        
    except ImportError as e:
        print(f"❌ 导入错误: {str(e)}")
        print("请确保增强的爬虫文件存在")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
    finally:
        try:
            scraper.close()
            print("🔒 WebDriver已关闭")
        except:
            pass

if __name__ == "__main__":
    test_enhanced_gsmchoice()