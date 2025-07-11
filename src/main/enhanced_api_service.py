import requests
from bs4 import BeautifulSoup
import re
import json
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeviceInfoService:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="device_info"):
        """初始化设备信息服务"""
        self.base_url = "https://www.gsmarena.com"
        self.session = requests.Session()
        
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
        
        # 初始化数据库连接
        self.mongo_client = None
        self.db = None
        self.collection = None
        self._init_mongodb(mongo_uri, db_name)
        
        # 初始化Selenium WebDriver
        self.driver = None
        self._init_driver()
    
    def _init_mongodb(self, mongo_uri, db_name):
        """初始化MongoDB连接"""
        try:
            self.mongo_client = MongoClient(mongo_uri)
            self.db = self.mongo_client[db_name]
            self.collection = self.db['devices']
            logger.info(f"MongoDB连接成功: {db_name}")
        except Exception as e:
            logger.warning(f"MongoDB连接失败: {str(e)}, 将只使用爬虫模式")
    
    def _init_driver(self):
        """初始化Chrome WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            logger.info("Selenium WebDriver 初始化成功")
        except Exception as e:
            logger.error(f"初始化WebDriver失败: {str(e)}")
            self.driver = None
    
    def query_from_database(self, model_code):
        """从数据库查询设备信息"""
        if not self.collection:
            return None
        
        try:
            device = self.collection.find_one({"model_code": model_code})
            if device:
                # 转换为API格式
                result = {
                    'success': True,
                    'source': 'database',
                    'data': {
                        'search_model': model_code,
                        'device_name': device.get('device_name', ''),
                        'model_code': device.get('model_code', ''),
                        'announced_date': device.get('announced_date', ''),
                        'release_date': device.get('release_date', ''),
                        'price': device.get('price', ''),  # 直接返回原始价格
                        'source_url': device.get('source_url', ''),
                        'created_at': device.get('created_at', ''),
                        'specifications': device.get('specifications', {})
                    }
                }
                logger.info(f"从数据库找到设备信息: {model_code}")
                return result
            else:
                logger.info(f"数据库中未找到设备: {model_code}")
                return None
        except Exception as e:
            logger.error(f"数据库查询失败: {str(e)}")
            return None
    
    def search_device(self, model_code):
        """搜索设备（Selenium方式）"""
        if not self.driver:
            logger.error("WebDriver未初始化，尝试备用方案")
            return self.try_direct_access(model_code)
            
        try:
            search_url = f"{self.base_url}/res.php3?sSearch={model_code}"
            logger.info(f"搜索设备: {search_url}")
            
            self.driver.get(search_url)
            wait = WebDriverWait(self.driver, 15)
            
            try:
                decrypted_element = wait.until(
                    EC.presence_of_element_located((By.ID, "decrypted"))
                )
                time.sleep(2)
                
                decrypted_content = decrypted_element.get_attribute('innerHTML')
                if not decrypted_content or decrypted_content.strip() == '':
                    logger.warning(f"解密内容为空: {model_code}")
                    return self.try_direct_access(model_code)
                
                soup = BeautifulSoup(decrypted_content, 'html.parser')
                device_links = []
                
                makers_div = soup.find('div', class_='makers')
                if makers_div:
                    device_links = makers_div.find_all('a', href=True)
                
                if not device_links:
                    all_links = soup.find_all('a', href=True)
                    device_links = [link for link in all_links if '.php' in link.get('href', '')]
                
                if not device_links:
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
            logger.error(f"搜索设备失败: {str(e)}")
            return self.try_direct_access(model_code)
    
    def try_direct_access(self, model_code):
        """直接访问已知设备"""
        known_mappings = {
            'CPH1931': 'oppo_a5_(2020)-9883.php',
            'CPH2387': 'oppo_a57_4g-11565.php',
            'V2111': 'vivo_y21-11063.php',
            'CPH2471': 'oppo_a96-11827.php',
            'CPH2269': 'oppo_reno7-11534.php'
        }
        
        if model_code in known_mappings:
            full_url = f"{self.base_url}/{known_mappings[model_code]}"
            return {
                'name': 'Unknown',
                'url': full_url,
                'relative_url': known_mappings[model_code]
            }
        return None
    
    def extract_device_details(self, device_url):
        """提取设备详细信息"""
        try:
            response = self.session.get(device_url, timeout=10)
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
        """获取设备信息（优先从数据库查询）"""
        # 1. 首先尝试从数据库查询
        db_result = self.query_from_database(model_code)
        if db_result:
            return db_result
        
        # 2. 数据库中没有，使用爬虫
        logger.info(f"数据库中未找到 {model_code}，开始爬虫获取")
        
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
        """关闭连接"""
        if self.driver:
            self.driver.quit()
        if self.mongo_client:
            self.mongo_client.close()

# 创建服务实例
device_service = DeviceInfoService()

@app.route('/api/device-info', methods=['POST'])
def get_device_info():
    """API接口：获取设备信息"""
    try:
        data = request.get_json()
        if not data or 'model_code' not in data:
            return jsonify({
                'success': False,
                'message': '请提供model_code参数'
            }), 400
        
        model_code = data['model_code'].strip()
        if not model_code:
            return jsonify({
                'success': False,
                'message': 'model_code不能为空'
            }), 400
        
        result = device_service.get_device_info(model_code)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"API请求失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/database-stats', methods=['GET'])
def get_database_stats():
    """获取数据库统计信息"""
    try:
        if not device_service.collection:
            return jsonify({
                'success': False,
                'message': '数据库未连接'
            }), 500
        
        total_count = device_service.collection.count_documents({})
        with_price = device_service.collection.count_documents({"price": {"$ne": ""}})
        with_date = device_service.collection.count_documents({"announced_date": {"$ne": ""}})
        
        stats = {
            "success": True,
            "data": {
                "total_devices": total_count,
                "devices_with_price": with_price,
                "devices_with_date": with_date,
                "price_coverage": f"{with_price/total_count*100:.1f}%" if total_count > 0 else "0%",
                "date_coverage": f"{with_date/total_count*100:.1f}%" if total_count > 0 else "0%"
            }
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取统计信息失败: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'message': '设备信息服务运行正常',
        'database_connected': device_service.collection is not None,
        'webdriver_status': device_service.driver is not None
    })

@app.route('/')
def index():
    """首页"""
    return '''
    <h1>设备信息服务</h1>
    <p>API接口：POST http://172.16.29.227:8080/api/device-info</p>
    <p>数据库统计：GET http://172.16.29.227:8080/api/database-stats</p>
    <p>健康检查：GET http://172.16.29.227:8080/api/health</p>
    '''