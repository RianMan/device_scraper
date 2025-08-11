#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GSMArena爬虫模块 - gsmarena/gsmarena_scraper.py
负责从GSMArena网站提取设备详细信息
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from urllib.parse import urljoin, quote_plus
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger(__name__)

class GSMArenaScraper:
    def __init__(self, request_delay=2):
        """初始化GSMArena爬虫"""
        self.base_url = "https://www.gsmarena.com"
        self.request_delay = request_delay
        self.session = requests.Session()
        
        # 随机User-Agent池
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'

        ]
        
        self._update_session_headers()
        self.driver = None
        self._init_driver()
        
        # 已知设备映射
        self.known_mappings = {
            'CPH1931': 'oppo_a5_(2020)-9883.php',
            'CPH2387': 'oppo_a57_4g-11565.php',
            'V2111': 'vivo_y21-11063.php',
            'CPH2471': 'oppo_a96-11827.php',
            'CPH2269': 'oppo_reno7-11534.php',
            'SM-A245F': 'samsung_galaxy_a24-12421.php',
            'SM-G991B': 'samsung_galaxy_s21-10626.php'
        }
    
    def _get_random_user_agent(self):
        return random.choice(self.user_agents)
    
    def _update_session_headers(self):
        self.session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
    
    def _init_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')

            chrome_options.add_argument('--incognito')  # 无痕模式
           

            chrome_options.add_argument(f'--user-agent={self._get_random_user_agent()}')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--keep-alive-for-test')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(60)
            logger.info("GSMArena WebDriver初始化成功")
        except Exception as e:
            logger.error(f"GSMArena WebDriver初始化失败: {str(e)}")
            self.driver = None
    
    def _random_delay(self):
        delay = random.uniform(self.request_delay * 0.8, self.request_delay * 1.5)
        time.sleep(delay)
        self._update_session_headers()
    
    def extract_device_info_from_url(self, gsmarena_url):
        """从GSMArena URL直接提取设备信息"""
        try:
            logger.info(f"📄 提取GSMArena设备信息: {gsmarena_url}")
            
            self._random_delay()
            
            response = self.session.get(gsmarena_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            device_info = self._parse_device_page(soup, gsmarena_url)
            
            if device_info:
                logger.info(f"✅ 成功提取设备信息: {device_info['name']}")
                return {
                    'success': True,
                    'source': 'gsmarena_direct',
                    'data': device_info
                }
            else:
                logger.warning(f"❌ 无法解析设备信息: {gsmarena_url}")
                return {
                    'success': False,
                    'message': '无法解析设备信息'
                }
                
        except Exception as e:
            logger.error(f"提取GSMArena设备信息失败: {str(e)}")
            return {
                'success': False,
                'message': f'提取失败: {str(e)}'
            }
    
    def search_device_by_model(self, model_code):
        if not self._check_driver_health():
            logger.warning("WebDriver连接失效，正在重新初始化...")
            self._init_driver()
        """通过型号在GSMArena搜索设备"""
        if not self.driver:
            logger.error("WebDriver未初始化")
            return None
        
        try:
            # 检查已知映射
            if model_code in self.known_mappings:
                direct_url = f"{self.base_url}/{self.known_mappings[model_code]}"
                logger.info(f"使用已知映射: {model_code} -> {direct_url}")
                return self.extract_device_info_from_url(direct_url)
            
            encoded_model = quote_plus(model_code)
            search_url = f"{self.base_url}/res.php3?sSearch={encoded_model}"
            
            logger.info(f"🔍 GSMArena搜索: {model_code}")
            
            self._random_delay()
            
            self.driver.get(search_url)
            wait = WebDriverWait(self.driver, 30)
            
            try:
                # 等待解密内容
                decrypted_element = wait.until(
                    EC.presence_of_element_located((By.ID, "decrypted"))
                )
                
                wait.until(lambda d: decrypted_element.get_attribute('innerHTML').strip() != '')
                time.sleep(random.uniform(1.5, 3.0))
                
                decrypted_content = decrypted_element.get_attribute('innerHTML')
                if not decrypted_content or decrypted_content.strip() == '':
                    logger.warning(f"GSMArena解密内容为空: {model_code}")
                    return None
                
                soup = BeautifulSoup(decrypted_content, 'html.parser')
                
                # 查找设备链接
                device_links, is_closest_match = self._find_device_links(soup)
                
                if not device_links:
                    logger.warning(f"GSMArena未找到设备链接: {model_code}")
                    return None
                
                # 选择最佳匹配
                best_device = self._find_best_match(device_links, model_code)
                
                if best_device:
                    device_url = best_device.get('href')
                    if not device_url.startswith('http'):
                        device_url = urljoin(self.base_url, device_url)
                    
                    result = self.extract_device_info_from_url(device_url)
                    if result and result['success']:
                        # 添加最接近匹配标记
                        result['data']['is_closest_match'] = is_closest_match
                        return result
                
                return None
                
            except TimeoutException:
                logger.warning(f"GSMArena搜索超时: {model_code}")
                return None
                
        except Exception as e:
            logger.error(f"GSMArena搜索失败 {model_code}: {str(e)}")
            return None
        
    def _check_driver_health(self):
        """检查WebDriver是否健康"""
        if not self.driver:
            return False
        
        try:
            # 尝试获取当前窗口句柄来检查session是否有效
            self.driver.current_window_handle
            return True
        except Exception as e:
            logger.warning(f"WebDriver健康检查失败: {str(e)}")
            return False
        
    def _reinit_driver(self):
        """重新初始化WebDriver"""
        try:
            # 关闭旧的driver
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            
            # 重新初始化
            self._init_driver()
            
            if self.driver:
                logger.info("WebDriver重新初始化成功")
                return True
            else:
                logger.error("WebDriver重新初始化失败")
                return False
                
        except Exception as e:
            logger.error(f"WebDriver重新初始化异常: {str(e)}")
            return False
    
    def search_device_by_name(self, device_name):
        
        if not self._check_driver_health():
            logger.warning("WebDriver连接失效，正在重新初始化...")
            self._init_driver()

        """通过设备名称在GSMArena搜索"""
        if not self.driver:
            logger.error("WebDriver未初始化")
            return None
        
        try:
            encoded_name = quote_plus(device_name)
            search_url = f"{self.base_url}/res.php3?sSearch={encoded_name}"
            
            logger.info(f"🔍 GSMArena按名称搜索: {device_name}")
            
            self._random_delay()
            
            self.driver.get(search_url)
            wait = WebDriverWait(self.driver, 30)
            
            try:
                decrypted_element = wait.until(
                    EC.presence_of_element_located((By.ID, "decrypted"))
                )
                
                wait.until(lambda d: decrypted_element.get_attribute('innerHTML').strip() != '')
                time.sleep(random.uniform(1.5, 3.0))
                
                decrypted_content = decrypted_element.get_attribute('innerHTML')
                if not decrypted_content:
                    return None
                
                soup = BeautifulSoup(decrypted_content, 'html.parser')
                device_links, is_closest_match = self._find_device_links(soup)
                
                if device_links:
                    best_device = self._find_best_match(device_links, device_name)
                    if best_device:
                        device_url = best_device.get('href')
                        if not device_url.startswith('http'):
                            device_url = urljoin(self.base_url, device_url)
                        
                        result = self.extract_device_info_from_url(device_url)
                        if result and result['success']:
                            # 添加最接近匹配标记
                            result['data']['is_closest_match'] = is_closest_match
                            return result
                
                return None
                
            except TimeoutException:
                logger.warning(f"GSMArena按名称搜索超时: {device_name}")
                return None
                
        except Exception as e:
            logger.error(f"GSMArena按名称搜索失败 {device_name}: {str(e)}")
            return None
    
    def _find_device_links(self, soup):
        """查找设备链接并检测是否是最接近匹配"""
        device_links = []
        is_closest_match = False
        
        # 检查是否有"closest matches"提示
        closest_match_div = soup.find('div', class_='no-results')
        if closest_match_div and 'closest matches' in closest_match_div.get_text():
            is_closest_match = True
            logger.warning("⚠️ GSMArena显示最接近匹配结果")
        
        # 方法1: 查找makers div
        makers_div = soup.find('div', class_='makers')
        if makers_div:
            device_links = makers_div.find_all('a', href=True)
        
        # 方法2: 查找所有.php链接
        if not device_links:
            all_links = soup.find_all('a', href=True)
            device_links = [link for link in all_links if '.php' in link.get('href', '')]
        
        return device_links, is_closest_match
    
    def _find_best_match(self, device_links, target_name):
        """找到最佳匹配的设备"""
        if not device_links:
            return None
        
        # 简单策略：返回第一个，但可以根据需要优化
        best_match = device_links[0]
        
        # 可以在这里添加更复杂的匹配逻辑
        # 比如计算名称相似度等
        
        return best_match
    
    def _parse_device_page(self, soup, source_url):
        """解析设备详情页面"""
        try:
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
                'source_url': source_url,
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
                        
                        # 提取关键信息
                        for i, cell_text in enumerate(cell_texts):
                            if 'Announced' in cell_text and i + 1 < len(cell_texts):
                                announced_info = cell_texts[i + 1]
                                device_info['announced_date'] = announced_info
                                
                                # 处理发布日期
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
            
            # 记录关键信息
            logger.info(f"设备名称: {device_info['name']}")
            logger.info(f"发布日期: {device_info['announced_date']}")
            logger.info(f"价格: {device_info['price']}")
            
            return device_info
            
        except Exception as e:
            logger.error(f"解析设备页面失败: {str(e)}")
            return None
    
    def close(self):
        """关闭WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("GSMArena WebDriver已关闭")