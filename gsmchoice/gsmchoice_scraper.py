#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GSMChoice爬虫模块 - gsmchoice/gsmchoice_scraper.py
负责从GSMChoice网站获取设备名称
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import random
import logging
from urllib.parse import quote_plus, urljoin
import re

logger = logging.getLogger(__name__)

class GSMChoiceScraper:
    def __init__(self, request_delay=2):
        """初始化GSMChoice爬虫"""
        self.base_url = "https://www.gsmchoice.com"
        self.search_api = "https://www.gsmchoice.com/js/searchy.xhtml"
        self.request_delay = request_delay
        self.session = requests.Session()
        
        # 随机User-Agent池
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        self._update_session_headers()
    
    def _get_random_user_agent(self):
        return random.choice(self.user_agents)
    
    def _update_session_headers(self):
        self.session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.gsmchoice.com/en/',
            'X-Requested-With': 'XMLHttpRequest'
        })
    
    def _random_delay(self):
        delay = random.uniform(self.request_delay * 0.8, self.request_delay * 1.5)
        time.sleep(delay)
    
    def search_device_name(self, model_code, brand_hint=None):
        """搜索设备名称和发布日期"""
        try:
            # 构建搜索查询
            search_query = model_code
            
            logger.info(f"🔍 GSMChoice搜索设备信息: {search_query}")
            
            # 方法1: API搜索
            api_result = self._search_via_api(search_query)
            if api_result:
                # API搜索成功，但只有设备名称，需要获取详细信息
                device_info = self._get_device_details_by_name(api_result)
                if device_info:
                    return {
                        'success': True,
                        'device_name': device_info['name'],
                        'announced_date': device_info.get('announced_date', ''),
                        'source': 'gsmchoice_api'
                    }
            
            # 方法2: 网页搜索
            web_result = self._search_via_web(search_query)
            if web_result:
                return {
                    'success': True,
                    'device_name': web_result['name'],
                    'announced_date': web_result.get('announced_date', ''),
                    'source': 'gsmchoice_web'
                }
            
            logger.warning(f"❌ GSMChoice未找到设备: {model_code}")
            return {
                'success': False,
                'message': f'未找到设备: {model_code}'
            }
            
        except Exception as e:
            logger.error(f"GSMChoice搜索失败 {model_code}: {str(e)}")
            return {
                'success': False,
                'message': f'搜索失败: {str(e)}'
            }
    
    def _get_device_details_by_name(self, device_name):
        """通过设备名称获取详细信息"""
        try:
            # encoded_name = quote_plus(device_name)
            # search_url = f"{self.base_url}/en/search/?sSearch4={encoded_name}"
            search_url = f"{self.base_url}/en/catalogue/{device_name}/"
            return self._extract_device_name_from_page(search_url)
            # print(search_url, "search_urlsearch_url")
            # self._random_delay()
            
            # response = self.session.get(search_url, timeout=30)
            # response.raise_for_status()
            
            # soup = BeautifulSoup(response.content, 'html.parser')
            
            # # 查找设备链接
            # device_links = soup.find_all('a', href=re.compile(r'/en/catalogue/.*\.php'))
            
            # if device_links:
            #     first_link = device_links[0]
            #     detail_url = urljoin(self.base_url, first_link.get('href', ''))
                
            #     return self._extract_device_name_from_page(detail_url)
            
            # return None
            
        except Exception as e:
            logger.warning(f"获取设备详情失败: {str(e)}")
            return None
    
    def _search_via_api(self, search_query):
        """通过API搜索设备"""
        try:
            encoded_query = quote_plus(search_query)
            search_url = f"{self.search_api}?search={encoded_query}&lang=en&v=3"
            
            self._random_delay()
            
            response = self.session.get(search_url, timeout=30)
            
            response.raise_for_status()
            
            try:
                results = response.json()
            except json.JSONDecodeError:
                logger.warning(f"GSMChoice API返回非JSON响应: {search_query}")
                return None
            
            if not results or len(results) == 0:
                logger.warning(f"GSMChoice API无搜索结果: {search_query}")
                return None
            
            # 取第一个结果的设备名称
            first_result = results[0]
            # device_name = first_result.get('model', '').strip()
            smodel = first_result.get('smodel', '').strip()
            sbrand = first_result.get('sbrand', '').strip()
            device_name = sbrand + '/' + smodel
            if device_name and device_name != 'Unknown':
                logger.info(f"✅ GSMChoice API找到设备: {device_name}")
                return device_name
            
            return None
            
        except Exception as e:
            logger.warning(f"GSMChoice API搜索失败: {str(e)}")
            return None
    
    def _search_via_web(self, search_query):
        """通过网页搜索设备"""
        try:
            encoded_query = quote_plus(search_query)
            search_url = f"{self.base_url}/en/search/?sSearch4={encoded_query}"
            
            self._random_delay()
            
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找设备链接
            device_links = soup.find_all('a', href=re.compile(r'/en/catalogue/.*\.php'))
            
            if not device_links:
                logger.warning(f"GSMChoice网页搜索无结果: {search_query}")
                return None
            
            # 访问第一个设备页面获取完整信息
            first_link = device_links[0]
            detail_url = urljoin(self.base_url, first_link.get('href', ''))
            
            device_info = self._extract_device_name_from_page(detail_url)
            
            if device_info and device_info['name']:
                logger.info(f"✅ GSMChoice网页找到设备: {device_info['name']}")
                return device_info
            
            return None
            
        except Exception as e:
            logger.warning(f"GSMChoice网页搜索失败: {str(e)}")
            return None
    
    def _extract_device_name_from_page(self, detail_url):
        """从设备详情页提取设备名称和发布日期"""
        try:
            self._random_delay()
            
            response = self.session.get(detail_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            device_info = {
                'name': None,
                'announced_date': None
            }
            
            # 查找设备名称 - 优先使用PhoneModelName div中的infoline__title
            phone_model_div = soup.find('div', {'id': 'PhoneModelName'})
            if phone_model_div:
                title_element = phone_model_div.find('h1', class_='infoline__title')
                if title_element:
                    title_span = title_element.find('span')
                    if title_span:
                        device_name = title_span.get_text(strip=True)
                        if device_name:
                            device_info['name'] = device_name
            
            # 备用方案：查找页面title标签
            if not device_info['name']:
                title_tag = soup.find('title')
                if title_tag:
                    title_text = title_tag.get_text(strip=True)
                    if title_text:
                        device_name = title_text.split(' - ')[0].split(' | ')[0]
                        device_info['name'] = device_name.strip()
            
            # 提取发布日期
            announced_date = self._extract_announced_date(soup)
            if announced_date:
                device_info['announced_date'] = announced_date
            
            return device_info
            
        except Exception as e:
            logger.warning(f"提取设备信息失败: {str(e)}")
            return None
    
    def _extract_announced_date(self, soup):
        """从GSMChoice页面提取发布日期"""
        try:
            # 查找规格表格中的Announced字段
            spec_table = soup.find('table', class_='PhoneData')
            if spec_table:
                rows = spec_table.find_all('tr')
                for row in rows:
                    th = row.find('th', class_='phoneCategoryName')
                    td = row.find('td', class_='phoneCategoryValue')
                    
                    if th and td:
                        key = th.get_text(strip=True)
                        if 'Announced' in key:
                            value_span = td.find('span')
                            if value_span:
                                announced_date = value_span.get_text(strip=True)
                                logger.info(f"✅ GSMChoice找到发布日期: {announced_date}")
                                return announced_date
            
            return None
            
        except Exception as e:
            logger.warning(f"提取发布日期失败: {str(e)}")
            return None
    
    def get_device_specifications(self, device_name):
        """获取设备规格信息（可选功能）"""
        try:
            logger.info(f"🔍 获取GSMChoice设备规格: {device_name}")
            
            # 通过设备名称搜索
            encoded_name = quote_plus(device_name)
            search_url = f"{self.base_url}/en/search/?sSearch4={encoded_name}"
            
            self._random_delay()
            
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找设备链接
            device_links = soup.find_all('a', href=re.compile(r'/en/catalogue/.*\.php'))
            
            if device_links:
                detail_url = urljoin(self.base_url, device_links[0].get('href', ''))
                return self._extract_specifications_from_page(detail_url)
            
            return {}
            
        except Exception as e:
            logger.warning(f"获取GSMChoice规格失败: {str(e)}")
            return {}
    
    def _extract_specifications_from_page(self, detail_url):
        """从详情页提取规格信息"""
        try:
            self._random_delay()
            
            response = self.session.get(detail_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            specifications = {}
            
            # 查找规格表格
            spec_table = soup.find('table', class_='PhoneData')
            if spec_table:
                rows = spec_table.find_all('tr')
                for row in rows:
                    th = row.find('th', class_='phoneCategoryName')
                    td = row.find('td', class_='phoneCategoryValue')
                    
                    if th and td:
                        key = th.get_text(strip=True)
                        value = td.get_text(strip=True)
                        
                        if key and value:
                            specifications[key] = value
            
            logger.info(f"✅ 提取了 {len(specifications)} 个规格项")
            return specifications
            
        except Exception as e:
            logger.warning(f"提取规格信息失败: {str(e)}")
            return {}
    
    def infer_brand_from_model(self, model_code):
        """从型号推断品牌"""
        model_lower = model_code.lower()
        
        brand_patterns = {
            'samsung': [r'^sm-', r'galaxy'],
            'motorola': [r'^moto', r'motorola'],
            'zte': [r'^zte'],
            'lg': [r'^lm-'],
            'huawei': [r'^alt-', r'huawei'],
            'xiaomi': [r'^mi ', r'redmi'],
            'oppo': [r'^cph'],
            'vivo': [r'^v\d+'],
            'hisense': [r'hisense'],
            'tecno': [r'tecno'],
            'cubot': [r'kingkong'],
            'ulefone': [r'tank'],
        }
        
        for brand, patterns in brand_patterns.items():
            for pattern in patterns:
                if re.search(pattern, model_lower):
                    return brand.capitalize()
        
        return 'Unknown'
    
    def close(self):
        """关闭连接（GSMChoice主要使用requests，无需特殊关闭）"""
        logger.info("GSMChoice爬虫已关闭")