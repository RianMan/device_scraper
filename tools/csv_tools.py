#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV工具模块 - tools/csv_tools.py
负责CSV文件的读取和写入操作
"""

import pandas as pd
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class CSVTools:
    """CSV操作工具类"""
    
    @staticmethod
    def read_model_codes_csv(csv_file="model_codes.csv"):
        """读取model_codes.csv文件"""
        try:
            if not os.path.exists(csv_file):
                logger.error(f"CSV文件不存在: {csv_file}")
                return []
            
            df = pd.read_csv(csv_file)
            logger.info(f"读取CSV文件: {csv_file}, 共 {len(df)} 行")
            
            # 获取唯一的型号代码
            if 'model_code' in df.columns:
                unique_models = df['model_code'].dropna().unique()
            else:
                logger.error(f"CSV文件缺少 'model_code' 列")
                return []
            
            logger.info(f"唯一型号数量: {len(unique_models)}")
            
            # 转换为处理格式
            devices = []
            for model_code in unique_models:
                if pd.notna(model_code) and str(model_code).strip():
                    devices.append({
                        'model_code': str(model_code).strip()
                    })
            
            logger.info(f"有效设备数量: {len(devices)}")
            return devices
            
        except Exception as e:
            logger.error(f"读取CSV文件失败: {str(e)}")
            return []
    
    @staticmethod
    def read_device_result_csv(csv_file="device_result.csv"):
        """读取device_result.csv文件（包含manufacture和model列）"""
        try:
            if not os.path.exists(csv_file):
                logger.error(f"CSV文件不存在: {csv_file}")
                return []
            
            df = pd.read_csv(csv_file)
            logger.info(f"读取CSV文件: {csv_file}, 共 {len(df)} 行")
            
            # 检查必要的列
            required_columns = ['clientmanufacture', 'clientmodel']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.error(f"CSV文件缺少必要列: {missing_columns}")
                return []
            
            # 提取设备信息
            devices = []
            for index, row in df.iterrows():
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
    
    @staticmethod
    def save_device_results(results: List[Dict[str, Any]], filename_prefix="device_info_extracted"):
        """保存设备信息结果到CSV"""
        try:
            if not results:
                logger.warning("没有结果需要保存")
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename_prefix}_{timestamp}.csv"
            
            # 确保输出目录存在
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)
            
            # 转换为DataFrame
            df = pd.DataFrame(results)
            
            # 保存到CSV
            df.to_csv(filepath, index=False, encoding='utf-8')
            
            logger.info(f"✅ 成功保存 {len(results)} 条结果到: {filepath}")
            
            # 显示样例数据
            if len(results) > 0:
                sample = results[0]
                logger.info(f"📋 样例数据:")
                logger.info(f"   设备: {sample.get('device_name', 'N/A')}")
                logger.info(f"   价格: {sample.get('price', 'N/A')}")
                logger.info(f"   发布: {sample.get('announced_date', 'N/A')}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"保存结果失败: {str(e)}")
            return None
    
    @staticmethod
    def save_failed_devices(failed_devices: List[Dict[str, Any]], filename_prefix="failed_devices"):
        """保存失败的设备信息"""
        try:
            if not failed_devices:
                logger.info("没有失败的设备需要保存")
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename_prefix}_{timestamp}.csv"
            
            # 确保输出目录存在
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)
            
            # 转换为DataFrame
            df = pd.DataFrame(failed_devices)
            
            # 保存到CSV
            df.to_csv(filepath, index=False, encoding='utf-8')
            
            logger.info(f"❌ 失败设备已保存到: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存失败设备失败: {str(e)}")
            return None
    
    @staticmethod
    def save_processing_log(log_data: Dict[str, Any], filename_prefix="processing_log"):
        """保存处理日志"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename_prefix}_{timestamp}.csv"
            
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)
            
            # 创建日志记录
            log_record = [{
                'timestamp': timestamp,
                'total_devices': log_data.get('total_devices', 0),
                'successful_devices': log_data.get('successful_devices', 0),
                'failed_devices': log_data.get('failed_devices', 0),
                'success_rate': log_data.get('success_rate', 0),
                'processing_time_seconds': log_data.get('processing_time_seconds', 0),
                'google_searches': log_data.get('google_searches', 0),
                'gsmarena_direct_hits': log_data.get('gsmarena_direct_hits', 0),
                'gsmchoice_fallbacks': log_data.get('gsmchoice_fallbacks', 0),
                'notes': log_data.get('notes', '')
            }]
            
            df = pd.DataFrame(log_record)
            df.to_csv(filepath, index=False, encoding='utf-8')
            
            logger.info(f"📊 处理日志已保存到: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存处理日志失败: {str(e)}")
            return None
    
    @staticmethod
    def create_sample_model_codes_csv(filename="model_codes.csv", sample_count=5):
        """创建示例model_codes.csv文件用于测试"""
        try:
            sample_models = [
                "SM-J415G",
                "moto g(50) 5G", 
                "ZTE 8050",
                "CPH2387",
                "LM-X420"
            ]
            
            # 如果请求更多样本，重复列表
            if sample_count > len(sample_models):
                multiplier = (sample_count // len(sample_models)) + 1
                extended_models = (sample_models * multiplier)[:sample_count]
            else:
                extended_models = sample_models[:sample_count]
            
            df = pd.DataFrame({'model_code': extended_models})
            df.to_csv(filename, index=False)
            
            logger.info(f"✅ 创建示例CSV文件: {filename}, 包含 {len(extended_models)} 个型号")
            return filename
            
        except Exception as e:
            logger.error(f"创建示例CSV失败: {str(e)}")
            return None
    
    @staticmethod
    def validate_csv_structure(csv_file, required_columns):
        """验证CSV文件结构"""
        try:
            if not os.path.exists(csv_file):
                return False, f"文件不存在: {csv_file}"
            
            df = pd.read_csv(csv_file)
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return False, f"缺少必要列: {missing_columns}"
            
            if len(df) == 0:
                return False, "文件为空"
            
            return True, f"文件有效，包含 {len(df)} 行数据"
            
        except Exception as e:
            return False, f"文件验证失败: {str(e)}"
    
    @staticmethod
    def merge_results_files(file_pattern="output/device_info_extracted_*.csv", output_filename="merged_results.csv"):
        """合并多个结果文件"""
        try:
            import glob
            
            files = glob.glob(file_pattern)
            if not files:
                logger.warning(f"没有找到匹配的文件: {file_pattern}")
                return None
            
            logger.info(f"找到 {len(files)} 个文件进行合并")
            
            all_dfs = []
            for file in files:
                try:
                    df = pd.read_csv(file)
                    df['source_file'] = os.path.basename(file)
                    all_dfs.append(df)
                    logger.info(f"读取文件: {file} ({len(df)} 行)")
                except Exception as e:
                    logger.warning(f"跳过文件 {file}: {str(e)}")
            
            if not all_dfs:
                logger.error("没有成功读取任何文件")
                return None
            
            # 合并所有DataFrame
            merged_df = pd.concat(all_dfs, ignore_index=True)
            
            # 去重（基于model_code）
            initial_count = len(merged_df)
            merged_df = merged_df.drop_duplicates(subset=['original_model_code'], keep='last')
            final_count = len(merged_df)
            
            # 保存合并结果
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)
            
            merged_df.to_csv(output_path, index=False, encoding='utf-8')
            
            logger.info(f"✅ 合并完成: {output_path}")
            logger.info(f"📊 合并前: {initial_count} 行，去重后: {final_count} 行")
            
            return output_path
            
        except Exception as e:
            logger.error(f"合并文件失败: {str(e)}")
            return None