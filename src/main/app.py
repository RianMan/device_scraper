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

app = Flask(__name__)
CORS(app)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeviceInfoScraper:
    def __init__(self):
        self.base_url = "https://www.gsmarena.com"
        self.session = requests.Session()
        # 设置更真实的请求头
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
        
        # 初始化Selenium WebDriver
        self.driver = None
        self._init_driver()
    
    def _init_driver(self):
        """初始化Chrome WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无头模式
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
    
    def search_device(self, model_code):
        """根据型号代码搜索设备（使用Selenium处理JavaScript加密内容）"""
        if not self.driver:
            logger.error("WebDriver未初始化，尝试备用方案")
            return self.try_direct_access(model_code)
            
        try:
            search_url = f"{self.base_url}/res.php3?sSearch={model_code}"
            logger.info(f"搜索设备: {search_url}")
            
            # 使用Selenium访问页面
            self.driver.get(search_url)
            
            # 等待JavaScript解密内容
            wait = WebDriverWait(self.driver, 15)
            
            # 等待decrypted div有内容
            try:
                decrypted_element = wait.until(
                    EC.presence_of_element_located((By.ID, "decrypted"))
                )
                
                # 再等待一下确保内容完全加载
                time.sleep(2)
                
                # 检查是否有实际内容
                decrypted_content = decrypted_element.get_attribute('innerHTML')
                if not decrypted_content or decrypted_content.strip() == '':
                    logger.warning(f"解密内容为空: {model_code}")
                    return self.try_direct_access(model_code)
                
                logger.info(f"成功获取解密内容，长度: {len(decrypted_content)}")
                
                # 解析解密后的HTML内容
                soup = BeautifulSoup(decrypted_content, 'html.parser')
                
                # 查找设备链接
                device_links = []
                
                # 方法1: 查找makers div
                makers_div = soup.find('div', class_='makers')
                if makers_div:
                    device_links = makers_div.find_all('a', href=True)
                    logger.info(f"在makers div中找到 {len(device_links)} 个设备链接")
                
                # 方法2: 查找所有包含.php的链接
                if not device_links:
                    all_links = soup.find_all('a', href=True)
                    device_links = [link for link in all_links if '.php' in link.get('href', '')]
                    logger.info(f"在所有链接中找到 {len(device_links)} 个设备链接")
                
                if not device_links:
                    logger.warning(f"未找到设备链接: {model_code}")
                    return self.try_direct_access(model_code)
                
                # 获取第一个设备的详细页面链接
                first_device = device_links[0]
                device_url = first_device.get('href')
                
                if device_url:
                    # 获取设备名称
                    device_name = first_device.get_text(strip=True)
                    if not device_name:
                        span_tag = first_device.find('span')
                        if span_tag:
                            device_name = span_tag.get_text(strip=True)
                        else:
                            device_name = "Unknown"
                    
                    # 确保URL是完整的
                    if not device_url.startswith('http'):
                        full_url = urljoin(self.base_url, device_url)
                    else:
                        full_url = device_url
                    
                    logger.info(f"找到设备: {device_name} - {full_url}")
                    
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
    
    def extract_device_details(self, device_url):
        """提取设备详细信息"""
        try:
            logger.info(f"获取设备详情: {device_url}")
            
            response = self.session.get(device_url, timeout=10)
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
                        # 获取所有单元格的文本
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        
                        # 查找关键字段
                        for i, cell_text in enumerate(cell_texts):
                            # 发布日期 - 查找包含日期信息的单元格
                            if 'Announced' in cell_text and i + 1 < len(cell_texts):
                                announced_info = cell_texts[i + 1]
                                device_info['announced_date'] = announced_info
                                
                                # 从Announced字段中提取发布日期
                                if 'Released' in announced_info:
                                    # 格式：2019, September 21. Released 2019, October
                                    parts = announced_info.split('Released')
                                    if len(parts) > 1:
                                        device_info['release_date'] = f"Released {parts[1].strip()}"
                                    announced_part = parts[0].replace('.', '').strip()
                                    device_info['announced_date'] = announced_part
                                
                            # 状态信息
                            elif 'Status' in cell_text and i + 1 < len(cell_texts):
                                status_info = cell_texts[i + 1]
                                if not device_info['release_date']:  # 如果还没有从Announced字段获取到
                                    device_info['release_date'] = status_info
                                
                            # 价格信息
                            elif 'Price' in cell_text and i + 1 < len(cell_texts):
                                price_info = cell_texts[i + 1]
                                device_info['price'] = price_info
                                
                            # 型号信息
                            elif 'Models' in cell_text and i + 1 < len(cell_texts):
                                models_info = cell_texts[i + 1]
                                device_info['model_code'] = models_info
                        
                        # 存储所有规格到specifications字典
                        if len(cell_texts) >= 2:
                            # 使用第一个非空的单元格作为键，最后一个作为值
                            key = next((text for text in cell_texts if text), '')
                            value = cell_texts[-1]
                            
                            if key and value and key != value:
                                device_info['specifications'][key] = value
            
            # 后处理：如果某些字段仍为空，尝试从specifications中提取
            if not device_info['announced_date']:
                for key, value in device_info['specifications'].items():
                    if 'announced' in key.lower() or 'year' in key.lower():
                        device_info['announced_date'] = value
                        break
            
            if not device_info['price']:
                for key, value in device_info['specifications'].items():
                    if 'price' in key.lower():
                        device_info['price'] = value
                        break
            
            if not device_info['model_code']:
                for key, value in device_info['specifications'].items():
                    if 'model' in key.lower():
                        device_info['model_code'] = value
                        break
            
            logger.info(f"设备信息提取完成: {device_name}")
            logger.info(f"发布日期: {device_info['announced_date']}")
            logger.info(f"上市日期: {device_info['release_date']}")
            logger.info(f"价格: {device_info['price']}")
            logger.info(f"型号: {device_info['model_code']}")
            
            return device_info
            
        except Exception as e:
            logger.error(f"提取设备详情失败: {str(e)}")
            return None
    
    def try_direct_access(self, model_code):
        """尝试根据已知映射直接访问设备页面"""
        # 已知的一些型号映射
        known_mappings = {
            'CPH1931': 'oppo_a5_(2020)-9883.php',
            'CPH2387': 'oppo_a57_4g-11565.php',
            'V2111': 'vivo_y21-11063.php',
            'CPH2471': 'oppo_a96-11827.php',
            'CPH2269': 'oppo_reno7-11534.php'
        }
        
        if model_code in known_mappings:
            full_url = f"{self.base_url}/{known_mappings[model_code]}"
            logger.info(f"使用直接映射: {model_code} -> {full_url}")
            return {
                'name': 'Unknown',
                'url': full_url,
                'relative_url': known_mappings[model_code]
            }
        
        return None
    
    def get_device_info(self, model_code):
        """获取完整的设备信息"""
        try:
            # 搜索设备
            search_result = self.search_device(model_code)
            if not search_result:
                return {
                    'success': False,
                    'message': f'未找到型号 {model_code} 的设备信息'
                }
            
            # 获取详细信息
            device_details = self.extract_device_details(search_result['url'])
            if not device_details:
                return {
                    'success': False,
                    'message': f'无法获取设备 {search_result["name"]} 的详细信息'
                }
            
            # 合并信息
            result = {
                'success': True,
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

# 创建爬虫实例
scraper = DeviceInfoScraper()

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
        
        # 获取设备信息
        result = scraper.get_device_info(model_code)
        
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

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'message': '设备信息爬取服务运行正常'
    })

@app.route('/')
def index():
    """首页"""
    return '''
    <h1>设备信息爬取服务</h1>
    <p>API接口：POST http://172.16.29.227:8080/api/device-info</p>
    <p>请求格式：{"model_code": "CPH1931"}</p>
    <p>健康检查：GET http://172.16.29.227:8080/api/health</p>
    <p>前端页面：请使用独立的 index.html 文件</p>
    '''

if __name__ == '__main__':
    try:
        print("启动设备信息爬取服务...")
        print("API接口: http://172.16.29.227:8080/api/device-info")
        print("健康检查: http://172.16.29.227:8080/api/health")
        print("局域网访问: 同局域网设备可通过以上地址访问")
        app.run(debug=True, host='0.0.0.0', port=8080)
    finally:
        # 确保在应用退出时关闭WebDriver
        scraper.close()
    
    def search_device(self, model_code):
        """根据型号代码搜索设备"""
        try:
            search_url = f"{self.base_url}/res.php3?sSearch={model_code}"
            logger.info(f"搜索设备: {search_url}")
            
            # 添加更多的请求头和延迟
            time.sleep(1)  # 添加延迟避免被封
            
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 调试：打印页面内容的一部分
            logger.info(f"页面标题: {soup.title.string if soup.title else 'No title'}")
            
            # 尝试多种方式查找设备列表
            device_links = []
            
            # 方法1: 查找makers div
            makers_div = soup.find('div', class_='makers')
            if makers_div:
                device_links = makers_div.find_all('a', href=True)
                logger.info(f"方法1找到 {len(device_links)} 个设备链接")
            
            # 方法2: 查找所有包含.php的链接
            if not device_links:
                all_links = soup.find_all('a', href=True)
                device_links = [link for link in all_links if '.php' in link.get('href', '') and 'oppo' in link.get('href', '').lower()]
                logger.info(f"方法2找到 {len(device_links)} 个设备链接")
            
            # 方法3: 直接查找review-body或specs相关的链接
            if not device_links:
                review_div = soup.find('div', {'id': 'review-body'})
                if review_div:
                    device_links = review_div.find_all('a', href=True)
                    logger.info(f"方法3找到 {len(device_links)} 个设备链接")
            
            # 方法4: 查找li标签中的链接
            if not device_links:
                li_tags = soup.find_all('li')
                for li in li_tags:
                    link = li.find('a', href=True)
                    if link and '.php' in link.get('href', ''):
                        device_links.append(link)
                logger.info(f"方法4找到 {len(device_links)} 个设备链接")
            
            if not device_links:
                logger.warning(f"未找到设备链接: {model_code}")
                # 调试：保存HTML到文件
                with open(f'debug_{model_code}.html', 'w', encoding='utf-8') as f:
                    f.write(str(soup.prettify()))
                logger.info(f"HTML已保存到 debug_{model_code}.html")
                return None
            
            # 获取第一个设备的详细页面链接
            first_device = device_links[0]
            device_url = first_device.get('href')
            
            if device_url:
                # 获取设备名称
                device_name = first_device.get_text(strip=True)
                if not device_name:
                    span_tag = first_device.find('span')
                    if span_tag:
                        device_name = span_tag.get_text(strip=True)
                    else:
                        device_name = "Unknown"
                
                # 确保URL是完整的
                if not device_url.startswith('http'):
                    full_url = urljoin(self.base_url, device_url)
                else:
                    full_url = device_url
                
                logger.info(f"找到设备: {device_name} - {full_url}")
                
                return {
                    'name': device_name,
                    'url': full_url,
                    'relative_url': device_url
                }
            
            return None
            
        except Exception as e:
            logger.error(f"搜索设备失败: {str(e)}")
            return None
    
    def extract_device_details(self, device_url):
        """提取设备详细信息"""
        try:
            logger.info(f"获取设备详情: {device_url}")
            
            response = self.session.get(device_url)
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
                        key = cells[0].get_text(strip=True) if cells[0].get_text(strip=True) else cells[1].get_text(strip=True)
                        value = cells[-1].get_text(strip=True)
                        
                        # 提取关键信息
                        if 'Announced' in key:
                            device_info['announced_date'] = value
                        elif 'Status' in key:
                            device_info['release_date'] = value
                        elif 'Price' in key:
                            device_info['price'] = value
                        elif 'Models' in key:
                            device_info['model_code'] = value
                        
                        # 存储所有规格
                        device_info['specifications'][key] = value
            
            logger.info(f"设备信息提取完成: {device_name}")
            return device_info
            
        except Exception as e:
            logger.error(f"提取设备详情失败: {str(e)}")
            return None
    
    def get_device_info(self, model_code):
        """获取完整的设备信息"""
        try:
            # 搜索设备
            search_result = self.search_device(model_code)
            if not search_result:
                # 备用方案：尝试根据已知的型号映射直接访问
                direct_url = self.try_direct_access(model_code)
                if direct_url:
                    search_result = {
                        'name': 'Unknown',
                        'url': direct_url,
                        'relative_url': direct_url.replace(self.base_url, '')
                    }
                else:
                    return {
                        'success': False,
                        'message': f'未找到型号 {model_code} 的设备信息'
                    }
            
            # 获取详细信息
            device_details = self.extract_device_details(search_result['url'])
            if not device_details:
                return {
                    'success': False,
                    'message': f'无法获取设备 {search_result["name"]} 的详细信息'
                }
            
            # 合并信息
            result = {
                'success': True,
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
    
    def try_direct_access(self, model_code):
        """尝试根据已知映射直接访问设备页面"""
        # 已知的一些型号映射
        known_mappings = {
            'CPH1931': 'oppo_a5_(2020)-9883.php',
            'CPH2387': 'oppo_a57_4g-11565.php',
            'V2111': 'vivo_y21-11063.php',
            'CPH2471': 'oppo_a96-11827.php',
            'CPH2269': 'oppo_reno7-11534.php'
        }
        
        if model_code in known_mappings:
            return f"{self.base_url}/{known_mappings[model_code]}"
        
        return None

# 创建爬虫实例
scraper = DeviceInfoScraper()

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
        
        # 获取设备信息
        result = scraper.get_device_info(model_code)
        
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

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'message': '设备信息爬取服务运行正常'
    })

@app.route('/')
def index():
    """首页"""
    return '''
    <h1>设备信息爬取服务</h1>
    <p>API接口：POST /api/device-info</p>
    <p>请求格式：{"model_code": "CPH2387"}</p>
    <p>健康检查：GET /api/health</p>
    '''

if __name__ == '__main__':
    print("启动设备信息爬取服务...")
    print("API接口: http://localhost:8080/api/device-info")
    print("健康检查: http://localhost:8080/api/health")
    app.run(debug=True, host='0.0.0.0', port=8080)