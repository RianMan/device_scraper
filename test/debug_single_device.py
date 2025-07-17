#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单设备调试脚本 - debug_single_device.py
专门测试单个设备的完整处理流程
"""

import logging
import sys
import os
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from google.google_search import GoogleSearcher
from gsmarena.gsmarena_scraper import GSMArenaScraper
from gsmchoice.gsmchoice_scraper import GSMChoiceScraper
from tools.device_name_normalizer import DeviceNameNormalizer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_google_search(model_code):
    """测试Google搜索"""
    logger.info("=" * 60)
    logger.info(f"🔍 测试Google搜索: {model_code}")
    logger.info("=" * 60)
    
    google_searcher = GoogleSearcher(request_delay=2)
    
    try:
        # 搜索GSMArena链接
        gsmarena_links = google_searcher.search_gsmarena_links(model_code)
        
        if gsmarena_links:
            logger.info(f"✅ Google找到 {len(gsmarena_links)} 个GSMArena链接:")
            for i, link in enumerate(gsmarena_links, 1):
                logger.info(f"  {i}. 标题: {link['title']}")
                logger.info(f"     URL: {link['url']}")
                logger.info(f"     排名: {link['rank']}")
                logger.info(f"     描述: {link['description'][:100]}...")
                logger.info("-" * 50)
            
            return gsmarena_links[0]['url']  # 返回第一个链接
        else:
            logger.warning(f"❌ Google未找到GSMArena链接")
            return None
            
    except Exception as e:
        logger.error(f"Google搜索异常: {str(e)}")
        return None
    finally:
        google_searcher.close()

def test_gsmarena_direct(gsmarena_url):
    """测试直接访问GSMArena URL"""
    logger.info("=" * 60)
    logger.info(f"📄 测试直接访问GSMArena: {gsmarena_url}")
    logger.info("=" * 60)
    
    gsmarena_scraper = GSMArenaScraper(request_delay=2)
    
    try:
        result = gsmarena_scraper.extract_device_info_from_url(gsmarena_url)
        
        if result and result['success']:
            data = result['data']
            logger.info(f"✅ 成功提取设备信息:")
            logger.info(f"   设备名称: {data['name']}")
            logger.info(f"   发布日期: {data['announced_date']}")
            logger.info(f"   价格: {data['price']}")
            logger.info(f"   型号: {data['model_code']}")
            logger.info(f"   规格数量: {len(data['specifications'])}")
            
            # 检查信息完整性
            has_name = data['name'] and data['name'] != 'Unknown'
            has_date = data['announced_date'] and data['announced_date'].strip()
            has_price = data['price'] and data['price'].strip() and data['price'] != 'Price not available'
            
            logger.info(f"   信息完整性检查:")
            logger.info(f"     有效名称: {has_name}")
            logger.info(f"     有发布日期: {has_date}")
            logger.info(f"     有价格: {has_price}")
            logger.info(f"     信息完整: {has_name and (has_date or has_price)}")
            
            return result
        else:
            logger.error(f"❌ 提取失败: {result}")
            return None
            
    except Exception as e:
        logger.error(f"GSMArena访问异常: {str(e)}")
        return None
    finally:
        gsmarena_scraper.close()

def test_gsmarena_search(model_code):
    """测试GSMArena搜索"""
    logger.info("=" * 60)
    logger.info(f"🔍 测试GSMArena搜索: {model_code}")
    logger.info("=" * 60)
    
    gsmarena_scraper = GSMArenaScraper(request_delay=2)
    
    try:
        result = gsmarena_scraper.search_device_by_model(model_code)
        
        if result and result['success']:
            data = result['data']
            logger.info(f"✅ GSMArena搜索成功:")
            logger.info(f"   设备名称: {data['name']}")
            logger.info(f"   发布日期: {data['announced_date']}")
            logger.info(f"   价格: {data['price']}")
            logger.info(f"   最接近匹配: {data.get('is_closest_match', False)}")
            return result
        else:
            logger.warning(f"❌ GSMArena搜索失败: {result}")
            return None
            
    except Exception as e:
        logger.error(f"GSMArena搜索异常: {str(e)}")
        return None
    finally:
        gsmarena_scraper.close()

def test_gsmchoice_search(model_code):
    """测试GSMChoice搜索"""
    logger.info("=" * 60)
    logger.info(f"🔍 测试GSMChoice搜索: {model_code}")
    logger.info("=" * 60)
    
    gsmchoice_scraper = GSMChoiceScraper(request_delay=2)
    
    try:
        # 推断品牌
        inferred_brand = DeviceNameNormalizer.infer_brand_from_model(model_code)
        logger.info(f"推断品牌: {inferred_brand}")
        
        # 标准化名称
        normalized_name = DeviceNameNormalizer.normalize_device_name(model_code, inferred_brand)
        logger.info(f"标准化名称: {model_code} -> {normalized_name}")
        
        result = gsmchoice_scraper.search_device_name(normalized_name, inferred_brand)
        
        if result['success']:
            logger.info(f"✅ GSMChoice搜索成功:")
            logger.info(f"   设备名称: {result['device_name']}")
            logger.info(f"   发布日期: {result.get('announced_date', 'N/A')}")
            logger.info(f"   来源: {result['source']}")
            return result
        else:
            logger.warning(f"❌ GSMChoice搜索失败: {result}")
            return None
            
    except Exception as e:
        logger.error(f"GSMChoice搜索异常: {str(e)}")
        return None
    finally:
        gsmchoice_scraper.close()

def debug_single_device(model_code):
    """完整调试单个设备"""
    logger.info("🚀 开始单设备完整调试")
    logger.info("=" * 80)
    logger.info(f"🔧 目标设备: {model_code}")
    logger.info("=" * 80)
    
    # 步骤1: 测试Google搜索
    gsmarena_url = test_google_search(model_code)
    
    # 步骤2: 如果Google找到链接，测试直接访问
    if gsmarena_url:
        gsmarena_result = test_gsmarena_direct(gsmarena_url)
        
        # 检查信息是否完整
        if gsmarena_result and gsmarena_result['success']:
            data = gsmarena_result['data']
            has_name = data['name'] and data['name'] != 'Unknown'
            has_date = data['announced_date'] and data['announced_date'].strip()
            has_price = data['price'] and data['price'].strip() and data['price'] != 'Price not available'
            
            if has_name and (has_date or has_price):
                logger.info("🎉 Google->GSMArena路径成功，信息完整")
                return
            else:
                logger.warning("⚠️ Google->GSMArena路径信息不完整，继续其他方案")
    
    # 步骤3: 测试GSMChoice搜索
    gsmchoice_result = test_gsmchoice_search(model_code)
    
    # 步骤4: 测试GSMArena直接搜索
    gsmarena_search_result = test_gsmarena_search(model_code)
    
    # 总结
    logger.info("\n" + "=" * 80)
    logger.info("📊 调试总结")
    logger.info("=" * 80)
    logger.info(f"Google搜索: {'✅' if gsmarena_url else '❌'}")
    logger.info(f"GSMArena直接访问: {'✅' if gsmarena_url and gsmarena_result else '❌'}")
    logger.info(f"GSMChoice搜索: {'✅' if gsmchoice_result and gsmchoice_result['success'] else '❌'}")
    logger.info(f"GSMArena搜索: {'✅' if gsmarena_search_result and gsmarena_search_result['success'] else '❌'}")

def main():
    """主函数"""
    if len(sys.argv) > 1:
        model_code = sys.argv[1]
    else:
        model_code = input("请输入要调试的设备型号: ").strip()
    
    if not model_code:
        logger.error("设备型号不能为空")
        return
    
    debug_single_device(model_code)

if __name__ == "__main__":
    main()