#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯净的设备信息爬虫类 - 无Flask依赖，支持多线程
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import logging
from urllib.parse import urljoin, quote_plus
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeviceInfoScraper:
    def __init__(self, max_workers=5, timeout=60, request_delay=5):
        """初始化设备信息爬虫
        
        Args:
            max_workers (int): 最大并发线程数（默认5个）
            timeout (int): WebDriver超时时间（秒）
            request_delay (int): 请求间隔时间（秒）
        """
        self.base_url = "https://www.gsmarena.com"
        self.max_workers = max_workers
        self.timeout = timeout
        self.request_delay = request_delay
        self.session = requests.Session()
        
        # 请求时间控制
        self.last_request_time = {}
        self.request_lock = threading.Lock()
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        # WebDriver池
        self.driver_pool = queue.Queue()
        self.driver_lock = threading.Lock()
        
        # 初始化WebDriver池
        self._init_driver_pool()
    
    def _wait_for_request(self, thread_id):
        """控制请求间隔"""
        with self.request_lock:
            current_time = time.time()
            last_time = self.last_request_time.get(thread_id, 0)
            
            if current_time - last_time < self.request_delay:
                wait_time = self.request_delay - (current_time - last_time)
                logger.info(f"线程 {thread_id} 等待 {wait_time:.1f} 秒...")
                time.sleep(wait_time)
            
            self.last_request_time[thread_id] = time.time()
    
    def _init_driver_pool(self):
        """初始化WebDriver池"""
        logger.info(f"初始化 {self.max_workers} 个WebDriver实例...")
        
        for i in range(self.max_workers):
            try:
                driver = self._create_driver(f"driver_{i}")
                if driver:
                    self.driver_pool.put(driver)
                    logger.info(f"WebDriver {i+1}/{self.max_workers} 初始化成功")
                else:
                    logger.warning(f"WebDriver {i+1} 初始化失败")
            except Exception as e:
                logger.error(f"创建WebDriver {i+1} 失败: {str(e)}")
        
        logger.info(f"WebDriver池初始化完成，可用实例: {self.driver_pool.qsize()}")
    
    def _create_driver(self, driver_id):
        """创建单个WebDriver实例"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # 不加载图片，提高速度
            chrome_options.add_argument(f'--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(self.timeout)
            driver.implicitly_wait(10)
            
            # 设置一个标识
            driver.driver_id = driver_id
            return driver
            
        except Exception as e:
            logger.error(f"创建WebDriver失败: {str(e)}")
            return None
    
    def _get_driver(self):
        """从池中获取WebDriver"""
        try:
            return self.driver_pool.get(timeout=30)
        except queue.Empty:
            logger.warning("WebDriver池为空，创建临时实例")
            return self._create_driver("temp")
    
    def _return_driver(self, driver):
        """将WebDriver返回到池中"""
        if driver and hasattr(driver, 'driver_id') and 'temp' not in driver.driver_id:
            self.driver_pool.put(driver)
    
    def search_device(self, model_code):
        """搜索设备（Selenium方式，控制请求频率）"""
        thread_id = threading.current_thread().ident
        
        # 控制请求间隔
        self._wait_for_request(thread_id)
        
        driver = self._get_driver()
        if not driver:
            logger.error("无法获取WebDriver，尝试备用方案")
            return self.try_direct_access(model_code)
            
        try:
            # URL编码优化：空格转换为+号
            encoded_model = quote_plus(model_code)
            search_url = f"{self.base_url}/res.php3?sSearch={encoded_model}"
            logger.info(f"搜索设备: {model_code} (线程: {thread_id})")
            
            driver.get(search_url)
            wait = WebDriverWait(driver, self.timeout)
            
            try:
                # 等待页面加载完成
                decrypted_element = wait.until(
                    EC.presence_of_element_located((By.ID, "decrypted"))
                )
                
                # 等待内容解密
                wait.until(lambda d: decrypted_element.get_attribute('innerHTML').strip() != '')
                time.sleep(2)  # 稍微等待确保内容完全加载
                
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
                    
                    logger.info(f"找到设备: {device_name} - {model_code}")
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
        finally:
            self._return_driver(driver)
    
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
        """提取设备详细信息"""
        try:
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
        """获取单个设备信息"""
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
    
    def batch_get_device_info(self, device_list, progress_callback=None):
        """批量并行获取设备信息"""
        results = []
        failed_devices = []
        
        logger.info(f"开始并行处理 {len(device_list)} 个设备，线程数: {self.max_workers}")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_device = {
                executor.submit(self.get_device_info, device['model_code']): device 
                for device in device_list
            }
            
            completed = 0
            total = len(device_list)
            
            # 处理完成的任务
            for future in as_completed(future_to_device):
                device = future_to_device[future]
                completed += 1
                
                try:
                    result = future.result()
                    if result['success']:
                        # 添加制造商信息
                        result['data']['manufacture'] = device['manufacture']
                        results.append({
                            'device_info': device,
                            'scrape_result': result
                        })
                        logger.info(f"✅ [{completed}/{total}] 成功: {device['model_code']} - {result['data']['device_name']}")
                    else:
                        failed_devices.append(device)
                        logger.warning(f"❌ [{completed}/{total}] 失败: {device['model_code']} - {result['message']}")
                        
                except Exception as e:
                    failed_devices.append(device)
                    logger.error(f"❌ [{completed}/{total}] 异常: {device['model_code']} - {str(e)}")
                
                # 调用进度回调
                if progress_callback:
                    progress_callback(completed, total, len(results), len(failed_devices))
                
                # 添加小延迟避免过于频繁
                time.sleep(0.1)
        
        logger.info(f"批量处理完成: 成功 {len(results)}, 失败 {len(failed_devices)}")
        return results, failed_devices
    
    def close(self):
        """关闭所有WebDriver"""
        logger.info("正在关闭WebDriver池...")
        
        # 关闭池中的所有WebDriver
        while not self.driver_pool.empty():
            try:
                driver = self.driver_pool.get_nowait()
                driver.quit()
            except (queue.Empty, Exception) as e:
                logger.warning(f"关闭WebDriver时出错: {str(e)}")
        
        logger.info("WebDriver池已关闭")