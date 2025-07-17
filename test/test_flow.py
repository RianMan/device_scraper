#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本 - test/test_flow.py
测试完整的设备信息爬取流程
"""

import logging
import sys
import os
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from scraper.orchestrator import DeviceInfoOrchestrator
from tools.csv_tools import CSVTools
from tools.device_name_normalizer import DeviceNameNormalizer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_single_device():
    """测试单个设备处理"""
    logger.info("=" * 60)
    logger.info("🧪 测试单个设备处理")
    logger.info("=" * 60)
    
    orchestrator = DeviceInfoOrchestrator(request_delay=2)
    
    try:
        # 测试不同类型的设备
        test_devices = [
            "SM-J415G",      # Samsung设备
            "moto g(50) 5G", # Motorola设备  
            "ZTE 8050",      # ZTE设备
        ]
        
        for device in test_devices:
            logger.info(f"\n🔍 测试设备: {device}")
            logger.info("-" * 40)
            
            start_time = time.time()
            result = orchestrator.process_single_device(device)
            end_time = time.time()
            
            if result['success']:
                data = result['data']
                logger.info(f"✅ 成功处理: {device}")
                logger.info(f"   设备名称: {data['device_name']}")
                logger.info(f"   发布日期: {data['announced_date']}")
                logger.info(f"   价格: {data['price']}")
                logger.info(f"   方法: {data['method_used']}")
                logger.info(f"   耗时: {end_time - start_time:.1f} 秒")
            else:
                logger.error(f"❌ 处理失败: {device}")
                logger.error(f"   错误: {result['data']['error_message']}")
            
            time.sleep(1)  # 短暂休息
    
    finally:
        orchestrator.close()

def test_batch_processing():
    """测试批量处理"""
    logger.info("=" * 60)
    logger.info("🧪 测试批量处理")
    logger.info("=" * 60)
    
    # 创建测试CSV文件
    test_csv = "test_model_codes.csv"
    CSVTools.create_sample_model_codes_csv(test_csv, sample_count=3)
    
    orchestrator = DeviceInfoOrchestrator(request_delay=3)
    
    try:
        # 读取测试设备
        devices = CSVTools.read_model_codes_csv(test_csv)
        logger.info(f"📄 读取到 {len(devices)} 个测试设备")
        
        # 批量处理
        summary = orchestrator.process_device_list(devices)
        
        # 保存结果
        saved_files = orchestrator.save_results()
        logger.info(f"📁 结果已保存: {saved_files}")
        
        # 清理测试文件
        if os.path.exists(test_csv):
            os.remove(test_csv)
            logger.info(f"🗑️ 清理测试文件: {test_csv}")
    
    finally:
        orchestrator.close()

def test_google_search():
    """测试Google搜索功能"""
    logger.info("=" * 60)
    logger.info("🧪 测试Google搜索功能")
    logger.info("=" * 60)
    
    from google.google_search import GoogleSearcher
    
    searcher = GoogleSearcher(request_delay=2)
    
    try:
        test_models = ["SM-J415G", "ZTE 8050"]
        
        for model in test_models:
            logger.info(f"\n🔍 Google搜索测试: {model}")
            logger.info("-" * 40)
            
            # 搜索GSMArena链接
            gsmarena_links = searcher.search_gsmarena_links(model)
            
            if gsmarena_links:
                logger.info(f"✅ 找到 {len(gsmarena_links)} 个GSMArena链接")
                for i, link in enumerate(gsmarena_links[:2], 1):  # 只显示前2个
                    logger.info(f"   {i}. {link['title']}")
                    logger.info(f"      {link['url']}")
            else:
                logger.warning(f"❌ 未找到GSMArena链接: {model}")
            
            time.sleep(2)
    
    finally:
        searcher.close()

def test_gsmarena_scraping():
    """测试GSMArena爬取功能"""
    logger.info("=" * 60)
    logger.info("🧪 测试GSMArena爬取功能") 
    logger.info("=" * 60)
    
    from gsmarena.gsmarena_scraper import GSMArenaScraper
    
    scraper = GSMArenaScraper(request_delay=2)
    
    try:
        # 测试直接URL提取
        test_url = "https://www.gsmarena.com/samsung_galaxy_j4+-9270.php"
        logger.info(f"🔍 测试URL提取: {test_url}")
        
        result = scraper.extract_device_info_from_url(test_url)
        
        if result and result['success']:
            data = result['data']
            logger.info(f"✅ 成功提取设备信息:")
            logger.info(f"   设备名称: {data['name']}")
            logger.info(f"   发布日期: {data['announced_date']}")
            logger.info(f"   价格: {data['price']}")
            logger.info(f"   规格数量: {len(data['specifications'])}")
        else:
            logger.error(f"❌ 提取失败: {result}")
        
        # 测试搜索功能
        test_model = "SM-J415G"
        logger.info(f"\n🔍 测试型号搜索: {test_model}")
        
        search_result = scraper.search_device_by_model(test_model)
        
        if search_result and search_result['success']:
            logger.info(f"✅ 搜索成功:")
            logger.info(f"   设备名称: {search_result['data']['name']}")
        else:
            logger.warning(f"❌ 搜索失败: {test_model}")
    
    finally:
        scraper.close()

def test_gsmchoice_search():
    """测试GSMChoice搜索功能"""
    logger.info("=" * 60)
    logger.info("🧪 测试GSMChoice搜索功能")
    logger.info("=" * 60)
    
    from gsmchoice.gsmchoice_scraper import GSMChoiceScraper
    
    scraper = GSMChoiceScraper(request_delay=2)
    
    try:
        test_models = [
            ("SM-J415G", "Samsung"),
            ("moto g(50) 5G", "Motorola"),
            ("ZTE 8050", "ZTE")
        ]
        
        for model, brand in test_models:
            logger.info(f"\n🔍 GSMChoice搜索测试: {model} ({brand})")
            logger.info("-" * 40)
            
            result = scraper.search_device_name(model, brand)
            
            if result['success']:
                logger.info(f"✅ 找到设备名称: {result['device_name']}")
                logger.info(f"   来源: {result['source']}")
            else:
                logger.warning(f"❌ 未找到设备: {model}")
            
            time.sleep(2)
    
    finally:
        scraper.close()

def test_device_name_normalization():
    """测试设备名称标准化"""
    logger.info("=" * 60)
    logger.info("🧪 测试设备名称标准化")
    logger.info("=" * 60)
    
    test_names = [
        "moto g(50) 5G",
        "moto g(9) plus", 
        "moto e(6) plus",
        "moto g stylus",
        "SM-J415G",
        "ZTE 8050"
    ]
    
    for name in test_names:
        normalized = DeviceNameNormalizer.normalize_device_name(name)
        brand = DeviceNameNormalizer.infer_brand_from_model(name)
        
        logger.info(f"原始: {name}")
        logger.info(f"标准化: {normalized}")
        logger.info(f"推断品牌: {brand}")
        logger.info("-" * 30)

def test_csv_operations():
    """测试CSV操作"""
    logger.info("=" * 60)
    logger.info("🧪 测试CSV操作")
    logger.info("=" * 60)
    
    # 创建测试数据
    test_results = [
        {
            'original_model_code': 'TEST001',
            'device_name': 'Test Device 1',
            'announced_date': '2023, January',
            'price': '€200.00',
            'inferred_brand': 'TestBrand'
        },
        {
            'original_model_code': 'TEST002', 
            'device_name': 'Test Device 2',
            'announced_date': '2023, February',
            'price': '€300.00',
            'inferred_brand': 'TestBrand'
        }
    ]
    
    test_failed = [
        {
            'model_code': 'FAIL001',
            'error_message': 'Test failure',
            'failed_time': '2025-07-16 12:00:00'
        }
    ]
    
    # 测试保存
    success_file = CSVTools.save_device_results(test_results, "test_success")
    failed_file = CSVTools.save_failed_devices(test_failed, "test_failed")
    
    logger.info(f"✅ 测试文件已创建:")
    logger.info(f"   成功文件: {success_file}")
    logger.info(f"   失败文件: {failed_file}")
    
    # 验证文件
    if success_file:
        valid, message = CSVTools.validate_csv_structure(success_file, ['original_model_code', 'device_name'])
        logger.info(f"文件验证: {valid} - {message}")

def run_comprehensive_test():
    """运行完整测试套件"""
    logger.info("🚀 开始运行完整测试套件")
    logger.info("=" * 80)
    
    tests = [
        ("设备名称标准化", test_device_name_normalization),
        ("CSV操作", test_csv_operations),
        ("GSMChoice搜索", test_gsmchoice_search),
        ("GSMArena爬取", test_gsmarena_scraping),
        ("Google搜索", test_google_search),
        ("单设备处理", test_single_device),
        ("批量处理", test_batch_processing),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_function in tests:
        try:
            logger.info(f"\n🧪 运行测试: {test_name}")
            start_time = time.time()
            
            test_function()
            
            end_time = time.time()
            logger.info(f"✅ 测试通过: {test_name} (耗时: {end_time - start_time:.1f}秒)")
            passed_tests += 1
            
        except Exception as e:
            logger.error(f"❌ 测试失败: {test_name}")
            logger.error(f"   错误: {str(e)}")
            import traceback
            logger.error(f"   详情: {traceback.format_exc()}")
        
        # 测试间暂停
        time.sleep(1)
    
    # 输出测试总结
    logger.info("\n" + "=" * 80)
    logger.info("🎯 测试总结")
    logger.info("=" * 80)
    logger.info(f"📊 总测试数: {total_tests}")
    logger.info(f"✅ 通过: {passed_tests}")
    logger.info(f"❌ 失败: {total_tests - passed_tests}")
    logger.info(f"📈 通过率: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        logger.info("🎉 所有测试都通过了！")
    else:
        logger.warning("⚠️ 部分测试失败，请检查错误信息")

def run_quick_test():
    """运行快速测试（只测试核心功能）"""
    logger.info("⚡ 运行快速测试")
    logger.info("=" * 60)
    
    quick_tests = [
        ("设备名称标准化", test_device_name_normalization),
        ("CSV操作", test_csv_operations),
        ("单设备处理", test_single_device),
    ]
    
    for test_name, test_function in quick_tests:
        try:
            logger.info(f"\n🧪 {test_name}")
            test_function()
            logger.info(f"✅ {test_name} 通过")
        except Exception as e:
            logger.error(f"❌ {test_name} 失败: {str(e)}")
        
        time.sleep(0.5)

def main():
    """主函数"""
    print("🧪 设备信息爬取系统测试")
    print("=" * 50)
    print("1. 运行完整测试套件 (推荐)")
    print("2. 运行快速测试")
    print("3. 测试单个设备处理")
    print("4. 测试批量处理")
    print("5. 测试设备名称标准化")
    print("0. 退出")
    
    while True:
        choice = input("\n请选择测试选项 (0-5): ").strip()
        
        if choice == '0':
            print("👋 测试结束")
            break
        elif choice == '1':
            run_comprehensive_test()
        elif choice == '2':
            run_quick_test()
        elif choice == '3':
            test_single_device()
        elif choice == '4':
            test_batch_processing()
        elif choice == '5':
            test_device_name_normalization()
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    main()