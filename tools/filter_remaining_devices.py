#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
过滤剩余设备脚本 - tools/filter_remaining_devices.py
从原始model_codes.csv中排除已成功处理的设备，生成新的待处理文件
"""

import pandas as pd
import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def filter_remaining_devices(
    original_file="model_codes.csv",
    success_file="device_success.csv", 
    output_file=None
):
    """
    过滤出剩余未处理的设备
    
    Args:
        original_file: 原始设备文件路径
        success_file: 成功处理的设备文件路径
        output_file: 输出文件路径，如果为None则自动生成
    
    Returns:
        str: 输出文件路径，如果失败返回None
    """
    
    logger.info("🔄 开始过滤剩余设备...")
    logger.info("=" * 60)
    
    try:
        # 1. 检查原始文件是否存在
        if not os.path.exists(original_file):
            logger.error(f"❌ 原始文件不存在: {original_file}")
            return None
        
        # 2. 检查成功文件是否存在
        if not os.path.exists(success_file):
            logger.warning(f"⚠️ 成功文件不存在: {success_file}")
            logger.info("将复制原始文件作为输出")
            
            # 如果没有成功文件，直接复制原始文件
            df_original = pd.read_csv(original_file)
            if output_file is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = f"model_codes_remaining_{timestamp}.csv"
            
            df_original.to_csv(output_file, index=False)
            logger.info(f"✅ 已复制原始文件到: {output_file}")
            return output_file
        
        # 3. 读取原始设备列表
        logger.info(f"📄 读取原始设备文件: {original_file}")
        df_original = pd.read_csv(original_file)
        
        if 'model_code' not in df_original.columns:
            logger.error(f"❌ 原始文件缺少 'model_code' 列")
            return None
        
        # 清理和标准化原始数据
        df_original['model_code'] = df_original['model_code'].astype(str).str.strip()
        df_original = df_original[df_original['model_code'] != '']
        df_original = df_original.dropna(subset=['model_code'])
        
        original_count = len(df_original)
        unique_original = df_original['model_code'].nunique()
        
        logger.info(f"   总行数: {original_count}")
        logger.info(f"   唯一设备数: {unique_original}")
        
        # 4. 读取成功处理的设备列表
        logger.info(f"📄 读取成功设备文件: {success_file}")
        df_success = pd.read_csv(success_file)
        
        if 'original_model_code' not in df_success.columns:
            logger.error(f"❌ 成功文件缺少 'original_model_code' 列")
            return None
        
        # 清理和标准化成功数据
        df_success['original_model_code'] = df_success['original_model_code'].astype(str).str.strip()
        df_success = df_success[df_success['original_model_code'] != '']
        df_success = df_success.dropna(subset=['original_model_code'])
        
        success_count = len(df_success)
        unique_success = df_success['original_model_code'].nunique()
        
        logger.info(f"   成功处理行数: {success_count}")
        logger.info(f"   唯一成功设备数: {unique_success}")
        
        # 5. 获取已成功处理的设备集合
        processed_devices = set(df_success['original_model_code'].unique())
        logger.info(f"📋 已处理设备集合大小: {len(processed_devices)}")
        
        # 6. 过滤出剩余设备
        logger.info("🔍 过滤剩余设备...")
        df_remaining = df_original[~df_original['model_code'].isin(processed_devices)]
        
        remaining_count = len(df_remaining)
        unique_remaining = df_remaining['model_code'].nunique()
        
        logger.info(f"   剩余设备行数: {remaining_count}")
        logger.info(f"   唯一剩余设备数: {unique_remaining}")
        
        # 7. 去重（保留第一次出现的）
        df_remaining_unique = df_remaining.drop_duplicates(subset=['model_code'], keep='first')
        final_count = len(df_remaining_unique)
        
        logger.info(f"   去重后剩余设备数: {final_count}")
        
        # 8. 生成输出文件名
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"model_codes_remaining_{timestamp}.csv"
        
        # 9. 保存结果
        df_remaining_unique.to_csv(output_file, index=False)
        
        # 10. 输出统计信息
        logger.info("\n" + "=" * 60)
        logger.info("📊 处理统计")
        logger.info("=" * 60)
        logger.info(f"📄 原始设备数: {unique_original}")
        logger.info(f"✅ 已处理设备数: {unique_success}")
        logger.info(f"📋 剩余设备数: {final_count}")
        logger.info(f"📈 处理进度: {(unique_success / unique_original * 100):.1f}%")
        logger.info(f"💾 输出文件: {output_file}")
        
        # 11. 显示一些样例剩余设备
        if final_count > 0:
            logger.info("\n📋 剩余设备样例:")
            sample_devices = df_remaining_unique['model_code'].head(5).tolist()
            for i, device in enumerate(sample_devices, 1):
                logger.info(f"   {i}. {device}")
            
            if final_count > 5:
                logger.info(f"   ... 还有 {final_count - 5} 个设备")
        
        logger.info("\n✅ 过滤完成!")
        return output_file
        
    except Exception as e:
        logger.error(f"❌ 过滤过程中发生错误: {str(e)}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return None

def show_processing_summary(
    original_file="model_codes.csv",
    success_file="device_success.csv"
):
    """
    显示处理进度摘要
    """
    logger.info("📊 处理进度摘要")
    logger.info("=" * 50)
    
    try:
        # 读取原始文件
        if os.path.exists(original_file):
            df_original = pd.read_csv(original_file)
            if 'model_code' in df_original.columns:
                df_original['model_code'] = df_original['model_code'].astype(str).str.strip()
                df_original = df_original[df_original['model_code'] != '']
                original_unique = df_original['model_code'].nunique()
            else:
                original_unique = 0
        else:
            original_unique = 0
        
        # 读取成功文件
        if os.path.exists(success_file):
            df_success = pd.read_csv(success_file)
            if 'original_model_code' in df_success.columns:
                df_success['original_model_code'] = df_success['original_model_code'].astype(str).str.strip()
                df_success = df_success[df_success['original_model_code'] != '']
                success_unique = df_success['original_model_code'].nunique()
            else:
                success_unique = 0
        else:
            success_unique = 0
        
        remaining = original_unique - success_unique
        progress = (success_unique / original_unique * 100) if original_unique > 0 else 0
        
        logger.info(f"📄 原始设备总数: {original_unique}")
        logger.info(f"✅ 已成功处理: {success_unique}")
        logger.info(f"📋 剩余待处理: {remaining}")
        logger.info(f"📈 完成进度: {progress:.1f}%")
        
        if remaining > 0:
            logger.info(f"💡 建议: 运行过滤脚本生成剩余设备文件")
        else:
            logger.info(f"🎉 所有设备已处理完成!")
            
    except Exception as e:
        logger.error(f"❌ 获取摘要失败: {str(e)}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='过滤剩余未处理的设备',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python filter_remaining_devices.py                    # 使用默认文件
  python filter_remaining_devices.py --summary          # 只显示处理摘要
  python filter_remaining_devices.py -o remaining.csv   # 指定输出文件
  python filter_remaining_devices.py -i my_models.csv -s my_success.csv  # 指定输入文件
        """
    )
    
    parser.add_argument('-i', '--input',
                       default='model_codes.csv',
                       help='原始设备文件路径 (默认: model_codes.csv)')
    
    parser.add_argument('-s', '--success',
                       default='device_success.csv',
                       help='成功处理的设备文件路径 (默认: device_success.csv)')
    
    parser.add_argument('-o', '--output',
                       help='输出文件路径 (默认: 自动生成带时间戳的文件名)')
    
    parser.add_argument('--summary',
                       action='store_true',
                       help='只显示处理进度摘要，不生成新文件')
    
    args = parser.parse_args()
    
    logger.info("🔧 设备过滤工具 v1.0.0")
    logger.info("💡 排除已成功处理的设备，生成剩余待处理列表")
    
    if args.summary:
        show_processing_summary(args.input, args.success)
    else:
        result = filter_remaining_devices(args.input, args.success, args.output)
        
        if result:
            logger.info(f"\n🎯 成功生成剩余设备文件: {result}")
            logger.info("💡 可以使用以下命令继续处理:")
            logger.info(f"   python main.py -i {result}")
        else:
            logger.error("❌ 过滤失败")

if __name__ == "__main__":
    main()