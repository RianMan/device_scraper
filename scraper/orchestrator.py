#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主调度器 - scraper/orchestrator.py
统筹调用各个爬虫模块的核心逻辑
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import random
import pandas as pd
# 导入各个模块
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.google_search import GoogleSearcher
from gsmarena.gsmarena_scraper import GSMArenaScraper
from gsmchoice.gsmchoice_scraper import GSMChoiceScraper
from tools.csv_tools import CSVTools
from tools.device_name_normalizer import DeviceNameNormalizer

logger = logging.getLogger(__name__)

class DeviceInfoOrchestrator:
    """设备信息爬取调度器"""
    
    def __init__(self, request_delay=3):
        """初始化调度器"""
        self.request_delay = request_delay
        
        # 初始化各个爬虫模块
        self.google_searcher = GoogleSearcher(request_delay=request_delay)
        self.gsmarena_scraper = GSMArenaScraper(request_delay=request_delay)
        self.gsmchoice_scraper = GSMChoiceScraper(request_delay=request_delay)
        
        # 统计信息
        self.stats = {
            'total_devices': 0,
            'successful_devices': 0,
            'failed_devices': 0,
            'google_searches': 0,
            'gsmarena_direct_hits': 0,
            'gsmchoice_fallbacks': 0,
            'processing_start_time': None,
            'processing_end_time': None
        }
        
        # 结果存储
        self.successful_results = []
        self.failed_devices = []
        
        logger.info("🚀 设备信息爬取调度器初始化完成")
    
    def process_single_device(self, model_code: str) -> Dict[str, Any]:
        """
        处理单个设备的完整流程
        """
        logger.info(f"🔄 开始处理设备: {model_code}")
        
        # 推断品牌
        inferred_brand = DeviceNameNormalizer.infer_brand_from_model(model_code)
        
        # 特殊处理：Moto设备直接跳转到GSMArena搜索
        if model_code.lower().startswith('moto'):
            logger.info(f"🔄 Moto设备直接使用GSMArena搜索: {model_code}")
            normalized_model = DeviceNameNormalizer.normalize_device_name(model_code, inferred_brand)
            result = self.gsmarena_scraper.search_device_by_name(normalized_model)
            if result and result['success']:
                logger.info(f"✅ Moto设备GSMArena搜索成功: {model_code}")
                return self._format_success_result(result, model_code, inferred_brand, 'gsmarena_moto_direct')
        
        # 第一步：Google搜索GSMArena链接
        result = self._try_google_gsmarena_search(model_code)
        if result and result['success']:
            logger.info(f"✅ Google->GSMArena 路径成功: {model_code}")
            return self._format_success_result(result, model_code, inferred_brand, 'google_gsmarena')
        
        # 第二步：如果Google搜索失败，尝试GSMChoice获取设备名称
        logger.info(f"🔄 Google搜索失败，尝试GSMChoice获取设备名称: {model_code}")
        self.stats['gsmchoice_fallbacks'] += 1
        
        # 标准化模型名称再搜索
        normalized_model = DeviceNameNormalizer.normalize_device_name(model_code, inferred_brand)
        gsmchoice_result = self.gsmchoice_scraper.search_device_name(normalized_model, inferred_brand)
        
        if gsmchoice_result['success']:
            device_name = gsmchoice_result['device_name']
            gsmchoice_announced_date = gsmchoice_result.get('announced_date', '')
            logger.info(f"✅ GSMChoice找到设备名称: {device_name}")
            
            # 用设备名称在GSMArena搜索
            gsmarena_result = self.gsmarena_scraper.search_device_by_name(device_name)
            if gsmarena_result and gsmarena_result['success']:
                logger.info(f"✅ GSMChoice->GSMArena 路径成功: {model_code}")
                
                # 如果GSMArena没有发布日期，使用GSMChoice的日期
                if not gsmarena_result['data'].get('announced_date') and gsmchoice_announced_date:
                    logger.info(f"📅 使用GSMChoice的发布日期: {gsmchoice_announced_date}")
                    gsmarena_result['data']['announced_date'] = gsmchoice_announced_date
                    gsmarena_result['data']['announced_date_source'] = 'gsmchoice'
                
                return self._format_success_result(gsmarena_result, model_code, inferred_brand, 'gsmchoice_gsmarena')
        
        # 第三步：直接在GSMArena搜索原型号（最后尝试）
        logger.info(f"🔄 尝试直接GSMArena搜索: {model_code}")
        direct_result = self.gsmarena_scraper.search_device_by_model(model_code)
        if direct_result and direct_result['success']:
            logger.info(f"✅ 直接GSMArena搜索成功: {model_code}")
            return self._format_success_result(direct_result, model_code, inferred_brand, 'gsmarena_direct')
        
        # 所有方法都失败
        logger.warning(f"❌ 所有搜索方法都失败: {model_code}")
        return self._format_failed_result(model_code, "所有搜索方法都失败")
    
    def _try_google_gsmarena_search(self, model_code: str) -> Optional[Dict[str, Any]]:
        """尝试通过Google搜索找到GSMArena链接"""
        try:
            self.stats['google_searches'] += 1
            
            # Google搜索GSMArena链接
            gsmarena_links = self.google_searcher.search_gsmarena_links(model_code)
            
            if not gsmarena_links:
                logger.info(f"Google未找到GSMArena链接: {model_code}")
                return None
            
            # 尝试提取第一个链接的信息
            best_link = gsmarena_links[0]  # 取排名最高的链接
            gsmarena_url = best_link['url']
            
            logger.info(f"📄 从Google找到GSMArena链接: {gsmarena_url}")
            
            # 直接从URL提取设备信息
            result = self.gsmarena_scraper.extract_device_info_from_url(gsmarena_url)
            
            if result and result['success']:
                # 检查关键信息是否完整
                data = result['data']
                if self._is_device_info_complete(data):
                    self.stats['gsmarena_direct_hits'] += 1
                    return result
                else:
                    logger.warning(f"GSMArena信息不完整: {model_code}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Google->GSMArena搜索失败: {str(e)}")
            return None
    
    def _is_device_info_complete(self, device_data: Dict[str, Any]) -> bool:
        """检查设备信息是否完整"""
        # 检查关键字段
        required_fields = ['name']
        for field in required_fields:
            if not device_data.get(field) or device_data[field] == 'Unknown':
                return False
        
        # 至少有发布日期或价格之一
        has_date = device_data.get('announced_date') and device_data['announced_date'].strip()
        has_price = device_data.get('price') and device_data['price'].strip() and device_data['price'] != 'Price not available'
        
        return has_date or has_price
    
    def _format_success_result(self, scrape_result: Dict[str, Any], original_model: str, 
                             inferred_brand: str, method: str) -> Dict[str, Any]:
        """格式化成功结果"""
        data = scrape_result['data']
        
        return {
            'success': True,
            'method': method,
            'data': {
                'original_model_code': original_model,
                'device_name': data.get('name', ''),
                'announced_date': data.get('announced_date', ''),
                'announced_date_source': data.get('announced_date_source', 'gsmarena'),
                'price': data.get('price', ''),
                'is_closest_match': data.get('is_closest_match', False),
                'inferred_brand': inferred_brand,
                'source_url': data.get('source_url', ''),
                'processed_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'method_used': method,
            }
        }
    
    def _format_failed_result(self, model_code: str, error_message: str) -> Dict[str, Any]:
        """格式化失败结果"""
        return {
            'success': False,
            'data': {
                'model_code': model_code,
                'error_message': error_message,
                'failed_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }
    
    def process_device_list(self, devices: List[Dict[str, str]], max_devices: Optional[int] = None) -> Dict[str, Any]:
        """处理设备列表"""
        if max_devices:
            devices = devices[:max_devices]
        
        self.stats['total_devices'] = len(devices)
        self.stats['processing_start_time'] = datetime.now()
        
        logger.info(f"🚀 开始批量处理 {len(devices)} 个设备")
        
        for i, device in enumerate(devices, 1):
            model_code = device['model_code']
            
            logger.info(f"📱 进度: {i}/{len(devices)} ({i/len(devices)*100:.1f}%)")
            
            # 处理单个设备
            result = self.process_single_device(model_code)
            
            if result['success']:
                self.successful_results.append(result['data'])
                self.stats['successful_devices'] += 1
                logger.info(f"✅ 成功: {model_code} - {result['data']['device_name']}")
                self._save_single_success_result(result['data'])
            else:
                self.failed_devices.append(result['data'])
                self.stats['failed_devices'] += 1
                logger.warning(f"❌ 失败: {model_code} - {result['data']['error_message']}")
                self._save_single_failed_result(result['data'])
            # 添加随机延迟
            if i < len(devices):
                self._random_delay()
        
        self.stats['processing_end_time'] = datetime.now()
        
        # 计算处理时间和成功率
        processing_time = (self.stats['processing_end_time'] - self.stats['processing_start_time']).total_seconds()
        self.stats['processing_time_seconds'] = processing_time
        self.stats['success_rate'] = (self.stats['successful_devices'] / self.stats['total_devices'] * 100) if self.stats['total_devices'] > 0 else 0
        
        return self._generate_summary()
    
    def _random_delay(self):
        """添加随机延迟"""
        delay = random.uniform(self.request_delay * 0.8, self.request_delay * 1.5)
        logger.info(f"⏳ 等待 {delay:.1f} 秒...")
        time.sleep(delay)
    
    def _generate_summary(self) -> Dict[str, Any]:
        """生成处理摘要"""
        summary = {
            'statistics': self.stats.copy(),
            'successful_results': self.successful_results,
            'failed_devices': self.failed_devices
        }
        
        # 输出统计信息
        logger.info(f"\n🎯 处理完成!")
        logger.info(f"📊 总数: {self.stats['total_devices']}")
        logger.info(f"✅ 成功: {self.stats['successful_devices']}")
        logger.info(f"❌ 失败: {self.stats['failed_devices']}")
        logger.info(f"📈 成功率: {self.stats['success_rate']:.1f}%")
        logger.info(f"⏱️ 处理时间: {self.stats['processing_time_seconds']:.1f} 秒")
        logger.info(f"🔍 Google搜索: {self.stats['google_searches']} 次")
        logger.info(f"🎯 GSMArena直接命中: {self.stats['gsmarena_direct_hits']} 次")
        logger.info(f"🔄 GSMChoice备用方案: {self.stats['gsmchoice_fallbacks']} 次")
        
        return summary
    
    def save_results(self) -> Dict[str, str]:
        """保存结果到CSV文件"""
        saved_files = {}
        
        # 保存成功结果
        if self.successful_results:
            success_file = CSVTools.save_device_results(self.successful_results)
            if success_file:
                saved_files['success_file'] = success_file
        
        # 保存失败设备
        if self.failed_devices:
            failed_file = CSVTools.save_failed_devices(self.failed_devices)
            if failed_file:
                saved_files['failed_file'] = failed_file
        
        # 保存处理日志
        log_file = CSVTools.save_processing_log(self.stats)
        if log_file:
            saved_files['log_file'] = log_file
        
        return saved_files
    
    def close(self):
        """关闭所有爬虫连接"""
        if self.google_searcher:
            self.google_searcher.close()
        if self.gsmarena_scraper:
            self.gsmarena_scraper.close()
        if self.gsmchoice_scraper:
            self.gsmchoice_scraper.close()
        
        logger.info("🔒 所有爬虫连接已关闭")

    def _save_single_success_result(self, result_data):
        """立即保存单个成功结果"""
        try:
            # 确定文件路径
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, "device_info_extracted_realtime.csv")
            
            # 转换为DataFrame
            df_new = pd.DataFrame([result_data])
            
            # 检查文件是否存在
            if os.path.exists(filepath):
                # 文件存在，追加数据
                df_new.to_csv(filepath, mode='a', header=False, index=False, encoding='utf-8')
            else:
                # 文件不存在，创建新文件
                df_new.to_csv(filepath, mode='w', header=True, index=False, encoding='utf-8')
            
            logger.info(f"💾 成功结果已实时保存: {result_data['original_model_code']}")
            
        except Exception as e:
            logger.error(f"实时保存成功结果失败: {str(e)}")

    def _save_single_failed_result(self, failed_data):
        """立即保存单个失败结果"""
        try:
            # 确定文件路径
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, "failed_devices_realtime.csv")
            
            # 转换为DataFrame
            df_new = pd.DataFrame([failed_data])
            
            # 检查文件是否存在
            if os.path.exists(filepath):
                # 文件存在，追加数据
                df_new.to_csv(filepath, mode='a', header=False, index=False, encoding='utf-8')
            else:
                # 文件不存在，创建新文件
                df_new.to_csv(filepath, mode='w', header=True, index=False, encoding='utf-8')
            
            logger.info(f"💾 失败结果已实时保存: {failed_data['model_code']}")
            
        except Exception as e:
            logger.error(f"实时保存失败结果失败: {str(e)}")

def main():
    """主函数示例"""
    # 创建调度器
    orchestrator = DeviceInfoOrchestrator(request_delay=4)
    
    try:
        # 读取设备列表
        devices = CSVTools.read_model_codes_csv("model_codes.csv")
        
        if not devices:
            logger.error("没有找到设备数据")
            return
        
        # 处理设备（可以设置max_devices限制处理数量）
        summary = orchestrator.process_device_list(devices, max_devices=10)
        
        # 保存结果
        saved_files = orchestrator.save_results()
        
        logger.info(f"📁 保存的文件: {saved_files}")
        
    finally:
        orchestrator.close()

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    main()