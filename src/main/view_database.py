#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看MongoDB数据库内容的脚本
"""

import pymongo
from pymongo import MongoClient
import json
from datetime import datetime
import pandas as pd

def connect_db():
    """连接数据库"""
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client["device_info"]
        collection = db["devices"]
        return client, collection
    except Exception as e:
        print(f"连接数据库失败: {e}")
        return None, None

def show_stats(collection):
    """显示数据库统计信息"""
    print("=" * 60)
    print("📊 数据库统计信息")
    print("=" * 60)
    
    total_count = collection.count_documents({})
    with_price = collection.count_documents({"price": {"$ne": ""}})
    with_date = collection.count_documents({"announced_date": {"$ne": ""}})
    
    print(f"📱 总设备数: {total_count}")
    print(f"💰 有价格信息: {with_price} ({with_price/total_count*100:.1f}%)" if total_count > 0 else "💰 有价格信息: 0")
    print(f"📅 有日期信息: {with_date} ({with_date/total_count*100:.1f}%)" if total_count > 0 else "📅 有日期信息: 0")
    
    # 品牌分布
    print(f"\n🏭 品牌分布:")
    brand_pipeline = [
        {"$group": {"_id": "$manufacture", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    brands = list(collection.aggregate(brand_pipeline))
    for brand in brands:
        print(f"  {brand['_id']}: {brand['count']} 台")

def show_recent_devices(collection, limit=5):
    """显示最近添加的设备"""
    print("\n" + "=" * 60)
    print(f"🕒 最近添加的 {limit} 台设备")
    print("=" * 60)
    
    devices = collection.find({}).sort("created_at", -1).limit(limit)
    
    for i, device in enumerate(devices, 1):
        print(f"\n{i}. {device.get('device_name', 'Unknown')}")
        print(f"   型号: {device.get('model_code', 'N/A')}")
        print(f"   制造商: {device.get('manufacture', 'N/A')}")
        print(f"   价格: {device.get('price', 'N/A')}")
        print(f"   发布日期: {device.get('announced_date', 'N/A')}")
        print(f"   添加时间: {device.get('created_at', 'N/A')}")

def search_device(collection, keyword):
    """搜索设备"""
    print(f"\n🔍 搜索关键词: {keyword}")
    print("=" * 60)
    
    # 在设备名称和型号中搜索
    query = {
        "$or": [
            {"device_name": {"$regex": keyword, "$options": "i"}},
            {"model_code": {"$regex": keyword, "$options": "i"}},
            {"manufacture": {"$regex": keyword, "$options": "i"}}
        ]
    }
    
    devices = list(collection.find(query).limit(10))
    
    if not devices:
        print("❌ 未找到匹配的设备")
        return
    
    print(f"✅ 找到 {len(devices)} 台设备:")
    for i, device in enumerate(devices, 1):
        print(f"\n{i}. {device.get('device_name', 'Unknown')}")
        print(f"   型号: {device.get('model_code', 'N/A')}")
        print(f"   制造商: {device.get('manufacture', 'N/A')}")
        print(f"   价格: {device.get('price', 'N/A')}")

def show_device_details(collection, model_code):
    """显示设备详细信息"""
    device = collection.find_one({"model_code": model_code})
    
    if not device:
        print(f"❌ 未找到型号为 {model_code} 的设备")
        return
    
    print(f"\n📱 设备详情: {device.get('device_name', 'Unknown')}")
    print("=" * 60)
    print(f"🏷️  型号代码: {device.get('model_code', 'N/A')}")
    print(f"🏭 制造商: {device.get('manufacture', 'N/A')}")
    print(f"📅 发布日期: {device.get('announced_date', 'N/A')}")
    print(f"🚀 上市日期: {device.get('release_date', 'N/A')}")
    print(f"💰 价格: {device.get('price', 'N/A')}")
    print(f"🔗 来源: {device.get('source_url', 'N/A')}")
    print(f"⏰ 添加时间: {device.get('created_at', 'N/A')}")
    
    # 显示主要规格
    specs = device.get('specifications', {})
    if specs:
        print(f"\n📋 主要规格:")
        important_specs = ['Technology', 'OS', 'Chipset', 'Internal', 'Dimensions', 'Weight']
        for spec in important_specs:
            if spec in specs:
                print(f"  {spec}: {specs[spec]}")

def export_to_csv(collection, filename="devices_export.csv"):
    """导出到CSV文件"""
    print(f"📤 正在导出到 {filename}...")
    
    # 获取所有设备的基本信息
    pipeline = [
        {
            "$project": {
                "_id": 0,
                "model_code": 1,
                "device_name": 1,
                "manufacture": 1,
                "announced_date": 1,
                "release_date": 1,
                "price": 1,
                "source_url": 1,
                "created_at": 1
            }
        }
    ]
    
    devices = list(collection.aggregate(pipeline))
    
    if devices:
        df = pd.DataFrame(devices)
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"✅ 成功导出 {len(devices)} 台设备到 {filename}")
    else:
        print("❌ 没有数据可导出")

def main():
    client, collection = connect_db()
    if client is None or collection is None:
        return
    
    try:
        while True:
            print("\n" + "=" * 60)
            print("🔧 MongoDB 设备数据库查看器")
            print("=" * 60)
            print("1. 📊 查看统计信息")
            print("2. 🕒 查看最近添加的设备")
            print("3. 🔍 搜索设备")
            print("4. 📱 查看设备详情")
            print("5. 📤 导出到CSV")
            print("6. 🚪 退出")
            
            choice = input("\n请选择操作 (1-6): ").strip()
            
            if choice == '1':
                show_stats(collection)
            
            elif choice == '2':
                limit = input("显示多少台设备? (默认5): ").strip()
                limit = int(limit) if limit.isdigit() else 5
                show_recent_devices(collection, limit)
            
            elif choice == '3':
                keyword = input("请输入搜索关键词: ").strip()
                if keyword:
                    search_device(collection, keyword)
            
            elif choice == '4':
                model_code = input("请输入设备型号代码: ").strip()
                if model_code:
                    show_device_details(collection, model_code)
            
            elif choice == '5':
                filename = input("导出文件名 (默认devices_export.csv): ").strip()
                filename = filename if filename else "devices_export.csv"
                export_to_csv(collection, filename)
            
            elif choice == '6':
                print("👋 再见!")
                break
            
            else:
                print("❌ 无效选择，请重试")
    
    finally:
        if client is not None:
            client.close()

if __name__ == "__main__":
    main()