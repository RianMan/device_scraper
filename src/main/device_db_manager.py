import pandas as pd
import pymongo
from pymongo import MongoClient
import json
import logging
import time
from datetime import datetime
import re
from app import DeviceInfoScraper
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeviceDBManager:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="device_info"):
        """
        初始化数据库管理器
        """
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self.collection = None
        self.scraper = DeviceInfoScraper()
        
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
            # 读取CSV文件
            df = pd.read_csv(csv_file)
            logger.info(f"成功读取CSV文件: {csv_file}, 共 {len(df)} 行数据")
            
            # 提取设备信息
            devices = []
            for index, row in df.iterrows():
                # 解析clientmanufacture和clientmodel
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
    
    def scrape_and_store_device(self, device_info):
        """爬取单个设备信息并存储到数据库"""
        model_code = device_info['model_code']
        
        try:
            # 检查是否已存在
            existing = self.collection.find_one({"model_code": model_code})
            if existing:
                logger.info(f"设备 {model_code} 已存在，跳过")
                return True
            
            # 爬取设备信息
            logger.info(f"正在爬取设备信息: {model_code}")
            result = self.scraper.get_device_info(model_code)
            
            if result['success']:
                data = result['data']
                
                # 构建要存储的文档
                device_doc = {
                    "model_code": model_code,
                    "device_name": data['device_name'],
                    "announced_date": data['announced_date'],
                    "release_date": data['release_date'],
                    "price": data['price'],  # 直接存储原始价格字符串
                    "manufacture": device_info['manufacture'],
                    "source_url": data['source_url'],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                    "specifications": data['specifications']  # 完整规格信息
                }
                
                # 插入数据库
                self.collection.insert_one(device_doc)
                logger.info(f"✅ 成功存储设备: {model_code} - {data['device_name']}")
                logger.info(f"   价格: {data['price']}")
                return True
                
            else:
                logger.warning(f"❌ 未找到设备信息: {model_code} - {result['message']}")
                return False
                
        except Exception as e:
            logger.error(f"处理设备 {model_code} 时出错: {str(e)}")
            return False
    
    def batch_process_devices(self, csv_file="device_result.csv", delay=2):
        """批量处理设备信息"""
        # 读取CSV数据
        devices = self.read_csv_data(csv_file)
        
        if not devices:
            logger.error("没有读取到设备数据")
            return
        
        # 统计信息
        total_count = len(devices)
        success_count = 0
        failed_devices = []
        
        logger.info(f"开始批量处理 {total_count} 个设备...")
        
        for i, device in enumerate(devices, 1):
            logger.info(f"进度: {i}/{total_count} - 处理设备: {device['model_code']}")
            
            success = self.scrape_and_store_device(device)
            
            if success:
                success_count += 1
            else:
                failed_devices.append(device)
            
            # 添加延迟避免过于频繁的请求
            if i < total_count:  # 最后一个不需要延迟
                time.sleep(delay)
        
        # 保存失败的设备信息
        self.save_failed_devices(failed_devices)
        
        # 输出统计结果
        logger.info(f"批量处理完成!")
        logger.info(f"总数: {total_count}")
        logger.info(f"成功: {success_count}")
        logger.info(f"失败: {len(failed_devices)}")
        logger.info(f"成功率: {success_count/total_count*100:.1f}%")
    
    def save_failed_devices(self, failed_devices):
        """保存查询失败的设备信息"""
        if not failed_devices:
            logger.info("没有失败的设备需要保存")
            return
        
        # 保存为CSV
        failed_df = pd.DataFrame(failed_devices)
        csv_filename = f"failed_devices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        failed_df.to_csv(csv_filename, index=False)
        
        # 保存为JSON
        json_filename = f"failed_devices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(failed_devices, f, ensure_ascii=False, indent=2)
        
        logger.info(f"失败设备信息已保存:")
        logger.info(f"CSV文件: {csv_filename}")
        logger.info(f"JSON文件: {json_filename}")
    
    def query_device(self, model_code):
        """查询单个设备信息"""
        try:
            device = self.collection.find_one({"model_code": model_code})
            if device:
                # 移除MongoDB的_id字段
                device.pop('_id', None)
                return device
            else:
                return None
        except Exception as e:
            logger.error(f"查询设备失败: {str(e)}")
            return None
    
    def get_all_devices(self, limit=None):
        """获取所有设备信息"""
        try:
            query = self.collection.find({})
            if limit:
                query = query.limit(limit)
            
            devices = []
            for device in query:
                device.pop('_id', None)  # 移除MongoDB的_id字段
                devices.append(device)
            
            return devices
        except Exception as e:
            logger.error(f"获取设备列表失败: {str(e)}")
            return []
    
    def get_stats(self):
        """获取数据库统计信息"""
        try:
            total_count = self.collection.count_documents({})
            with_price = self.collection.count_documents({"price": {"$ne": ""}})
            with_date = self.collection.count_documents({"announced_date": {"$ne": ""}})
            
            stats = {
                "total_devices": total_count,
                "devices_with_price": with_price,
                "devices_with_date": with_date,
                "price_coverage": f"{with_price/total_count*100:.1f}%" if total_count > 0 else "0%",
                "date_coverage": f"{with_date/total_count*100:.1f}%" if total_count > 0 else "0%"
            }
            
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {}
    
    def close(self):
        """关闭数据库连接"""
        if self.scraper:
            self.scraper.close()
        if self.client:
            self.client.close()
            logger.info("数据库连接已关闭")

def main():
    """主函数"""
    # 检查CSV文件是否存在
    csv_file = "device_result.csv"
    if not os.path.exists(csv_file):
        logger.error(f"CSV文件不存在: {csv_file}")
        logger.info("请确保CSV文件存在并包含 'clientmanufacture' 和 'clientmodel' 列")
        return
    
    # 初始化数据库管理器
    try:
        db_manager = DeviceDBManager()
    except Exception as e:
        logger.error(f"初始化数据库管理器失败: {str(e)}")
        logger.info("请确保MongoDB服务已启动")
        return
    
    try:
        # 开始批量处理
        db_manager.batch_process_devices(csv_file, delay=3)  # 3秒延迟
        
        # 输出统计信息
        stats = db_manager.get_stats()
        logger.info("数据库统计信息:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
    finally:
        # 关闭连接
        db_manager.close()

if __name__ == "__main__":
    main()