#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合策略设备信息爬虫
1. GSMChoice获取设备名称
2. GSMArena获取详细信息和价格
3. 处理失败设备和Unknown设备
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
from urllib.parse import quote_plus, urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HybridDeviceScraper:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="device_info", request_delay=3):
        """初始化混合策略爬虫"""
        self.request_delay = request_delay
        
        # GSMChoice配置
        self.gsmchoice_base = "https://www.gsmchoice.com"
        self.gsmchoice_search_api = "https://www.gsmchoice.com/js/searchy.xhtml"
        
        # GSMArena配置
        self.gsmarena_base = "https://www.gsmarena.com"
        
        # 初始化MongoDB
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client[db_name]
        self.collection = self.db['devices']
        
        # 初始化session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        
        # 初始化Selenium WebDriver
        self.driver = None
        self._init_driver()
        
        logger.info("🚀 混合策略爬虫初始化完成")
    
    def _init_driver(self):
        """初始化Selenium WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(30)
            logger.info("✅ Selenium WebDriver初始化成功")
        except Exception as e:
            logger.error(f"❌ WebDriver初始化失败: {str(e)}")
            self.driver = None
    
    def get_device_name_from_gsmchoice(self, manufacture, model_code):
        """从GSMChoice获取准确的设备名称（只要名称，不要价格）"""
        try:
            search_query = f"{manufacture} {model_code}"
            encoded_query = quote_plus(search_query)
            
            # 方法1: API搜索
            search_url = f"{self.gsmchoice_search_api}?search={encoded_query}&lang=en&v=3"
            logger.info(f"🔍 GSMChoice API搜索: {search_query}")
            
            time.sleep(self.request_delay)
            
            try:
                response = self.session.get(search_url, timeout=30)
                response.raise_for_status()
                results = response.json()
                
                if results and len(results) > 0:
                    first_result = results[0]
                    device_name = first_result.get('model', '').strip()
                    if device_name and device_name != 'Unknown':
                        logger.info(f"✅ GSMChoice API找到设备名称: {device_name}")
                        return device_name
            except Exception as e:
                logger.warning(f"GSMChoice API搜索失败: {str(e)}")
            
            # 方法2: 网页搜索
            if self.driver:
                try:
                    search_url = f"{self.gsmchoice_base}/en/search/?sSearch4={encoded_query}"
                    logger.info(f"🌐 GSMChoice网页搜索: {search_query}")
                    
                    self.driver.get(search_url)
                    time.sleep(3)
                    
                    # 查找搜索结果
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    device_links = soup.find_all('a', href=re.compile(r'/en/catalogue/.*/.*/'))
                    
                    if device_links:
                        # 访问第一个设备详情页获取名称
                        first_link = device_links[0]
                        href = first_link.get('href', '')
                        
                        if href:
                            detail_url = urljoin(self.gsmchoice_base, href)
                            self.driver.get(detail_url)
                            time.sleep(2)
                            
                            detail_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                            title_element = detail_soup.find('h1', class_='infoline__title')
                            
                            if title_element:
                                title_span = title_element.find('span')
                                if title_span:
                                    device_name = title_span.get_text(strip=True)
                                    logger.info(f"✅ GSMChoice网页找到设备名称: {device_name}")
                                    return device_name
                except Exception as e:
                    logger.warning(f"GSMChoice网页搜索失败: {str(e)}")
            
            logger.warning(f"❌ GSMChoice未找到设备: {manufacture} {model_code}")
            return None
            
        except Exception as e:
            logger.error(f"❌ GSMChoice搜索异常: {str(e)}")
            return None
    
    def search_gsmarena_by_name(self, device_name):
        """通过设备名称在GSMArena搜索"""
        if not self.driver:
            logger.error("WebDriver未初始化")
            return None
        
        try:
            # 清理设备名称，提取关键词
            clean_name = re.sub(r'[^\w\s]', ' ', device_name)
            search_terms = clean_name.strip().split()
            
            # 尝试不同的搜索组合
            search_queries = [
                device_name,  # 完整名称
                ' '.join(search_terms[:3]),  # 前3个词
                ' '.join(search_terms[:2]),  # 前2个词
            ]
            
            for query in search_queries:
                encoded_query = quote_plus(query)
                search_url = f"{self.gsmarena_base}/res.php3?sSearch={encoded_query}"
                logger.info(f"🔍 GSMArena搜索: {query}")
                
                try:
                    self.driver.get(search_url)
                    wait = WebDriverWait(self.driver, 15)
                    
                    # 等待解密内容
                    decrypted_element = wait.until(
                        EC.presence_of_element_located((By.ID, "decrypted"))
                    )
                    
                    # 等待内容加载
                    wait.until(lambda d: decrypted_element.get_attribute('innerHTML').strip() != '')
                    time.sleep(2)
                    
                    decrypted_content = decrypted_element.get_attribute('innerHTML')
                    if not decrypted_content or decrypted_content.strip() == '':
                        continue
                    
                    soup = BeautifulSoup(decrypted_content, 'html.parser')
                    device_links = []
                    
                    # 查找设备链接
                    makers_div = soup.find('div', class_='makers')
                    if makers_div:
                        device_links = makers_div.find_all('a', href=True)
                    
                    if not device_links:
                        all_links = soup.find_all('a', href=True)
                        device_links = [link for link in all_links if '.php' in link.get('href', '')]
                    
                    if device_links:
                        first_device = device_links[0]
                        device_url = first_device.get('href')
                        
                        if device_url:
                            if not device_url.startswith('http'):
                                full_url = urljoin(self.gsmarena_base, device_url)
                            else:
                                full_url = device_url
                            
                            logger.info(f"✅ GSMArena找到设备: {query} -> {full_url}")
                            return full_url
                    
                except TimeoutException:
                    logger.warning(f"GSMArena搜索超时: {query}")
                    continue
                except Exception as e:
                    logger.warning(f"GSMArena搜索异常: {query} - {str(e)}")
                    continue
                
                time.sleep(self.request_delay)
            
            logger.warning(f"❌ GSMArena未找到设备: {device_name}")
            return None
            
        except Exception as e:
            logger.error(f"❌ GSMArena搜索异常: {str(e)}")
            return None
    
    def extract_gsmarena_details(self, device_url):
        """从GSMArena提取详细信息"""
        try:
            logger.info(f"📄 提取GSMArena详情: {device_url}")
            
            response = self.session.get(device_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 提取设备名称
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
            
            # 提取规格信息
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
                        
                        # 存储所有规格
                        if len(cell_texts) >= 2:
                            key = next((text for text in cell_texts if text), '')
                            value = cell_texts[-1]
                            
                            if key and value and key != value:
                                device_info['specifications'][key] = value
            
            logger.info(f"✅ GSMArena信息提取完成: {device_name}")
            return device_info
            
        except Exception as e:
            logger.error(f"❌ GSMArena信息提取失败: {str(e)}")
            return None
    
    def process_single_device(self, device_info):
        """处理单个设备的混合策略"""
        manufacture = device_info.get('manufacture', '').strip()
        model_code = device_info.get('model_code', '').strip()
        
        if not manufacture or not model_code:
            logger.warning(f"设备信息不完整: {device_info}")
            return False
        
        try:
            logger.info(f"🔄 处理设备: {manufacture} {model_code}")
            
            # 检查数据库中是否已存在且不是Unknown
            existing = self.collection.find_one({"model_code": model_code})
            if existing and existing.get('device_name', '') != 'Unknown':
                logger.info(f"⏭️ 设备已存在且有效: {model_code}")
                return True
            
            # 步骤1: 从GSMChoice获取设备名称（忽略价格信息）
            device_name = self.get_device_name_from_gsmchoice(manufacture, model_code)
            
            if not device_name:
                logger.warning(f"❌ 无法从GSMChoice获取设备名称: {manufacture} {model_code}")
                return False
            
            # 步骤2: 使用设备名称在GSMArena搜索并获取完整信息
            gsmarena_url = self.search_gsmarena_by_name(device_name)
            
            if not gsmarena_url:
                logger.warning(f"❌ 无法在GSMArena找到设备: {device_name}")
                return False
            
            # 步骤3: 从GSMArena提取详细信息（包括准确的价格）
            gsmarena_details = self.extract_gsmarena_details(gsmarena_url)
            
            if not gsmarena_details:
                logger.warning(f"❌ 无法从GSMArena提取详情: {device_name}")
                return False
            
            # 步骤4: 构建最终的设备文档
            device_doc = {
                "model_code": model_code,
                "device_name": gsmarena_details['name'],  # 使用GSMArena的准确名称
                "announced_date": gsmarena_details['announced_date'],
                "release_date": gsmarena_details['release_date'],
                "price": gsmarena_details['price'],
                "manufacture": manufacture,
                "source_url": gsmarena_url,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "specifications": gsmarena_details['specifications'],
                "data_source": "hybrid_gsmchoice_gsmarena",
                "gsmchoice_name": device_name  # 保存GSMChoice找到的名称作为参考
            }
            
            # 步骤5: 更新或插入数据库
            if existing:
                self.collection.update_one(
                    {"model_code": model_code},
                    {"$set": device_doc}
                )
                logger.info(f"✅ 更新设备: {model_code} - {gsmarena_details['name']}")
            else:
                self.collection.insert_one(device_doc)
                logger.info(f"✅ 混合策略成功处理设备:")
            logger.info(f"   型号代码: {model_code}")
            logger.info(f"   GSMChoice发现名称: {device_name}")
            logger.info(f"   GSMArena确认名称: {gsmarena_details['name']}")
            logger.info(f"   价格: {gsmarena_details['price']}")
            logger.info(f"   发布日期: {gsmarena_details['announced_date']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 处理设备失败 {manufacture} {model_code}: {str(e)}")
            return False
    
    def read_failed_devices(self, failed_csv="data/failed_devices_20250711_030807.csv"):
        """读取失败设备列表"""
        try:
            if os.path.exists(failed_csv):
                df = pd.read_csv(failed_csv)
                logger.info(f"📄 读取失败设备文件: {failed_csv}, 共 {len(df)} 个设备")
                return df.to_dict('records')
            else:
                logger.warning(f"失败设备文件不存在: {failed_csv}")
                return []
        except Exception as e:
            logger.error(f"读取失败设备文件失败: {str(e)}")
            return []
    
    def read_unknown_devices(self, export_csv="data/devices_export.csv"):
        """读取Unknown设备"""
        try:
            if os.path.exists(export_csv):
                df = pd.read_csv(export_csv)
                unknown_df = df[df['device_name'] == 'Unknown']
                logger.info(f"📄 从导出文件识别Unknown设备: {len(unknown_df)} 个")
                
                # 转换为处理格式
                unknown_devices = []
                for _, row in unknown_df.iterrows():
                    unknown_devices.append({
                        'manufacture': row.get('manufacture', ''),
                        'model_code': row.get('model_code', '')
                    })
                
                return unknown_devices
            else:
                logger.warning(f"导出文件不存在: {export_csv}")
                return []
        except Exception as e:
            logger.error(f"读取Unknown设备失败: {str(e)}")
            return []
    
    def process_failed_and_unknown_devices(self):
        """处理失败设备和Unknown设备"""
        logger.info("🚀 开始处理失败设备和Unknown设备")
        
        # 读取失败设备
        failed_devices = self.read_failed_devices()
        
        # 读取Unknown设备
        unknown_devices = self.read_unknown_devices()
        
        # 合并设备列表
        all_devices = failed_devices + unknown_devices
        
        # 去重（基于model_code）
        unique_devices = {}
        for device in all_devices:
            model_code = device.get('model_code', '')
            if model_code and model_code not in unique_devices:
                unique_devices[model_code] = device
        
        devices_to_process = list(unique_devices.values())
        logger.info(f"📊 总计需要处理 {len(devices_to_process)} 个设备")
        logger.info(f"   失败设备: {len(failed_devices)}")
        logger.info(f"   Unknown设备: {len(unknown_devices)}")
        logger.info(f"   去重后: {len(devices_to_process)}")
        
        # 处理设备
        success_count = 0
        failed_count = 0
        still_failed = []
        
        for i, device in enumerate(devices_to_process, 1):
            logger.info(f"📱 进度: {i}/{len(devices_to_process)} ({i/len(devices_to_process)*100:.1f}%)")
            
            success = self.process_single_device(device)
            
            if success:
                success_count += 1
            else:
                failed_count += 1
                still_failed.append(device)
            
            # 添加延迟避免被封
            time.sleep(self.request_delay)
        
        # 保存仍然失败的设备
        if still_failed:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            failed_file = f"data/still_failed_hybrid_{timestamp}.csv"
            
            os.makedirs('data', exist_ok=True)
            failed_df = pd.DataFrame(still_failed)
            failed_df.to_csv(failed_file, index=False)
            logger.info(f"💾 仍然失败的设备已保存到: {failed_file}")
        
        # 输出统计
        logger.info(f"\n🎯 处理完成!")
        logger.info(f"📊 总数: {len(devices_to_process)}")
        logger.info(f"✅ 成功: {success_count}")
        logger.info(f"❌ 失败: {failed_count}")
        logger.info(f"📈 成功率: {success_count/len(devices_to_process)*100:.1f}%")
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.quit()
            logger.info("🔒 WebDriver已关闭")
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("🔒 数据库连接已关闭")

def main():
    """主函数"""
    logger.info("🔧 启动混合策略设备信息爬虫")
    
    # 检查必要文件
    required_files = [
        "data/failed_devices_20250711_030807.csv",
        "data/devices_export.csv"
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        logger.error(f"❌ 缺少必要文件: {missing_files}")
        logger.info("请确保以下文件存在:")
        for file in missing_files:
            logger.info(f"  - {file}")
        return
    
    try:
        # 初始化爬虫
        scraper = HybridDeviceScraper(request_delay=4)  # 4秒间隔，更安全
        
        # 开始处理
        start_time = time.time()
        scraper.process_failed_and_unknown_devices()
        end_time = time.time()
        
        logger.info(f"⏱️ 总耗时: {end_time - start_time:.2f} 秒")
        
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            scraper.close()
        except:
            pass

if __name__ == "__main__":
    main()