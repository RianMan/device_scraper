#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GSMChoice网站爬虫 - 补充失败设备信息
"""

import pandas as pd
import pymongo
from pymongo import MongoClient
import requests
from bs4 import BeautifulSoup
import json
import logging
import time
from datetime import datetime
import os
import re
from urllib.parse import quote_plus

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GSMChoiceScraper:
    def __init__(self, request_delay=2):
        """初始化GSMChoice爬虫"""
        self.base_url = "https://www.gsmchoice.com"
        self.search_api = "https://www.gsmchoice.com/js/searchy.xhtml"
        self.request_delay = request_delay
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.gsmchoice.com/en/',
            'X-Requested-With': 'XMLHttpRequest'
        })
    
    def search_device(self, manufacture, model):
        """搜索设备"""
        try:
            # 构建搜索查询
            search_query = f"{manufacture} {model}"
            encoded_query = quote_plus(search_query)
            
            search_url = f"{self.search_api}?search={encoded_query}&lang=en&v=3"
            logger.info(f"搜索设备: {search_query}")
            
            time.sleep(self.request_delay)
            
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            # 解析JSON响应
            try:
                results = response.json()
            except json.JSONDecodeError:
                logger.warning(f"无法解析JSON响应: {manufacture} {model}")
                return None
            
            if not results or len(results) == 0:
                logger.warning(f"未找到搜索结果: {manufacture} {model}")
                return None
            
            # 取第一个结果
            first_result = results[0]
            logger.info(f"找到设备: {first_result.get('brand', '')} {first_result.get('model', '')}")
            
            return first_result
            
        except Exception as e:
            logger.error(f"搜索设备失败 {manufacture} {model}: {str(e)}")
            return None
    
    def get_device_details(self, device_info):
        """获取设备详细信息"""
        try:
            sbrand = device_info.get('sbrand', '')
            smodel = device_info.get('smodel', '')
            
            if not sbrand or not smodel:
                logger.warning("缺少sbrand或smodel信息")
                return None
            
            # 构建详情页URL
            detail_url = f"{self.base_url}/en/catalogue/{sbrand}/{smodel}/"
            logger.info(f"获取详情页: {detail_url}")
            
            time.sleep(self.request_delay)
            
            response = self.session.get(detail_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 提取设备信息
            device_details = {
                'device_name': device_info.get('model', 'Unknown'),
                'brand': device_info.get('brand', ''),
                'announced_date': '',
                'price': '',
                'specifications': {},
                'source_url': detail_url
            }
            with open(f'{sbrand}_{smodel}_soup.html', 'w', encoding='utf-8') as f:
                f.write(str(soup))
            # 提取规格信息
            self._extract_specifications(soup, device_details)
            
            # 提取价格信息
            self._extract_price(soup, device_details)
            
            return device_details
            
        except Exception as e:
            logger.error(f"获取设备详情失败: {str(e)}")
            return None
    
    def _extract_specifications(self, soup, device_details):
        """提取规格信息"""
        try:
            # 查找规格表格
            spec_table = soup.find('table', class_='PhoneData')
            if not spec_table:
                logger.warning("未找到规格表格")
                return
            
            rows = spec_table.find_all('tr')
            for row in rows:
                th = row.find('th', class_='phoneCategoryName')
                td = row.find('td', class_='phoneCategoryValue')
                
                if th and td:
                    key = th.get_text(strip=True)
                    value = td.get_text(strip=True)
                    
                    # 清理值中的多余空白
                    value = ' '.join(value.split())
                    
                    # 特殊处理发布日期
                    if 'Announced' in key:
                        device_details['announced_date'] = value
                    
                    # 存储到规格字典
                    device_details['specifications'][key] = value
            
            logger.info(f"提取了 {len(device_details['specifications'])} 个规格项")
            
        except Exception as e:
            logger.error(f"提取规格信息失败: {str(e)}")
    
    def _extract_price(self, soup, device_details):
        """提取价格信息"""
        try:
            # 查找价格容器
            price_container = soup.find('div', class_='scard-widget-prices__container')
            if not price_container:
                logger.warning("未找到价格容器")
                return
            
            # 查找价格链接
            price_links = price_container.find_all('a', class_='scard-widget-prices__button2')
            if not price_links:
                # 尝试其他价格类名
                price_links = price_container.find_all('a', class_=re.compile(r'scard-widget-prices__button'))
            
            if price_links:
                # 取第一个价格
                first_price = price_links[0].get_text(strip=True)
                device_details['price'] = first_price
                logger.info(f"找到价格: {first_price}")
            else:
                logger.warning("未找到价格信息")
            
        except Exception as e:
            logger.error(f"提取价格信息失败: {str(e)}")
    
    def get_device_info(self, manufacture, model):
        """获取完整设备信息"""
        try:
            # 搜索设备
            search_result = self.search_device(manufacture, model)
            if not search_result:
                return {
                    'success': False,
                    'message': f'未找到设备 {manufacture} {model}'
                }
            
            # 获取详细信息
            device_details = self.get_device_details(search_result)
            if not device_details:
                return {
                    'success': False,
                    'message': f'无法获取设备详情 {manufacture} {model}'
                }
            
            return {
                'success': True,
                'source': 'gsmchoice',
                'data': device_details
            }
            
        except Exception as e:
            logger.error(f"获取设备信息失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取设备信息时发生错误: {str(e)}'
            }

class FailedDeviceProcessor:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="device_info"):
        """初始化失败设备处理器"""
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self.collection = None
        
        # 初始化爬虫
        self.scraper = GSMChoiceScraper(request_delay=2)
        
        # 初始化MongoDB连接
        self._init_mongodb()
    
    def _init_mongodb(self):
        """初始化MongoDB连接"""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            self.collection = self.db['devices']
            logger.info(f"MongoDB连接成功: {self.db_name}")
        except Exception as e:
            logger.error(f"MongoDB连接失败: {str(e)}")
            raise
    
    def identify_unknown_devices(self, csv_file="devices_export.csv"):
        """识别device_name为Unknown的设备"""
        try:
            df = pd.read_csv(csv_file)
            unknown_devices = df[df['device_name'] == 'Unknown']
            logger.info(f"发现 {len(unknown_devices)} 个Unknown设备")
            return unknown_devices.to_dict('records')
        except Exception as e:
            logger.error(f"读取CSV文件失败: {str(e)}")
            return []
    
    def read_failed_devices(self, csv_file="failed_devices_20250711_030807.csv"):
        """读取失败设备列表"""
        try:
            if not os.path.exists(csv_file):
                logger.warning(f"失败设备文件不存在: {csv_file}")
                return []
            
            df = pd.read_csv(csv_file)
            logger.info(f"读取到 {len(df)} 个失败设备")
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"读取失败设备文件失败: {str(e)}")
            return []
    
    def process_single_device(self, device_info):
        """处理单个设备"""
        manufacture = device_info.get('manufacture', '').strip()
        model_code = device_info.get('model_code', '').strip()
        
        if not manufacture or not model_code:
            logger.warning(f"设备信息不完整: {device_info}")
            return False
        
        try:
            logger.info(f"正在处理设备: {manufacture} {model_code}")
            
            # 使用GSMChoice搜索
            result = self.scraper.get_device_info(manufacture, model_code)
            
            if result['success']:
                data = result['data']
                
                # 构建MongoDB文档
                device_doc = {
                    "model_code": model_code,
                    "device_name": data['device_name'],
                    "announced_date": data['announced_date'],
                    "release_date": "",  # GSMChoice没有专门的release_date
                    "price": data['price'],
                    "manufacture": manufacture,
                    "source_url": data['source_url'],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                    "specifications": data['specifications'],
                    "data_source": "gsmchoice"  # 标记数据来源
                }
                
                # 检查是否已存在（更新或插入）
                existing = self.collection.find_one({"model_code": model_code})
                if existing:
                    # 如果已存在且是Unknown，则更新
                    if existing.get('device_name') == 'Unknown':
                        self.collection.update_one(
                            {"model_code": model_code},
                            {"$set": device_doc}
                        )
                        logger.info(f"✅ 更新设备: {model_code} - {data['device_name']}")
                    else:
                        logger.info(f"⏭️  设备已存在且有效: {model_code}")
                else:
                    # 插入新设备
                    self.collection.insert_one(device_doc)
                    logger.info(f"✅ 新增设备: {model_code} - {data['device_name']}")
                
                logger.info(f"   价格: {data['price']}")
                return True
                
            else:
                logger.warning(f"❌ 未找到设备: {manufacture} {model_code} - {result['message']}")
                return False
                
        except Exception as e:
            logger.error(f"处理设备失败 {manufacture} {model_code}: {str(e)}")
            return False
    
    def process_failed_devices(self, failed_csv="failed_devices_20250711_030807.csv", 
                              export_csv="devices_export.csv"):
        """处理失败设备和Unknown设备"""
        
        # 1. 读取失败设备
        failed_devices = self.read_failed_devices(failed_csv)
        
        # 2. 读取Unknown设备
        unknown_devices = self.identify_unknown_devices(export_csv)
        
        # 3. 合并设备列表
        all_devices = failed_devices + unknown_devices
        
        # 4. 去重（基于model_code）
        unique_devices = {}
        for device in all_devices:
            model_code = device.get('model_code', '')
            if model_code and model_code not in unique_devices:
                unique_devices[model_code] = device
        
        devices_to_process = list(unique_devices.values())
        logger.info(f"总共需要处理 {len(devices_to_process)} 个设备")
        
        # 5. 处理设备
        success_count = 0
        failed_count = 0
        still_failed = []
        
        for i, device in enumerate(devices_to_process, 1):
            logger.info(f"进度: {i}/{len(devices_to_process)} ({i/len(devices_to_process)*100:.1f}%)")
            
            success = self.process_single_device(device)
            
            if success:
                success_count += 1
            else:
                failed_count += 1
                still_failed.append(device)
        
        # 6. 保存仍然失败的设备
        if still_failed:
            failed_df = pd.DataFrame(still_failed)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            failed_file = f"still_failed_devices_{timestamp}.csv"
            failed_df.to_csv(failed_file, index=False)
            logger.info(f"仍然失败的设备已保存到: {failed_file}")
        
        # 7. 输出统计
        logger.info(f"\n处理完成!")
        logger.info(f"总数: {len(devices_to_process)}")
        logger.info(f"成功: {success_count}")
        logger.info(f"失败: {failed_count}")
        logger.info(f"成功率: {success_count/len(devices_to_process)*100:.1f}%")
    
    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()
            logger.info("数据库连接已关闭")

def main():
    """主函数"""
    try:
        processor = FailedDeviceProcessor()
    except Exception as e:
        logger.error(f"初始化处理器失败: {str(e)}")
        return
    
    try:
        start_time = time.time()
        
        # 处理失败设备和Unknown设备
        processor.process_failed_devices()
        
        end_time = time.time()
        logger.info(f"总耗时: {end_time - start_time:.2f} 秒")
        
    finally:
        processor.close()

if __name__ == "__main__":
    main()