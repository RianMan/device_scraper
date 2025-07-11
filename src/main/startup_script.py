#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备信息爬取项目启动脚本
"""

import os
import sys
import subprocess
import time
import argparse

def check_requirements():
    """检查必要的依赖"""
    print("🔍 检查依赖...")
    
    # 包名映射：pip包名 -> import包名
    package_mapping = {
        'flask': 'flask',
        'flask-cors': 'flask_cors',
        'requests': 'requests',
        'beautifulsoup4': 'bs4',  # 修正：beautifulsoup4导入时使用bs4
        'selenium': 'selenium',
        'pandas': 'pandas',
        'pymongo': 'pymongo'
    }
    
    missing_packages = []
    
    for pip_name, import_name in package_mapping.items():
        try:
            __import__(import_name)
            print(f"  ✅ {pip_name}")
        except ImportError:
            missing_packages.append(pip_name)
            print(f"  ❌ {pip_name}")
    
    if missing_packages:
        print(f"\n缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install " + " ".join(missing_packages))
        return False
    
    return True

def check_mongodb():
    """检查MongoDB连接"""
    print("🔍 检查MongoDB连接...")
    
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
        client.server_info()
        client.close()
        print("  ✅ MongoDB连接正常")
        return True
    except Exception as e:
        print(f"  ❌ MongoDB连接失败: {str(e)}")
        print("\n📝 MongoDB安装说明:")
        print("  macOS:")
        print("    brew tap mongodb/brew")
        print("    brew install mongodb-community")
        print("    brew services start mongodb/brew/mongodb-community")
        print("\n  Ubuntu:")
        print("    sudo apt update")
        print("    sudo apt install -y mongodb")
        print("    sudo systemctl start mongod")
        print("\n  Windows:")
        print("    下载MongoDB安装包: https://www.mongodb.com/try/download/community")
        print("    安装后启动MongoDB服务")
        return False

def check_csv_file():
    """检查CSV文件"""
    print("🔍 检查CSV文件...")
    
    csv_file = "device_result.csv"
    if os.path.exists(csv_file):
        print(f"  ✅ 找到CSV文件: {csv_file}")
        
        # 检查文件内容
        try:
            import pandas as pd
            df = pd.read_csv(csv_file)
            
            required_columns = ['clientmanufacture', 'clientmodel']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"  ❌ CSV文件缺少必要列: {missing_columns}")
                return False
            
            print(f"  ✅ CSV文件格式正确，共 {len(df)} 行数据")
            return True
            
        except Exception as e:
            print(f"  ❌ CSV文件读取失败: {str(e)}")
            return False
    else:
        print(f"  ❌ 未找到CSV文件: {csv_file}")
        return False

def run_data_import():
    """运行数据导入"""
    print("🚀 开始数据导入...")
    
    try:
        # 使用独立的导入脚本避免Flask路由冲突
        import subprocess
        import sys
        
        # 运行独立的导入脚本
        result = subprocess.run([
            sys.executable, 'import_data_script.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 数据导入完成")
            # 输出导入日志
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if 'INFO' in line:
                        print(f"  {line.split('INFO:')[-1]}")
            return True
        else:
            print(f"❌ 数据导入失败")
            if result.stderr:
                print(f"错误信息: {result.stderr}")
            return False
        
    except Exception as e:
        print(f"❌ 数据导入失败: {str(e)}")
        return False

def run_api_service():
    """启动API服务"""
    print("🚀 启动API服务...")
    
    try:
        # 确保没有路由冲突，重新导入
        import importlib
        import sys
        
        # 清除之前的模块缓存
        modules_to_clear = [k for k in sys.modules.keys() if k.startswith('enhanced_api_service') or k.startswith('device_db_manager')]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # 重新导入API服务
        from enhanced_api_service import app, device_service
        
        print("API服务已启动:")
        print("  - 设备查询: http://172.16.29.227:8080/api/device-info")
        print("  - 数据库统计: http://172.16.29.227:8080/api/database-stats")
        print("  - 健康检查: http://172.16.29.227:8080/api/health")
        print("  - 前端页面: 打开 index.html")
        
        app.run(debug=False, host='0.0.0.0', port=8080)
        
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 服务启动失败: {str(e)}")
    finally:
        try:
            device_service.close()
        except:
            pass

def main():
    parser = argparse.ArgumentParser(description='设备信息爬取项目管理工具')
    parser.add_argument('action', choices=['check', 'import', 'api', 'all'], 
                       help='执行的操作: check(检查环境), import(导入数据), api(启动API), all(完整流程)')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("🔧 设备信息爬取项目管理工具")
    print("=" * 50)
    
    if args.action in ['check', 'all']:
        print("\n📋 环境检查:")
        
        # 检查依赖
        if not check_requirements():
            print("❌ 依赖检查失败，请先安装必要的包")
            return
        
        # 检查MongoDB
        mongodb_ok = check_mongodb()
        
        # 检查CSV文件
        csv_ok = check_csv_file()
        
        if not csv_ok:
            print("❌ CSV文件检查失败")
            if args.action == 'all':
                return
        
        print("✅ 环境检查完成")
    
    if args.action in ['import', 'all']:
        if args.action == 'all':
            print("\n" + "=" * 50)
        
        print("\n📥 数据导入:")
        
        if not check_mongodb():
            print("❌ MongoDB未连接，跳过数据导入")
        elif not check_csv_file():
            print("❌ CSV文件不可用，跳过数据导入")
        else:
            if not run_data_import():
                print("❌ 数据导入失败")
                if args.action == 'all':
                    return
    
    if args.action in ['api', 'all']:
        if args.action == 'all':
            print("\n" + "=" * 50)
        
        print("\n🌐 API服务:")
        run_api_service()

if __name__ == "__main__":
    main()