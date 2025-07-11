#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的GSMChoice网站爬虫 - 支持JavaScript和价格提取
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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedGSMChoiceScraper:
    def __init__(self, request_delay=3, use_selenium=True):
        """初始化增强的GSMChoice爬虫"""
        self.base_url = "https://www.gsmchoice.com"
        self.search_api = "https://www.gsmchoice.com/js/searchy.xhtml"
        self.request_delay = request_delay
        self.use_selenium = use_selenium
        
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
        
        # 初始化Selenium WebDriver（如果需要）
        self.driver = None
        if self.use_selenium:
            self._init_driver()
    
    def _init_driver(self):
        """初始化Selenium WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            logger.info("Selenium WebDriver初始化成功")
        except Exception as e:
            logger.error(f"WebDriver初始化失败: {str(e)}")
            self.driver = None
    
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
            logger.info(f"API搜索设备: {search_query}")
            
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
            logger.info(f"API找到设备: {first_result.get('brand', '')} {first_result.get('model', '')}")
            return first_result
            
        except Exception as e:
            logger.error(f"API搜索失败 {manufacture} {model}: {str(e)}")
            return None
    
    def _search_via_web(self, manufacture, model):
        """通过网页搜索设备"""
        try:
            search_query = f"{manufacture} {model}"
            encoded_query = quote_plus(search_query)
            
            search_url = f"{self.base_url}/en/search/?sSearch4={encoded_query}"
            logger.info(f"网页搜索设备: {search_query}")
            
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
            device_links = soup.find_all('a', href=re.compile(r'/en/catalogue/.*\.php'))
            
            if not device_links:
                logger.warning(f"网页搜索未找到结果: {manufacture} {model}")
                return None
            
            # 取第一个结果并构造设备信息
            first_link = device_links[0]
            href = first_link.get('href', '')
            
            # 从URL中提取sbrand和smodel
            url_parts = href.split('/')
            if len(url_parts) >= 4:
                sbrand = url_parts[-2]
                smodel = url_parts[-1].replace('.php', '')
                
                device_info = {
                    'brand': manufacture,
                    'model': model,
                    'sbrand': sbrand,
                    'smodel': smodel
                }
                
                logger.info(f"网页搜索找到: {sbrand}/{smodel}")
                return device_info
            
            return None
            
        except Exception as e:
            logger.error(f"网页搜索失败 {manufacture} {model}: {str(e)}")
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
            logger.info(f"获取详情页: {detail_url}")
            
            time.sleep(self.request_delay)
            
            if self.driver:
                # 使用Selenium获取页面
                self.driver.get(detail_url)
                
                # 等待页面完全加载
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "PhoneData"))
                )
                
                # 额外等待JavaScript执行
                time.sleep(5)
                
                # 尝试等待价格组件加载
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "scard-widget-prices__container"))
                    )
                    logger.info("价格容器已加载")
                except TimeoutException:
                    logger.warning("价格容器加载超时")
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            else:
                # 使用requests
                response = self.session.get(detail_url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
            
            # 保存调试HTML
            debug_filename = f'{sbrand}_{smodel}_enhanced_soup.html'
            with open(debug_filename, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            logger.info(f"调试HTML已保存: {debug_filename}")
            
            # 提取设备信息
            device_details = {
                'device_name': device_info.get('model', 'Unknown'),
                'brand': device_info.get('brand', ''),
                'announced_date': '',
                'price': '',
                'specifications': {},
                'source_url': detail_url
            }
            
            # 提取规格信息
            self._extract_specifications(soup, device_details)
            
            # 增强的价格提取
            self._extract_price_enhanced(soup, device_details)
            
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
                # 尝试其他可能的表格
                spec_table = soup.find('table', {'cellspacing': '0'})
            
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
    
    def _extract_price_enhanced(self, soup, device_details):
        """增强的价格提取"""
        try:
            price_found = False
            
            # 方法1：查找Amazon价格按钮
            amazon_buttons = soup.find_all('a', class_=re.compile(r'amazon-button'))
            for button in amazon_buttons:
                # 检查是否是购买链接而不是配件链接
                href = button.get('href', '')
                text = button.get_text(strip=True)
                
                # 跳过配件相关的链接
                accessory_keywords = ['Handyhülle', 'Schutzfolien', 'Powerbank', 'Kopfhörer', 'USB-Adapter', 'Speicherkarte']
                if any(keyword in text for keyword in accessory_keywords):
                    continue
                
                # 如果是设备购买链接，尝试从URL中提取价格信息
                if 'search' in href and len(text) > 5:
                    # 有时候按钮文本包含价格
                    price_match = re.search(r'(\d+[.,]\d+|\d+)\s*(€|EUR|Dollar|\$)', text)
                    if price_match:
                        device_details['price'] = price_match.group(0)
                        price_found = True
                        logger.info(f"从Amazon按钮找到价格: {device_details['price']}")
                        break
            
            # 方法2：查找价格容器和脚本
            if not price_found:
                price_containers = soup.find_all('div', class_=re.compile(r'price'))
                for container in price_containers:
                    price_text = container.get_text(strip=True)
                    price_match = re.search(r'(\d+[.,]\d+|\d+)\s*(€|EUR|Dollar|\$)', price_text)
                    if price_match:
                        device_details['price'] = price_match.group(0)
                        price_found = True
                        logger.info(f"从价格容器找到价格: {device_details['price']}")
                        break
            
            # 方法3：从JavaScript中查找价格信息
            if not price_found:
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string:
                        # 查找价格相关的JavaScript变量
                        price_match = re.search(r'price["\']?\s*[:=]\s*["\']?(\d+[.,]\d+|\d+)\s*(€|EUR|Dollar|\$)?["\']?', script.string, re.IGNORECASE)
                        if price_match:
                            price_value = price_match.group(1)
                            currency = price_match.group(2) or '€'
                            device_details['price'] = f"{price_value} {currency}"
                            price_found = True
                            logger.info(f"从JavaScript找到价格: {device_details['price']}")
                            break
            
            # 方法4：查找任何包含价格模式的文本
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
                        # 取第一个合理的价格（通常在50-5000范围内）
                        for match in matches:
                            price_num = float(match.replace(',', '.'))
                            if 50 <= price_num <= 5000:
                                device_details['price'] = f"{match} €"
                                price_found = True
                                logger.info(f"从页面文本找到价格: {device_details['price']}")
                                break
                    if price_found:
                        break
            
            if not price_found:
                # 如果找到Amazon购买链接，至少标记为"Available on Amazon"
                if amazon_buttons:
                    device_details['price'] = "Available on Amazon"
                    logger.info("未找到具体价格，但有Amazon购买链接")
                else:
                    device_details['price'] = "Price not available"
                    logger.warning("未找到任何价格信息")
            
        except Exception as e:
            logger.error(f"提取价格信息失败: {str(e)}")
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

# 测试代码
def test_enhanced_scraper():
    """测试增强的爬虫"""
    scraper = EnhancedGSMChoiceScraper(request_delay=2, use_selenium=True)
    
    try:
        # 测试Blackview BV4900 Pro
        result = scraper.get_device_info("Blackview", "BV4900 Pro")
        
        if result['success']:
            data = result['data']
            print("✅ 成功获取设备信息:")
            print(f"设备名称: {data['device_name']}")
            print(f"品牌: {data['brand']}")
            print(f"发布日期: {data['announced_date']}")
            print(f"价格: {data['price']}")
            print(f"规格数量: {len(data['specifications'])}")
            print(f"来源: {data['source_url']}")
        else:
            print(f"❌ 失败: {result['message']}")
            
    finally:
        scraper.close()

if __name__ == "__main__":
    test_enhanced_scraper()