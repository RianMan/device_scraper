#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的单线程数据导入脚本 - 避免被封IP
"""

import pandas as pd
import pymongo
from pymongo import MongoClient
import json
import logging
import time
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import random

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleDeviceScraper:
    def __init__(self, request_delay=3):
        """初始化简单的设备爬虫（单线程，增强伪装）"""
        self.base_url = "https://www.gsmarena.com"
        self.request_delay = request_delay
        self.session = requests.Session()
        
        # 随机User-Agent池
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0'
        ]
        
        # 设置基础请求头
        self._update_session_headers()
        
        # 初始化单个WebDriver
        self.driver = None
        self._init_driver()
        
        # 请求计数器
        self.request_count = 0
    
    def _get_random_user_agent(self):
        """获取随机User-Agent"""
        return random.choice(self.user_agents)
    
    def _update_session_headers(self):
        """更新session请求头（随机化）"""
        self.session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-US,en;q=0.9,zh-CN;q=0.8', 'en-GB,en;q=0.9']),
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': random.choice(['none', 'same-origin', 'cross-site']),
            'Sec-Fetch-User': '?1',
            'Cache-Control': random.choice(['max-age=0', 'no-cache']),
            'DNT': '1'
        })
    
    def _init_driver(self):
        """初始化单个WebDriver（增强伪装）"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # 不加载图片，提高速度
            chrome_options.add_argument('--disable-javascript')  # 禁用JS检测
            chrome_options.add_argument('--window-size=1920,1080')
            
            # 随机窗口大小
            width = random.randint(1280, 1920)
            height = random.randint(720, 1080)
            chrome_options.add_argument(f'--window-size={width},{height}')
            
            # 随机User-Agent
            chrome_options.add_argument(f'--user-agent={self._get_random_user_agent()}')
            
            # 禁用自动化检测
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 添加随机的浏览器特征
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # 执行JavaScript隐藏webdriver特征
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.driver.set_page_load_timeout(60)
            logger.info("WebDriver初始化成功（增强伪装）")
        except Exception as e:
            logger.error(f"WebDriver初始化失败: {str(e)}")
            self.driver = None
    
    def _random_delay(self):
        """随机延迟"""
        base_delay = self.request_delay
        random_delay = random.uniform(base_delay * 0.8, base_delay * 1.5)
        logger.info(f"等待 {random_delay:.1f} 秒...")
        time.sleep(random_delay)
    
    def _maybe_update_headers(self):
        """偶尔更新请求头"""
        self.request_count += 1
        if self.request_count % 10 == 0:  # 每10个请求更新一次
            logger.info("更新请求头以增强伪装...")
            self._update_session_headers()
    
    def search_device(self, model_code):
        """搜索设备（单线程，增强伪装）"""
        if not self.driver:
            logger.error("WebDriver未初始化，尝试备用方案")
            return self.try_direct_access(model_code)
        
        try:
            # 随机延迟和更新头信息
            self._random_delay()
            self._maybe_update_headers()
            
            # URL编码优化：空格转换为+号
            encoded_model = quote_plus(model_code)
            search_url = f"{self.base_url}/res.php3?sSearch={encoded_model}"
            logger.info(f"搜索设备: {model_code}")
            
            self.driver.get(search_url)
            wait = WebDriverWait(self.driver, 30)
            
            try:
                # 等待页面加载完成
                decrypted_element = wait.until(
                    EC.presence_of_element_located((By.ID, "decrypted"))
                )
                
                # 等待内容解密
                wait.until(lambda d: decrypted_element.get_attribute('innerHTML').strip() != '')
                
                # 随机等待时间
                random_wait = random.uniform(1.5, 3.0)
                time.sleep(random_wait)
                
                decrypted_content = decrypted_element.get_attribute('innerHTML')
                if not decrypted_content or decrypted_content.strip() == '':
                    logger.warning(f"解密内容为空: {model_code}")
                    return self.try_direct_access(model_code)
                
                soup = BeautifulSoup(decrypted_content, 'html.parser')
                device_links = []
                
                # 查找设备链接
                makers_div = soup.find('div', class_='makers')
                if makers_div:
                    device_links = makers_div.find_all('a', href=True)
                
                if not device_links:
                    all_links = soup.find_all('a', href=True)
                    device_links = [link for link in all_links if '.php' in link.get('href', '')]
                
                if not device_links:
                    logger.warning(f"未找到设备链接: {model_code}")
                    return self.try_direct_access(model_code)
                
                first_device = device_links[0]
                device_url = first_device.get('href')
                
                if device_url:
                    device_name = first_device.get_text(strip=True)
                    if not device_name:
                        span_tag = first_device.find('span')
                        if span_tag:
                            device_name = span_tag.get_text(strip=True)
                        else:
                            device_name = "Unknown"
                    
                    if not device_url.startswith('http'):
                        full_url = urljoin(self.base_url, device_url)
                    else:
                        full_url = device_url
                    
                    return {
                        'name': device_name,
                        'url': full_url,
                        'relative_url': device_url
                    }
                
                return self.try_direct_access(model_code)
                
            except TimeoutException:
                logger.warning(f"等待解密内容超时: {model_code}")
                return self.try_direct_access(model_code)
                
        except Exception as e:
            logger.error(f"搜索设备失败 {model_code}: {str(e)}")
            return self.try_direct_access(model_code)
    
    def try_direct_access(self, model_code):
        """直接访问已知设备"""
        known_mappings = {
            'CPH1931': 'oppo_a5_(2020)-9883.php',
            'CPH2387': 'oppo_a57_4g-11565.php',
            'V2111': 'vivo_y21-11063.php',
            'CPH2471': 'oppo_a96-11827.php',
            'CPH2269': 'oppo_reno7-11534.php',
            'SM-A245F': 'samsung_galaxy_a24-12421.php',
            'SM-G991B': 'samsung_galaxy_s21-10626.php'
        }
        
        if model_code in known_mappings:
            full_url = f"{self.base_url}/{known_mappings[model_code]}"
            logger.info(f"使用直接映射: {model_code}")
            return {
                'name': 'Unknown',
                'url': full_url,
                'relative_url': known_mappings[model_code]
            }
        return None
    
    def extract_device_details(self, device_url):
        """提取设备详细信息（增强伪装）"""
        try:
            # 随机延迟
            random_delay = random.uniform(0.8, 1.5)
            time.sleep(random_delay)
            
            # 偶尔更新请求头
            self._maybe_update_headers()
            
            response = self.session.get(device_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            device_name = soup.find('h1', class_='specs-phone-name-title')
            if device_name:
                device_name = device_name.get_text(strip=True)
            else:
                device_name = "Unknown"
            
            device_info = {
                'name': device_name,
                'model_code': '',
                'announced_date': '',
                'release_date': '',
                'price': '',
                'specifications': {}
            }
            
            specs_tables = soup.find_all('table', cellspacing='0')
            
            for table in specs_tables:
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all(['th', 'td'])
                    if len(cells) >= 2:
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        
                        for i, cell_text in enumerate(cell_texts):
                            if 'Announced' in cell_text and i + 1 < len(cell_texts):
                                announced_info = cell_texts[i + 1]
                                device_info['announced_date'] = announced_info
                                
                                if 'Released' in announced_info:
                                    parts = announced_info.split('Released')
                                    if len(parts) > 1:
                                        device_info['release_date'] = f"Released {parts[1].strip()}"
                                    announced_part = parts[0].replace('.', '').strip()
                                    device_info['announced_date'] = announced_part
                                
                            elif 'Status' in cell_text and i + 1 < len(cell_texts):
                                status_info = cell_texts[i + 1]
                                if not device_info['release_date']:
                                    device_info['release_date'] = status_info
                                
                            elif 'Price' in cell_text and i + 1 < len(cell_texts):
                                price_info = cell_texts[i + 1]
                                device_info['price'] = price_info
                                
                            elif 'Models' in cell_text and i + 1 < len(cell_texts):
                                models_info = cell_texts[i + 1]
                                device_info['model_code'] = models_info
                        
                        if len(cell_texts) >= 2:
                            key = next((text for text in cell_texts if text), '')
                            value = cell_texts[-1]
                            
                            if key and value and key != value:
                                device_info['specifications'][key] = value
            
            return device_info
            
        except Exception as e:
            logger.error(f"提取设备详情失败: {str(e)}")
            return None
    
    def get_device_info(self, model_code):
        """获取设备信息"""
        try:
            search_result = self.search_device(model_code)
            if not search_result:
                return {
                    'success': False,
                    'message': f'未找到型号 {model_code} 的设备信息'
                }
            
            device_details = self.extract_device_details(search_result['url'])
            if not device_details:
                return {
                    'success': False,
                    'message': f'无法获取设备 {search_result["name"]} 的详细信息'
                }
            
            result = {
                'success': True,
                'source': 'scraper',
                'data': {
                    'search_model': model_code,
                    'device_name': device_details['name'],
                    'model_code': device_details['model_code'],
                    'announced_date': device_details['announced_date'],
                    'release_date': device_details['release_date'],
                    'price': device_details['price'],
                    'source_url': search_result['url'],
                    'specifications': device_details['specifications']
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取设备信息失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取设备信息时发生错误: {str(e)}'
            }
    
    def close(self):
        """关闭WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver已关闭")

class SimpleDataImporter:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="device_info", request_delay=3):
        """初始化数据导入器（单线程）"""
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.request_delay = request_delay
        self.client = None
        self.db = None
        self.collection = None
        
        # 初始化爬虫
        self.scraper = SimpleDeviceScraper(request_delay=request_delay)
        
        # 初始化MongoDB连接
        self._init_mongodb()
    
    def _init_mongodb(self):
        """初始化MongoDB连接"""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            self.collection = self.db['devices']
            
            # 创建索引
            self.collection.create_index("model_code", unique=True)
            self.collection.create_index("device_name")
            
            logger.info(f"MongoDB连接成功: {self.db_name}")
        except Exception as e:
            logger.error(f"MongoDB连接失败: {str(e)}")
            raise
    
    def read_csv_data(self, csv_file="device_result.csv"):
        """读取CSV文件中的设备数据"""
        try:
            df = pd.read_csv(csv_file)
            logger.info(f"成功读取CSV文件: {csv_file}, 共 {len(df)} 行数据")
            
            devices = []
            for index, row in df.iterrows():
                manufacture = str(row['clientmanufacture']).strip() if pd.notna(row['clientmanufacture']) else ''
                model = str(row['clientmodel']).strip() if pd.notna(row['clientmodel']) else ''
                
                if manufacture and model:
                    devices.append({
                        'manufacture': manufacture,
                        'model_code': model,
                        'raw_data': f"{manufacture} {model}"
                    })
            
            logger.info(f"提取到 {len(devices)} 个有效设备信息")
            return devices
            
        except Exception as e:
            logger.error(f"读取CSV文件失败: {str(e)}")
            return []
    
    def normalize_model_code(self, model_code):
        """标准化设备型号代码"""
        return ' '.join(model_code.strip().split())
    
    def filter_existing_devices(self, devices):
        """过滤掉数据库中已存在的设备"""
        existing_codes = set()
        try:
            cursor = self.collection.find({}, {"model_code": 1})
            for doc in cursor:
                normalized_code = self.normalize_model_code(doc["model_code"])
                existing_codes.add(normalized_code)
            
            logger.info(f"数据库中已存在 {len(existing_codes)} 个设备")
        except Exception as e:
            logger.warning(f"查询已存在设备失败: {str(e)}")
        
        new_devices = []
        for device in devices:
            normalized_code = self.normalize_model_code(device['model_code'])
            if normalized_code not in existing_codes:
                new_devices.append(device)
            else:
                logger.info(f"设备已存在，跳过: {device['model_code']}")
        
        logger.info(f"需要处理的新设备: {len(new_devices)} 个")
        return new_devices
    
    def process_single_device(self, device_info):
        """处理单个设备"""
        model_code = device_info['model_code']
        
        try:
            logger.info(f"正在处理设备: {model_code}")
            result = self.scraper.get_device_info(model_code)
            
            if result['success']:
                data = result['data']
                
                device_doc = {
                    "model_code": model_code,
                    "device_name": data['device_name'],
                    "announced_date": data['announced_date'],
                    "release_date": data['release_date'],
                    "price": data['price'],
                    "manufacture": device_info['manufacture'],
                    "source_url": data['source_url'],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                    "specifications": data['specifications']
                }
                
                self.collection.insert_one(device_doc)
                logger.info(f"✅ 成功存储: {model_code} - {data['device_name']}")
                logger.info(f"   价格: {data['price']}")
                return True
                
            else:
                logger.warning(f"❌ 未找到设备信息: {model_code} - {result['message']}")
                return False
                
        except Exception as e:
            logger.error(f"处理设备 {model_code} 时出错: {str(e)}")
            return False
    
    def batch_process_devices(self, csv_file="device_result.csv"):
        """批量处理设备信息（单线程）"""
        devices = self.read_csv_data(csv_file)
        
        if not devices:
            logger.error("没有读取到设备数据")
            return
        
        new_devices = self.filter_existing_devices(devices)
        
        if not new_devices:
            logger.info("所有设备都已存在于数据库中")
            return
        
        total_count = len(new_devices)
        success_count = 0
        failed_devices = []
        
        logger.info(f"开始处理 {total_count} 个新设备...")
        logger.info(f"配置: 单线程，每个请求间隔 {self.request_delay} 秒")
        
        for i, device in enumerate(new_devices, 1):
            logger.info(f"进度: {i}/{total_count} ({i/total_count*100:.1f}%)")
            
            success = self.process_single_device(device)
            
            if success:
                success_count += 1
            else:
                failed_devices.append(device)
        
        # 保存失败的设备
        if failed_devices:
            failed_df = pd.DataFrame(failed_devices)
            csv_filename = f"failed_devices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            failed_df.to_csv(csv_filename, index=False)
            logger.info(f"失败设备信息已保存到: {csv_filename}")
        
        logger.info(f"处理完成!")
        logger.info(f"总数: {total_count}")
        logger.info(f"成功: {success_count}")
        logger.info(f"失败: {len(failed_devices)}")
        logger.info(f"成功率: {success_count/total_count*100:.1f}%")
    
    def close(self):
        """关闭连接"""
        if self.scraper:
            self.scraper.close()
        if self.client:
            self.client.close()
            logger.info("数据库连接已关闭")

def main():
    """主函数"""
    csv_file = "device_result.csv"
    if not os.path.exists(csv_file):
        logger.error(f"CSV文件不存在: {csv_file}")
        return
    
    try:
        # 3秒间隔，稳妥一些
        importer = SimpleDataImporter(request_delay=3)
    except Exception as e:
        logger.error(f"初始化数据导入器失败: {str(e)}")
        return
    
    try:
        start_time = time.time()
        importer.batch_process_devices(csv_file)
        end_time = time.time()
        
        logger.info(f"总耗时: {end_time - start_time:.2f} 秒")
        
    finally:
        importer.close()

if __name__ == "__main__":
    main()