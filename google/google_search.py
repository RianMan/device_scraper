#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google搜索模块 - google/google_search.py
负责通过Google搜索查找GSMArena链接
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from urllib.parse import quote_plus, urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger(__name__)

class GoogleSearcher:
    def __init__(self, request_delay=2):
        """初始化Google搜索器"""
        self.request_delay = request_delay
        self.session = requests.Session()
        
        # 随机User-Agent池
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        self._update_session_headers()
        self.driver = None
        self._init_driver()
    
    def _get_random_user_agent(self):
        """获取随机User-Agent"""
        return random.choice(self.user_agents)
    
    def _update_session_headers(self):
        """更新请求头"""
        self.session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'DNT': '1',
        })
    
    def _init_driver(self):
        """初始化Selenium WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'--user-agent={self._get_random_user_agent()}')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(30)
            logger.info("Google搜索WebDriver初始化成功")
        except Exception as e:
            logger.error(f"WebDriver初始化失败: {str(e)}")
            self.driver = None
    
    def _random_delay(self):
        """随机延迟"""
        delay = random.uniform(self.request_delay * 0.8, self.request_delay * 1.5)
        time.sleep(delay)
    
    def search_gsmarena_links(self, model_code):
        """通过Google搜索查找GSMArena链接"""
        try:
            # 构建搜索查询
            search_query = f"{model_code} site:gsmarena.com"
            encoded_query = quote_plus(search_query)
            google_url = f"https://www.google.com/search?q={encoded_query}"
            
            logger.info(f"🔍 Google搜索: {search_query}")
            
            if not self.driver:
                logger.error("WebDriver未初始化")
                return []
            
            # 添加随机延迟
            self._random_delay()
            
            # 访问Google搜索页面
            self.driver.get(google_url)
            
            # 等待搜索结果加载
            wait = WebDriverWait(self.driver, 15)
            try:
                # 等待搜索结果容器
                search_container = wait.until(
                    EC.presence_of_element_located((By.ID, "search"))
                )
                
                # 等待结果列表
                results_container = wait.until(
                    EC.presence_of_element_located((By.ID, "rso"))
                )
                
                time.sleep(2)  # 确保页面完全加载
                
            except TimeoutException:
                logger.warning(f"Google搜索页面加载超时: {model_code}")
                return []
            
            # 解析搜索结果
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            gsmarena_links = self._extract_gsmarena_links(soup, model_code)
            
            return gsmarena_links
            
        except Exception as e:
            logger.error(f"Google搜索失败 {model_code}: {str(e)}")
            return []
    
    def _extract_gsmarena_links(self, soup, model_code):
        """从Google搜索结果中提取GSMArena链接"""
        gsmarena_links = []
        
        try:
            # 查找搜索结果容器
            search_div = soup.find('div', {'id': 'search'})
            if not search_div:
                logger.warning(f"未找到Google搜索结果容器: {model_code}")
                return []
            
            # 查找结果列表容器
            rso_div = search_div.find('div', {'id': 'rso'})
            if not rso_div:
                logger.warning(f"未找到Google结果列表: {model_code}")
                return []
            
            # 查找所有结果项
            result_items = rso_div.find_all('div', class_='MjjYud')
            logger.info(f"找到 {len(result_items)} 个Google搜索结果")
            
            for i, item in enumerate(result_items):
                try:
                    # 查找链接
                    link_element = item.find('a', href=True)
                    if not link_element:
                        continue
                    
                    href = link_element.get('href', '')
                    
                    # 检查是否是GSMArena链接
                    if 'gsmarena.com' in href and href.startswith('http'):
                        # 提取标题
                        title_element = link_element.find('h3')
                        title = title_element.get_text(strip=True) if title_element else ''
                        
                        # 提取描述
                        description = ''
                        desc_div = item.find('div', class_='VwiC3b')
                        if desc_div:
                            description = desc_div.get_text(strip=True)
                        
                        gsmarena_link = {
                            'url': href,
                            'title': title,
                            'description': description,
                            'rank': i + 1
                        }
                        
                        gsmarena_links.append(gsmarena_link)
                        logger.info(f"✅ 找到GSMArena链接 #{i+1}: {title}")
                        
                except Exception as e:
                    logger.warning(f"解析搜索结果项失败: {str(e)}")
                    continue
            
            if gsmarena_links:
                logger.info(f"🎯 Google搜索找到 {len(gsmarena_links)} 个GSMArena链接")
            else:
                logger.warning(f"❌ Google搜索未找到GSMArena链接: {model_code}")
            
            return gsmarena_links
            
        except Exception as e:
            logger.error(f"提取GSMArena链接失败: {str(e)}")
            return []
    
    def search_general_info(self, model_code):
        """通用Google搜索（不限制site）"""
        try:
            search_query = model_code
            encoded_query = quote_plus(search_query)
            google_url = f"https://www.google.com/search?q={encoded_query}"
            
            logger.info(f"🔍 Google通用搜索: {search_query}")
            
            if not self.driver:
                logger.error("WebDriver未初始化")
                return []
            
            self._random_delay()
            
            self.driver.get(google_url)
            
            wait = WebDriverWait(self.driver, 15)
            try:
                search_container = wait.until(
                    EC.presence_of_element_located((By.ID, "search"))
                )
                time.sleep(2)
                
            except TimeoutException:
                logger.warning(f"通用搜索页面加载超时: {model_code}")
                return []
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 提取所有相关链接（包括GSMArena和其他站点）
            all_links = self._extract_all_relevant_links(soup, model_code)
            
            return all_links
            
        except Exception as e:
            logger.error(f"通用Google搜索失败 {model_code}: {str(e)}")
            return []
    
    def _extract_all_relevant_links(self, soup, model_code):
        """提取所有相关链接"""
        relevant_links = []
        
        try:
            search_div = soup.find('div', {'id': 'search'})
            if not search_div:
                return []
            
            rso_div = search_div.find('div', {'id': 'rso'})
            if not rso_div:
                return []
            
            result_items = rso_div.find_all('div', class_='MjjYud')
            
            for i, item in enumerate(result_items):
                try:
                    link_element = item.find('a', href=True)
                    if not link_element:
                        continue
                    
                    href = link_element.get('href', '')
                    if not href.startswith('http'):
                        continue
                    
                    title_element = link_element.find('h3')
                    title = title_element.get_text(strip=True) if title_element else ''
                    
                    # 识别站点类型
                    site_type = 'other'
                    if 'gsmarena.com' in href:
                        site_type = 'gsmarena'
                    elif 'gsmchoice.com' in href:
                        site_type = 'gsmchoice'
                    elif any(word in href.lower() for word in ['phone', 'mobile', 'spec', 'review']):
                        site_type = 'mobile_related'
                    
                    link_info = {
                        'url': href,
                        'title': title,
                        'site_type': site_type,
                        'rank': i + 1
                    }
                    
                    relevant_links.append(link_info)
                    
                except Exception as e:
                    continue
            
            logger.info(f"通用搜索找到 {len(relevant_links)} 个相关链接")
            return relevant_links
            
        except Exception as e:
            logger.error(f"提取相关链接失败: {str(e)}")
            return []
    
    def close(self):
        """关闭WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("Google搜索WebDriver已关闭")