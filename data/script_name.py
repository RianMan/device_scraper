import pandas as pd
import re
from datetime import datetime

def process_date(date_str):
    """
    处理日期格式，转换为标准格式
    输入格式如：2024, October 15 -> 2024-10-15
    """
    if pd.isna(date_str) or date_str == '':
        return ''
    
    date_str = str(date_str).strip()
    
    # 月份映射
    month_map = {
        'January': '01', 'February': '02', 'March': '03', 'April': '04',
        'May': '05', 'June': '06', 'July': '07', 'August': '08',
        'September': '09', 'October': '10', 'November': '11', 'December': '12'
    }
    
    # 情况1: 只有年份，如 "2022"
    if re.match(r'^\d{4}$', date_str):
        return date_str
    
    # 情况2: 年份和月份，如 "2019, March"
    match = re.match(r'^(\d{4}),\s*(\w+)$', date_str)
    if match:
        year, month = match.groups()
        month_num = month_map.get(month, '')
        if month_num:
            return f"{year}-{month_num}"
        return year
    
    # 情况3: 完整日期，如 "2024, October 15"
    match = re.match(r'^(\d{4}),\s*(\w+)\s+(\d{1,2})$', date_str)
    if match:
        year, month, day = match.groups()
        month_num = month_map.get(month, '')
        if month_num:
            day = day.zfill(2)  # 补零
            return f"{year}-{month_num}-{day}"
    
    return ''

def process_price(price_str):
    """
    处理价格格式，转换为美元
    """
    if pd.isna(price_str) or price_str == '':
        return ''
    
    price_str = str(price_str).strip()
    
    # 简单汇率映射（固定汇率，实际项目中可能需要实时汇率）
    exchange_rates = {
        'EUR': 1.1,    # 欧元转美元
        'GBP': 1.3,    # 英镑转美元
        'INR': 0.012,  # 印度卢比转美元
        'CAD': 0.74,   # 加元转美元
    }
    
    # 如果已经包含美元，直接提取美元价格
    usd_match = re.search(r'\$\s*([\d,]+\.?\d*)', price_str)
    if usd_match:
        usd_price = usd_match.group(1).replace(',', '')
        try:
            return float(usd_price)
        except:
            pass
    
    # 处理 "About XXX EUR" 格式
    about_match = re.search(r'About\s+([\d,]+\.?\d*)\s+(\w+)', price_str)
    if about_match:
        amount, currency = about_match.groups()
        amount = float(amount.replace(',', ''))
        if currency in exchange_rates:
            return round(amount * exchange_rates[currency], 2)
    
    # 处理其他货币格式
    for currency, rate in exchange_rates.items():
        pattern = f'({currency}|€|£|₹)\\s*([\d,]+\.?\d*)'
        if currency == 'EUR':
            pattern = f'(€|EUR)\\s*([\d,]+\.?\d*)'
        elif currency == 'GBP':
            pattern = f'(£|GBP)\\s*([\d,]+\.?\d*)'
        elif currency == 'INR':
            pattern = f'(₹|INR)\\s*([\d,]+\.?\d*)'
        
        match = re.search(pattern, price_str)
        if match:
            amount = float(match.group(2).replace(',', ''))
            return round(amount * rate, 2)
    
    return ''

def main():
    """
    主函数：处理所有数据
    """
    print("开始处理数据...")
    
    # 1. 读取ina_data.csv
    print("读取ina_data.csv...")
    ina_data = pd.read_csv('ina_data.csv')
    print(f"ina_data包含 {len(ina_data)} 条记录")
    
    # 2. 读取所有device_success文件并合并
    print("读取device_success文件...")
    device_data_list = []
    
    for i in range(1, 2):  # device_success01.csv 到 device_success05.csv
        filename = f'device_success{i:02d}.csv'
        try:
            df = pd.read_csv(filename)
            device_data_list.append(df)
            print(f"读取 {filename}: {len(df)} 条记录")
        except FileNotFoundError:
            print(f"警告: 文件 {filename} 不存在，跳过...")
    
    if not device_data_list:
        print("错误: 没有找到任何device_success文件")
        return
    
    # 合并所有device_success数据
    device_data = pd.concat(device_data_list, ignore_index=True)
    print(f"合并后的device_success数据包含 {len(device_data)} 条记录")
    
    # 3. 去重
    device_data = device_data.drop_duplicates(subset=['original_model_code'])
    print(f"去重后包含 {len(device_data)} 条记录")
    
    # 4. 合并数据
    print("合并数据...")
    # 使用original_model_code与clientmodel进行匹配
    merged_data = device_data.merge(
        ina_data, 
        left_on='original_model_code', 
        right_on='clientmodel', 
        how='inner'
    )
    print(f"匹配成功 {len(merged_data)} 条记录")
    
    # 5. 处理日期和价格
    print("处理日期格式...")
    merged_data['formatted_date'] = merged_data['announced_date'].apply(process_date)
    
    print("处理价格格式...")
    merged_data['formatted_price'] = merged_data['price'].apply(process_price)
    
    # 6. 创建最终结果表格
    result_df = pd.DataFrame({
        'model_code': merged_data['original_model_code'],
        'device_name': merged_data['device_name'],
        'announced_date': merged_data['formatted_date'],
        'price': merged_data['formatted_price'],
        'manufacture': merged_data['clientmanufacture']
    })
    
    # 7. 保存结果
    output_filename = 'processed_phone_data.csv'
    result_df.to_csv(output_filename, index=False, encoding='utf-8')
    print(f"结果已保存到 {output_filename}")
    print(f"最终结果包含 {len(result_df)} 条记录")
    
    # 8. 显示样例数据
    print("\n样例数据预览:")
    print(result_df.head(10))
    
    # 9. 数据统计
    print(f"\n数据统计:")
    print(f"总记录数: {len(result_df)}")
    print(f"有发布日期的记录: {len(result_df[result_df['announced_date'] != ''])}")
    print(f"有价格的记录: {len(result_df[result_df['price'] != ''])}")
    print(f"品牌分布:")
    print(result_df['manufacture'].value_counts())

if __name__ == "__main__":
    main()