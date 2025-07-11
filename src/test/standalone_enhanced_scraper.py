#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立的增强版GSMChoice爬虫 - 包含测试代码
"""

import requests
from bs4 import BeautifulSoup
import json
import logging
import time
from datetime import datetime
import os
import re
from urllib.parse import quote_plus
import sys

# 尝试导入Selenium（可选）
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
    print("✅ Selenium可用")
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️  Selenium不可用，将使用requests模式")

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedGSMChoiceScraper:
    def __init__(self, request_delay=3, use_selenium=True):
        """初始化增强的GSMChoice爬虫"""
        self.base_url = "https://www.gsmchoice.com"
        self.search_api = "https://www.gsmchoice.com/js/searchy.xhtml"
        self.request_delay = request_delay
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        
        # 初始化requests session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.gsmchoice.com/en/',
        })
        
        # 初始化Selenium WebDriver（如果可用且需要）
        self.driver = None
        if self.use_selenium:
            self._init_driver()
        else:
            logger.info("使用requests模式（无JavaScript支持）")
    
    def _init_driver(self):
        """初始化Selenium WebDriver"""
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium不可用，跳过WebDriver初始化")
            return
            
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
            self.use_selenium = False
    
    def search_device(self, manufacture, model):
        """搜索设备（先用API，失败则用网页搜索）"""
        # 方法1：尝试搜索API
        api_result = self._search_via_api(manufacture, model)
        if api_result:
            return api_result
        
        # 方法2：网页搜索
        logger.info("API搜索失败，尝试网页搜索...")
        return self._search_via_web(manufacture, model)
    
    def _search_via_api(self, manufacture, model):
        """通过API搜索设备"""
        try:
            search_query = f"{manufacture} {model}"
            encoded_query = quote_plus(search_query)
            
            search_url = f"{self.search_api}?search={encoded_query}&lang=en&v=3"
            logger.info(f"🔍 API搜索设备: {search_query}")
            
            time.sleep(self.request_delay)
            
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            try:
                results = response.json()
            except json.JSONDecodeError:
                logger.warning(f"无法解析JSON响应: {manufacture} {model}")
                return None
            
            if not results or len(results) == 0:
                logger.warning(f"API未找到搜索结果: {manufacture} {model}")
                return None
            
            first_result = results[0]
            logger.info(f"✅ API找到设备: {first_result.get('brand', '')} {first_result.get('model', '')}")
            return first_result
            
        except Exception as e:
            logger.error(f"❌ API搜索失败 {manufacture} {model}: {str(e)}")
            return None
    
    def _search_via_web(self, manufacture, model):
        """通过网页搜索设备"""
        try:
            search_query = f"{manufacture} {model}"
            encoded_query = quote_plus(search_query)
            
            search_url = f"{self.base_url}/en/search/?sSearch4={encoded_query}"
            logger.info(f"🌐 网页搜索设备: {search_query}")
            
            time.sleep(self.request_delay)
            
            if self.driver:
                # 使用Selenium
                self.driver.get(search_url)
                time.sleep(3)  # 等待页面加载
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            else:
                # 使用requests
                response = self.session.get(search_url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找搜索结果
            device_links = soup.find_all('a', href=re.compile(r'/en/catalogue/.*/.*/'))
            
            if not device_links:
                logger.warning(f"网页搜索未找到结果: {manufacture} {model}")
                return None
            
            # 取第一个结果并构造设备信息
            first_link = device_links[0]
            href = first_link.get('href', '')
            
            # 从URL中提取sbrand和smodel
            url_parts = href.strip('/').split('/')
            if len(url_parts) >= 4:
                sbrand = url_parts[-2]
                smodel = url_parts[-1]
                
                device_info = {
                    'brand': manufacture,
                    'model': model,
                    'sbrand': sbrand,
                    'smodel': smodel
                }
                
                logger.info(f"✅ 网页搜索找到: {sbrand}/{smodel}")
                return device_info
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 网页搜索失败 {manufacture} {model}: {str(e)}")
            return None
    
    def get_device_details(self, device_info):
        """获取设备详细信息（支持Selenium）"""
        try:
            sbrand = device_info.get('sbrand', '')
            smodel = device_info.get('smodel', '')
            
            if not sbrand or not smodel:
                logger.warning("缺少sbrand或smodel信息")
                return None
            
            detail_url = f"{self.base_url}/en/catalogue/{sbrand}/{smodel}/"
            logger.info(f"📄 获取详情页: {detail_url}")
            
            time.sleep(self.request_delay)
            
            if self.driver:
                # 使用Selenium获取页面
                logger.info("使用Selenium加载页面...")
                self.driver.get(detail_url)
                
                # 等待页面基础内容加载
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.CLASS_NAME, "PhoneData")),
                            EC.presence_of_element_located((By.TAG_NAME, "table"))
                        )
                    )
                    logger.info("✅ 页面基础内容已加载")
                except TimeoutException:
                    logger.warning("⚠️ 页面基础内容加载超时")
                
                # 额外等待JavaScript执行
                time.sleep(5)
                
                # 尝试等待价格组件加载
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "scard-widget-prices__container"))
                    )
                    logger.info("✅ 价格容器已加载")
                except TimeoutException:
                    logger.warning("⚠️ 价格容器加载超时，继续处理...")
                
                # 尝试滚动页面触发懒加载
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            else:
                # 使用requests
                logger.info("使用requests获取页面...")
                response = self.session.get(detail_url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
            
            # 保存调试HTML
            debug_filename = f'{sbrand}_{smodel}_enhanced_soup.html'
            with open(debug_filename, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            logger.info(f"📁 调试HTML已保存: {debug_filename}")
            
            # 提取设备信息
            device_details = {
                'device_name': device_info.get('model', 'Unknown'),
                'brand': device_info.get('brand', ''),
                'announced_date': '',
                'price': '',
                'specifications': {},
                'source_url': detail_url
            }
            
            # 更新设备名称（从页面提取）
            title_element = soup.find('h1', class_='infoline__title')
            if title_element:
                title_span = title_element.find('span')
                if title_span:
                    device_details['device_name'] = title_span.get_text(strip=True)
                    logger.info(f"📱 设备名称: {device_details['device_name']}")
            
            # 提取规格信息
            self._extract_specifications(soup, device_details)
            
            # 增强的价格提取
            self._extract_price_enhanced(soup, device_details)
            
            return device_details
            
        except Exception as e:
            logger.error(f"❌ 获取设备详情失败: {str(e)}")
            return None
    
    def _extract_specifications(self, soup, device_details):
        """提取规格信息"""
        try:
            specs_count = 0
            
            # 查找规格表格
            spec_table = soup.find('table', class_='PhoneData')
            if not spec_table:
                # 尝试其他可能的表格
                spec_tables = soup.find_all('table', {'cellspacing': '0'})
                if spec_tables:
                    spec_table = spec_tables[0]
            
            if spec_table:
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
                            logger.info(f"📅 发布日期: {value}")
                        
                        # 存储到规格字典
                        if key and value:
                            device_details['specifications'][key] = value
                            specs_count += 1
            
            # 如果没找到PhoneData表格，尝试查找其他规格容器
            if specs_count == 0:
                spec_containers = soup.find_all(['div', 'section'], class_=re.compile(r'spec|phone|data', re.I))
                logger.info(f"尝试从 {len(spec_containers)} 个容器中提取规格...")
                
                for container in spec_containers:
                    # 在容器中查找键值对
                    items = container.find_all(['tr', 'li', 'div'])
                    for item in items:
                        text = item.get_text(strip=True)
                        if ':' in text and len(text) < 200:  # 避免太长的文本
                            parts = text.split(':', 1)
                            if len(parts) == 2:
                                key, value = parts[0].strip(), parts[1].strip()
                                if key and value and len(key) < 50:
                                    device_details['specifications'][key] = value
                                    specs_count += 1
            
            logger.info(f"📋 提取了 {specs_count} 个规格项")
            
        except Exception as e:
            logger.error(f"❌ 提取规格信息失败: {str(e)}")
    
    def _extract_price_enhanced(self, soup, device_details):
        """增强的价格提取"""
        try:
            price_found = False
            
            # 方法1：查找Amazon价格按钮和链接
            amazon_elements = soup.find_all(['a', 'button'], class_=re.compile(r'amazon|price', re.I))
            logger.info(f"💰 找到 {len(amazon_elements)} 个价格相关元素")
            
            for element in amazon_elements:
                href = element.get('href', '')
                text = element.get_text(strip=True)
                
                # 跳过明显的配件链接
                accessory_keywords = ['Handyhülle', 'Schutzfolien', 'Powerbank', 'Kopfhörer', 'USB-Adapter', 'Speicherkarte', 'kaufen']
                if any(keyword.lower() in text.lower() for keyword in accessory_keywords):
                    continue
                
                # 查找价格模式
                price_patterns = [
                    r'(\d+[.,]\d+)\s*(€|EUR)',
                    r'€\s*(\d+[.,]\d+)',
                    r'(\d+)\s*(€|EUR)',
                    r'USD\s*(\d+[.,]\d+)',
                    r'\$(\d+[.,]\d+)'
                ]
                
                for pattern in price_patterns:
                    match = re.search(pattern, text)
                    if match:
                        price_value = match.group(1)
                        currency = match.group(2) if len(match.groups()) > 1 else '€'
                        device_details['price'] = f"{price_value} {currency}"
                        price_found = True
                        logger.info(f"💰 从元素找到价格: {device_details['price']}")
                        break
                
                if price_found:
                    break
            
            # 方法2：查找价格容器
            if not price_found:
                price_containers = soup.find_all(['div', 'span', 'p'], class_=re.compile(r'price|cost|scard-widget', re.I))
                logger.info(f"🔍 检查 {len(price_containers)} 个价格容器")
                
                for container in price_containers:
                    price_text = container.get_text(strip=True)
                    price_match = re.search(r'(\d+[.,]\d+|\d+)\s*(€|EUR|Dollar|\$)', price_text)
                    if price_match:
                        device_details['price'] = price_match.group(0)
                        price_found = True
                        logger.info(f"💰 从价格容器找到价格: {device_details['price']}")
                        break
            
            # 方法3：从JavaScript中查找价格信息
            if not price_found:
                scripts = soup.find_all('script')
                logger.info(f"🔍 检查 {len(scripts)} 个脚本标签")
                
                for script in scripts:
                    if script.string:
                        # 查找价格相关的JavaScript变量
                        price_patterns = [
                            r'price["\']?\s*[:=]\s*["\']?(\d+[.,]\d+|\d+)\s*(€|EUR|Dollar|\$)?["\']?',
                            r'amazonKartaWidget.*?(\d+[.,]\d+)',
                            r'cost["\']?\s*[:=]\s*["\']?(\d+[.,]\d+)'
                        ]
                        
                        for pattern in price_patterns:
                            match = re.search(pattern, script.string, re.IGNORECASE)
                            if match:
                                price_value = match.group(1)
                                currency = match.group(2) if len(match.groups()) > 1 and match.group(2) else '€'
                                device_details['price'] = f"{price_value} {currency}"
                                price_found = True
                                logger.info(f"💰 从JavaScript找到价格: {device_details['price']}")
                                break
                        
                        if price_found:
                            break
            
            # 方法4：查找任何包含价格模式的文本（最后尝试）
            if not price_found:
                all_text = soup.get_text()
                price_patterns = [
                    r'(\d+[.,]\d+)\s*€',
                    r'€\s*(\d+[.,]\d+)',
                    r'(\d+[.,]\d+)\s*EUR',
                    r'USD\s*(\d+[.,]\d+)',
                    r'\$(\d+[.,]\d+)'
                ]
                
                for pattern in price_patterns:
                    matches = re.findall(pattern, all_text)
                    if matches:
                        # 取第一个合理的价格（通常在30-5000范围内）
                        for match in matches:
                            try:
                                price_num = float(match.replace(',', '.'))
                                if 30 <= price_num <= 5000:
                                    device_details['price'] = f"{match} €"
                                    price_found = True
                                    logger.info(f"💰 从页面文本找到价格: {device_details['price']}")
                                    break
                            except ValueError:
                                continue
                    if price_found:
                        break
            
            # 设置默认值
            if not price_found:
                # 检查是否有购买链接
                amazon_links = soup.find_all('a', href=re.compile(r'amazon', re.I))
                if amazon_links:
                    device_details['price'] = "Available on Amazon"
                    logger.info("🛒 未找到具体价格，但有Amazon购买链接")
                else:
                    device_details['price'] = "Price not available"
                    logger.warning("❌ 未找到任何价格信息")
            
        except Exception as e:
            logger.error(f"❌ 提取价格信息失败: {str(e)}")
            device_details['price'] = "Price extraction failed"
    
    def get_device_info(self, manufacture, model):
        """获取完整设备信息"""
        try:
            search_result = self.search_device(manufacture, model)
            if not search_result:
                return {
                    'success': False,
                    'message': f'未找到设备 {manufacture} {model}'
                }
            
            device_details = self.get_device_details(search_result)
            if not device_details:
                return {
                    'success': False,
                    'message': f'无法获取设备详情 {manufacture} {model}'
                }
            
            return {
                'success': True,
                'source': 'gsmchoice_enhanced',
                'data': device_details
            }
            
        except Exception as e:
            logger.error(f"❌ 获取设备信息失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取设备信息时发生错误: {str(e)}'
            }
    
    def close(self):
        """关闭WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("🔒 WebDriver已关闭")

def test_enhanced_scraper():
    """测试增强的爬虫"""
    print("🔧 增强版GSMChoice爬虫测试")
    print("=" * 60)
    
    # 检查Selenium可用性
    if SELENIUM_AVAILABLE:
        print("✅ Selenium可用，将使用完整功能")
        use_selenium = True
    else:
        print("⚠️ Selenium不可用，将使用基础模式")
        use_selenium = False
    
    scraper = EnhancedGSMChoiceScraper(request_delay=2, use_selenium=use_selenium)
    
    try:
        # 测试用例
        test_cases = [
            ("lge", "LG-M430"),
            ("Lanix", "Alpha 1R"),
            ("motorola", "moto g play - 2023"),
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
                    important_keys = ['Display', 'Processor', 'Standard battery', 'Operating system', 'Dimensions', 'Weight']
                    for key in important_keys:
                        if key in specs:
                            print(f"   {key}: {specs[key]}")
                else:
                    print(f"❌ 失败: {result['message']}")
                    
            except Exception as e:
                print(f"❌ 异常: {str(e)}")
                import traceback
                traceback.print_exc()
        
        print(f"\n🔚 测试完成")
        
    finally:
        scraper.close()

if __name__ == "__main__":
    test_enhanced_scraper()