#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键运行混合设备恢复脚本
"""

import os
import sys
import subprocess

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境")
    print("=" * 50)
    
    # 检查Python版本
    python_version = sys.version_info
    print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 7):
        print("❌ Python版本过低，需要3.7+")
        return False
    
    # 检查依赖
    required_packages = [
        'pandas', 'pymongo', 'requests', 'beautifulsoup4', 'selenium'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'beautifulsoup4':
                import bs4
            else:
                __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n缺少依赖包，正在安装: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install'
            ] + missing_packages)
            print("✅ 依赖安装完成")
        except subprocess.CalledProcessError:
            print("❌ 依赖安装失败，请手动安装")
            return False
    
    return True

def check_mongodb():
    """检查MongoDB"""
    print("\n🔍 检查MongoDB")
    print("-" * 30)
    
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
        client.server_info()
        
        # 检查数据库状态
        db = client["device_info"]
        collection = db["devices"]
        total_count = collection.count_documents({})
        unknown_count = collection.count_documents({"device_name": "Unknown"})
        
        print(f"✅ MongoDB连接成功")
        print(f"📊 现有设备总数: {total_count}")
        print(f"❓ Unknown设备数: {unknown_count}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ MongoDB连接失败: {str(e)}")
        print("\n💡 MongoDB启动指南:")
        print("macOS: brew services start mongodb/brew/mongodb-community")
        print("Ubuntu: sudo systemctl start mongod")
        print("Windows: 启动MongoDB服务")
        return False

def check_data_files():
    """检查数据文件"""
    print("\n🔍 检查数据文件")
    print("-" * 30)
    
    # 确保data目录存在
    if not os.path.exists('data'):
        os.makedirs('data', exist_ok=True)
        print("📁 创建data目录")
    
    required_files = [
        'data/failed_devices_20250711_030807.csv',
        'data/devices_export.csv'
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            try:
                import pandas as pd
                df = pd.read_csv(file_path)
                print(f"✅ {file_path} ({len(df)} 行)")
            except Exception as e:
                print(f"⚠️ {file_path} (读取失败: {str(e)})")
                missing_files.append(file_path)
        else:
            print(f"❌ {file_path} (不存在)")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❓ 缺少数据文件，是否创建示例文件用于测试?")
        response = input("输入 y 创建示例文件，或将现有文件放入data目录后重新运行: ")
        
        if response.lower() == 'y':
            create_sample_files()
            return True
        else:
            return False
    
    return True

def create_sample_files():
    """创建示例文件"""
    import pandas as pd
    
    print("📝 创建示例数据文件...")
    
    # 示例失败设备
    sample_failed = pd.DataFrame([
        {'manufacture': 'Blackview', 'model_code': 'BV4900 Pro'},
        {'manufacture': 'OPPO', 'model_code': 'CPH2387'}, 
        {'manufacture': 'Samsung', 'model_code': 'SM-A245F'},
        {'manufacture': 'Motorola', 'model_code': 'XT2129-1'},
        {'manufacture': 'Xiaomi', 'model_code': 'M2101K6G'},
    ])
    sample_failed.to_csv('data/failed_devices_20250711_030807.csv', index=False)
    
    # 示例导出数据（包含Unknown设备）
    sample_export = pd.DataFrame([
        {'model_code': 'BV4900 Pro', 'device_name': 'Unknown', 'manufacture': 'Blackview'},
        {'model_code': 'CPH2387', 'device_name': 'Unknown', 'manufacture': 'OPPO'},
        {'model_code': 'SM-G991B', 'device_name': 'Samsung Galaxy S21', 'manufacture': 'Samsung'},
        {'model_code': 'TEST001', 'device_name': 'Unknown', 'manufacture': 'TestBrand'},
    ])
    sample_export.to_csv('data/devices_export.csv', index=False)
    
    print("✅ 示例文件创建完成")

def save_hybrid_scraper():
    """保存混合爬虫代码到文件"""
    print("\n📄 检查混合爬虫脚本")
    print("-" * 30)
    
    script_file = 'hybrid_device_scraper.py'
    
    if os.path.exists(script_file):
        print(f"✅ {script_file} 已存在")
        return True
    else:
        print(f"❌ {script_file} 不存在")
        print("请将混合策略爬虫代码保存为 'hybrid_device_scraper.py'")
        return False

def run_hybrid_scraper():
    """运行混合爬虫"""
    print("\n🚀 运行混合设备恢复")
    print("=" * 50)
    
    try:
        # 导入并运行混合爬虫
        import importlib.util
        
        spec = importlib.util.spec_from_file_location(
            "hybrid_scraper", "hybrid_device_scraper.py"
        )
        hybrid_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hybrid_module)
        
        # 运行主函数
        hybrid_module.main()
        
    except Exception as e:
        print(f"❌ 运行失败: {str(e)}")
        import traceback
        traceback.print_exc()

def show_results():
    """显示处理结果"""
    print("\n📊 处理结果统计")
    print("=" * 50)
    
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/")
        db = client["device_info"]
        collection = db["devices"]
        
        # 统计信息
        total_count = collection.count_documents({})
        unknown_count = collection.count_documents({"device_name": "Unknown"})
        hybrid_count = collection.count_documents({"data_source": "hybrid_gsmchoice_gsmarena"})
        with_price = collection.count_documents({"price": {"$ne": ""}, "price": {"$ne": "Price not available"}})
        
        print(f"📱 设备总数: {total_count}")
        print(f"❓ Unknown设备: {unknown_count}")
        print(f"🔄 混合策略处理: {hybrid_count}")
        print(f"💰 有价格信息: {with_price}")
        print(f"📈 价格覆盖率: {with_price/total_count*100:.1f}%" if total_count > 0 else "📈 价格覆盖率: 0%")
        
        # 检查是否有新的失败文件
        import glob
        still_failed_files = glob.glob('data/still_failed_hybrid_*.csv')
        if still_failed_files:
            latest_failed = max(still_failed_files, key=os.path.getctime)
            import pandas as pd
            failed_df = pd.read_csv(latest_failed)
            print(f"⚠️ 仍有 {len(failed_df)} 个设备处理失败，详见: {latest_failed}")
        else:
            print("✅ 所有设备处理完成")
        
        client.close()
        
    except Exception as e:
        print(f"❌ 获取统计信息失败: {str(e)}")

def main():
    """主函数"""
    print("🔧 混合策略设备信息恢复工具")
    print("=" * 60)
    print("功能: 结合GSMChoice和GSMArena恢复失败设备信息")
    print("策略: GSMChoice获取设备名 → GSMArena获取详细信息")
    print("=" * 60)
    
    # 步骤1: 检查环境
    if not check_environment():
        print("❌ 环境检查失败")
        return
    
    # 步骤2: 检查MongoDB
    if not check_mongodb():
        print("❌ MongoDB检查失败")
        return
    
    # 步骤3: 检查数据文件
    if not check_data_files():
        print("❌ 数据文件检查失败")
        return
    
    # 步骤4: 检查爬虫脚本
    if not save_hybrid_scraper():
        print("❌ 爬虫脚本检查失败")
        return
    
    # 步骤5: 询问是否继续
    print("\n" + "=" * 60)
    print("🚨 注意事项:")
    print("1. 此过程会访问外部网站，请确保网络连接稳定")
    print("2. 处理时间可能较长，建议耐心等待")
    print("3. 程序会自动保存处理失败的设备到新文件")
    print("4. 所有成功的设备信息会更新到MongoDB数据库")
    
    response = input("\n❓ 是否开始处理? (y/n): ")
    
    if response.lower() != 'y':
        print("👋 程序退出")
        return
    
    # 步骤6: 运行混合爬虫
    run_hybrid_scraper()
    
    # 步骤7: 显示结果
    show_results()
    
    print("\n🎉 混合恢复任务完成!")

if __name__ == "__main__":
    main()