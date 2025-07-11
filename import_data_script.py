# -*- coding: utf-8 -*-
"""
独立的数据导入脚本 - 避免Flask路由冲突
"""

import pandas as pd
import pymongo
from pymongo import MongoClient
import json
import logging
import time
from datetime import datetime
import os
import sys

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入爬虫模块（只导入爬虫类，不导入Flask应用）
from device_scraper_core import DeviceInfoScraper

class DataImporter:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="device_info", max_workers=5):
        """初始化数据导入器"""
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.max_workers = max_workers
        self.client = None
        self.db = None
        self.collection = None
        
        # 初始化爬虫（支持多线程，5秒间隔）
        self.scraper = DeviceInfoScraper(max_workers=max_workers, timeout=60, request_delay=5)
        
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
    
    def normalize_model_code(self, model_code):
        """标准化设备型号代码，用于数据库匹配"""
        # 移除多余的空格并标准化
        normalized = ' '.join(model_code.strip().split())
        return normalized
    
    def filter_existing_devices(self, devices):
        """过滤掉数据库中已存在的设备（考虑型号标准化）"""
        existing_codes = set()
        try:
            # 获取数据库中已存在的型号
            cursor = self.collection.find({}, {"model_code": 1})
            for doc in cursor:
                # 标准化已存在的型号代码
                normalized_code = self.normalize_model_code(doc["model_code"])
                existing_codes.add(normalized_code)
            
            logger.info(f"数据库中已存在 {len(existing_codes)} 个设备")
        except Exception as e:
            logger.warning(f"查询已存在设备失败: {str(e)}")
        
        # 过滤新设备
        new_devices = []
        for device in devices:
            normalized_code = self.normalize_model_code(device['model_code'])
            if normalized_code not in existing_codes:
                new_devices.append(device)
            else:
                logger.info(f"设备已存在，跳过: {device['model_code']} (标准化: {normalized_code})")
        
        logger.info(f"需要处理的新设备: {len(new_devices)} 个")
        return new_devices
    
    def store_device_batch(self, scrape_results):
        """批量存储设备信息到数据库"""
        success_count = 0
        error_count = 0
        
        for result_data in scrape_results:
            try:
                device_info = result_data['device_info']
                scrape_result = result_data['scrape_result']
                data = scrape_result['data']
                
                # 构建要存储的文档
                device_doc = {
                    "model_code": device_info['model_code'],
                    "device_name": data['device_name'],
                    "announced_date": data['announced_date'],
                    "release_date": data['release_date'],
                    "price": data['price'],  # 直接存储原始价格字符串
                    "manufacture": data['manufacture'],
                    "source_url": data['source_url'],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                    "specifications": data['specifications']  # 完整规格信息
                }
                
                # 插入数据库
                self.collection.insert_one(device_doc)
                success_count += 1
                
            except Exception as e:
                logger.error(f"存储设备 {device_info['model_code']} 失败: {str(e)}")
                error_count += 1
        
        logger.info(f"批量存储完成: 成功 {success_count}, 失败 {error_count}")
        return success_count, error_count
    
    def progress_callback(self, completed, total, success, failed):
        """进度回调函数"""
        progress = completed / total * 100
        print(f"\r🔄 进度: {completed}/{total} ({progress:.1f}%) | 成功: {success} | 失败: {failed}", end='', flush=True)
    
    def batch_process_devices(self, csv_file="device_result.csv"):
        """批量并行处理设备信息"""
        # 读取CSV数据
        devices = self.read_csv_data(csv_file)
        
        if not devices:
            logger.error("没有读取到设备数据")
            return
        
        # 过滤已存在的设备
        new_devices = self.filter_existing_devices(devices)
        
        if not new_devices:
            logger.info("所有设备都已存在于数据库中")
            return
        
        logger.info(f"开始并行处理 {len(new_devices)} 个新设备，线程数: {self.max_workers}")
        
        # 并行爬取设备信息
        scrape_results, failed_devices = self.scraper.batch_get_device_info(
            new_devices, 
            progress_callback=self.progress_callback
        )
        
        print()  # 换行
        
        # 批量存储成功的结果
        if scrape_results:
            store_success, store_error = self.store_device_batch(scrape_results)
        else:
            store_success, store_error = 0, 0
        
        # 保存失败的设备信息
        self.save_failed_devices(failed_devices)
        
        # 输出统计结果
        total_count = len(new_devices)
        logger.info(f"批量处理完成!")
        logger.info(f"总数: {total_count}")
        logger.info(f"爬取成功: {len(scrape_results)}")
        logger.info(f"存储成功: {store_success}")
        logger.info(f"爬取失败: {len(failed_devices)}")
        logger.info(f"成功率: {len(scrape_results)/total_count*100:.1f}%")
    
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
        """关闭连接"""
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
    
    # 初始化数据导入器（5个并发线程，5秒间隔）
    try:
        importer = DataImporter(max_workers=5)
    except Exception as e:
        logger.error(f"初始化数据导入器失败: {str(e)}")
        logger.info("请确保MongoDB服务已启动")
        return
    
    try:
        # 开始批量并行处理
        start_time = time.time()
        logger.info("🚀 开始处理设备数据...")
        logger.info("⚙️  配置: 5个线程，每个请求间隔5秒")
        
        importer.batch_process_devices(csv_file)
        end_time = time.time()
        
        # 输出统计信息
        stats = importer.get_stats()
        logger.info("\n📊 数据库统计信息:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        logger.info(f"\n⏱️ 总耗时: {end_time - start_time:.2f} 秒")
        
    finally:
        # 关闭连接
        importer.close()

if __name__ == "__main__":
    main()