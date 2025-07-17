#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备信息爬取系统主入口 - main.py
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from scraper.orchestrator import DeviceInfoOrchestrator
from tools.csv_tools import CSVTools

def setup_logging(verbose=False):
    """设置日志配置"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # 创建logs目录
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 日志文件名
    log_filename = f"device_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_filepath = os.path.join(log_dir, log_filename)
    
    # 配置日志
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filepath, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"日志文件: {log_filepath}")
    return logger

def check_environment():
    """检查运行环境"""
    logger = logging.getLogger(__name__)
    
    logger.info("🔍 检查运行环境...")
    
    # 检查必要的包
    required_packages = [
        'requests', 'beautifulsoup4', 'selenium', 'pandas'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'beautifulsoup4':
                import bs4
            else:
                __import__(package)
            logger.info(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"❌ {package}")
    
    if missing_packages:
        logger.error(f"缺少依赖包: {', '.join(missing_packages)}")
        logger.info("请运行: pip install " + " ".join(missing_packages))
        return False
    
    # 检查Chrome WebDriver
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.quit()
        logger.info("✅ Chrome WebDriver")
    except Exception as e:
        logger.error(f"❌ Chrome WebDriver: {str(e)}")
        logger.info("请确保安装了Chrome浏览器和ChromeDriver")
        return False
    
    logger.info("✅ 环境检查通过")
    return True

def create_directory_structure():
    """创建必要的目录结构"""
    directories = [
        "output",
        "logs", 
        "google",
        "gsmarena",
        "gsmchoice",
        "scraper",
        "tools",
        "test"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        
        # 创建__init__.py文件
        init_file = os.path.join(directory, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write(f'"""\\n{directory.title()} 模块\\n"""\n')

def validate_input_file(csv_file):
    """验证输入文件"""
    logger = logging.getLogger(__name__)
    
    if not os.path.exists(csv_file):
        logger.error(f"输入文件不存在: {csv_file}")
        
        # 询问是否创建示例文件
        response = input(f"是否创建示例文件 {csv_file}? (y/n): ")
        if response.lower() == 'y':
            CSVTools.create_sample_model_codes_csv(csv_file, sample_count=5)
            logger.info(f"✅ 已创建示例文件: {csv_file}")
            return True
        else:
            return False
    
    # 验证文件结构
    valid, message = CSVTools.validate_csv_structure(csv_file, ['model_code'])
    
    if valid:
        logger.info(f"✅ 输入文件有效: {message}")
        return True
    else:
        logger.error(f"❌ 输入文件无效: {message}")
        return False

def run_scraper(args):
    """运行爬虫"""
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 启动设备信息爬取系统")
    logger.info("=" * 60)
    
    # 验证输入文件
    if not validate_input_file(args.input):
        return False
    
    # 创建调度器
    orchestrator = DeviceInfoOrchestrator(request_delay=args.delay)
    
    try:
        # 读取设备列表
        devices = CSVTools.read_model_codes_csv(args.input)
        
        if not devices:
            logger.error("没有读取到有效的设备数据")
            return False
        
        logger.info(f"📄 读取到 {len(devices)} 个设备")
        
        # 限制处理数量（如果指定）
        if args.limit and args.limit > 0:
            devices = devices[:args.limit]
            logger.info(f"⚡ 限制处理数量: {len(devices)} 个设备")
        
        # 开始处理
        logger.info(f"⚙️ 配置: 延迟 {args.delay} 秒/请求")
        start_time = datetime.now()
        
        summary = orchestrator.process_device_list(devices)
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # 保存结果
        saved_files = orchestrator.save_results()
        
        # 输出最终统计
        logger.info("\n" + "=" * 60)
        logger.info("🎉 处理完成!")
        logger.info("=" * 60)
        logger.info(f"⏱️ 总耗时: {total_time:.1f} 秒")
        logger.info(f"📁 保存的文件:")
        for file_type, filepath in saved_files.items():
            logger.info(f"   {file_type}: {filepath}")
        
        return True
        
    except KeyboardInterrupt:
        logger.warning("⚠️ 用户中断处理")
        return False
    except Exception as e:
        logger.error(f"❌ 处理过程中发生错误: {str(e)}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False
    finally:
        orchestrator.close()

def run_test():
    """运行测试模式"""
    logger = logging.getLogger(__name__)
    
    logger.info("🧪 运行测试模式")
    
    try:
        from test.test_flow import run_quick_test
        run_quick_test()
        return True
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='设备信息爬取系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py                           # 使用默认设置处理model_codes.csv
  python main.py -i my_devices.csv        # 指定输入文件
  python main.py -l 10                    # 只处理前10个设备
  python main.py -d 5                     # 设置5秒延迟
  python main.py --test                   # 运行测试模式
  python main.py -v                       # 详细日志模式
        """
    )
    
    parser.add_argument('-i', '--input', 
                       default='model_codes.csv',
                       help='输入CSV文件路径 (默认: model_codes.csv)')
    
    parser.add_argument('-d', '--delay',
                       type=int, default=4,
                       help='请求间隔延迟(秒) (默认: 4)')
    
    parser.add_argument('-l', '--limit',
                       type=int, default=0,
                       help='限制处理设备数量 (0=全部处理)')
    
    parser.add_argument('--test',
                       action='store_true',
                       help='运行测试模式')
    
    parser.add_argument('-v', '--verbose',
                       action='store_true',
                       help='详细日志输出')
    
    args = parser.parse_args()
    
    # 创建目录结构
    create_directory_structure()
    
    # 设置日志
    logger = setup_logging(args.verbose)
    
    logger.info("📱 设备信息爬取系统 v1.0.0")
    logger.info("🔧 模块化架构 | Google+GSMArena+GSMChoice")
    
    # 检查环境
    if not check_environment():
        logger.error("❌ 环境检查失败，程序退出")
        sys.exit(1)
    
    # 根据模式运行
    if args.test:
        success = run_test()
    else:
        success = run_scraper(args)
    
    if success:
        logger.info("✅ 程序执行成功")
        sys.exit(0)
    else:
        logger.error("❌ 程序执行失败")
        sys.exit(1)

if __name__ == "__main__":
    main()