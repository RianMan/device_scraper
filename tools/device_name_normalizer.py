#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备名称标准化工具 - tools/device_name_normalizer.py
负责设备名称的标准化和匹配
"""

import re
import logging

logger = logging.getLogger(__name__)

class DeviceNameNormalizer:
    """设备名称标准化处理器"""
    
    @staticmethod
    def normalize_motorola_name(model_name):
        """标准化Motorola设备名称"""
        model_name = model_name.strip()
        
        # Motorola特殊处理模式
        patterns = [
            # moto g系列
            (r'moto g\((\d+)\) 5G', r'Moto G\1 5G'),
            (r'moto g\((\d+)\) plus', r'Moto G\1 Plus'),
            (r'moto g\((\d+)\)', r'Moto G\1'),
            (r'moto g (\d+)G', r'Moto G \1G'),
            
            # moto g stylus系列
            (r'moto g stylus 5G - (\d+)', r'Moto G Stylus 5G (\1)'),
            (r'moto g stylus 5G', r'Moto G Stylus 5G'),
            (r'moto g stylus', r'Moto G Stylus'),
            
            # moto e系列
            (r'moto e\((\d+)\) plus', r'Moto E\1 Plus'),
            (r'moto e(\d+)', r'Moto E\1'),
            
            # 通用moto处理
            (r'moto g', r'Moto G'),
            (r'moto e', r'Moto E'),
            (r'^moto\s+', r'Moto '),
        ]
        
        for pattern, replacement in patterns:
            model_name = re.sub(pattern, replacement, model_name, flags=re.IGNORECASE)
        
        # 确保首字母大写
        if model_name.lower().startswith('moto'):
            model_name = 'Moto' + model_name[4:]
        
        return model_name
    
    @staticmethod
    def normalize_samsung_name(model_name):
        """标准化Samsung设备名称"""
        model_name = model_name.strip()
        
        # Samsung型号映射
        samsung_mappings = {
            'SM-J415G': 'Samsung Galaxy J4+',
            'SM-A217M': 'Samsung Galaxy A21s',
            'SM-J810M': 'Samsung Galaxy J8',
            'SM-A730F': 'Samsung Galaxy A8+ (2018)',
            'SM-N976U': 'Samsung Galaxy Note10+ 5G',
            'SM-A920F': 'Samsung Galaxy A9 (2018)',
            'SM-A137F': 'Samsung Galaxy A13',
            'SM-A245F': 'Samsung Galaxy A24',
            'SM-G991B': 'Samsung Galaxy S21',
        }
        
        # 如果是型号代码，尝试映射
        if model_name.startswith('SM-'):
            return samsung_mappings.get(model_name, model_name)
        
        return model_name
    
    @staticmethod
    def normalize_zte_name(model_name):
        """标准化ZTE设备名称"""
        model_name = model_name.strip()
        
        # ZTE型号映射
        zte_mappings = {
            'ZTE 8050': 'ZTE Blade A73',
            'ZTE 8010': 'ZTE Blade V20',
            'ZTE 9050N': 'ZTE Blade A71',
            'ZTE A7040': 'ZTE Blade A7 (2020)',
            'ZTE 9046': 'ZTE Blade A51',
            'ZTE 9045': 'ZTE Blade A31',
            'ZTE A2022L': 'ZTE Blade A52',
            'ZTE Blade V10': 'ZTE Blade V10',
            'ZTE Blade A33s': 'ZTE Blade A33s',
            'ZTE Blade L210': 'ZTE Blade L210',
        }
        
        return zte_mappings.get(model_name, model_name)
    
    @staticmethod
    def normalize_device_name(model_name, brand_hint=None):
        """统一的设备名称标准化"""
        if not model_name:
            return model_name
        
        model_name = model_name.strip()
        
        # 根据品牌提示或名称特征选择处理方式
        if brand_hint:
            brand_lower = brand_hint.lower()
            if 'motorola' in brand_lower:
                return DeviceNameNormalizer.normalize_motorola_name(model_name)
            elif 'samsung' in brand_lower:
                return DeviceNameNormalizer.normalize_samsung_name(model_name)
            elif 'zte' in brand_lower:
                return DeviceNameNormalizer.normalize_zte_name(model_name)
        
        # 根据名称特征自动识别
        model_lower = model_name.lower()
        if model_lower.startswith('moto'):
            return DeviceNameNormalizer.normalize_motorola_name(model_name)
        elif model_name.startswith('SM-'):
            return DeviceNameNormalizer.normalize_samsung_name(model_name)
        elif model_lower.startswith('zte'):
            return DeviceNameNormalizer.normalize_zte_name(model_name)
        
        return model_name
    
    @staticmethod
    def calculate_name_similarity(name1, name2):
        """计算设备名称相似度"""
        if not name1 or not name2:
            return 0.0
        
        name1 = name1.lower().strip()
        name2 = name2.lower().strip()
        
        # 完全匹配
        if name1 == name2:
            return 1.0
        
        # 包含匹配
        if name1 in name2 or name2 in name1:
            return 0.8
        
        # 分词匹配
        words1 = set(re.findall(r'\w+', name1))
        words2 = set(re.findall(r'\w+', name2))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        # Jaccard相似度
        jaccard_similarity = len(intersection) / len(union)
        
        # 品牌匹配加分
        brand_keywords = ['samsung', 'motorola', 'moto', 'zte', 'lg', 'huawei', 'xiaomi', 'oppo', 'vivo']
        brand_match = any(brand in words1 and brand in words2 for brand in brand_keywords)
        
        if brand_match:
            jaccard_similarity += 0.1  # 品牌匹配加分
        
        return min(jaccard_similarity, 1.0)
    
    @staticmethod
    def find_best_device_match(device_links, target_name):
        """智能匹配最佳设备链接"""
        if not device_links:
            return None
        
        # 标准化目标名称
        normalized_target = DeviceNameNormalizer.normalize_device_name(target_name)
        logger.info(f"标准化目标名称: {target_name} -> {normalized_target}")
        
        best_match = None
        best_score = 0
        
        for link in device_links:
            # 获取链接中的设备名称
            device_name = link.get_text(strip=True)
            if not device_name:
                span_tag = link.find('span')
                if span_tag:
                    device_name = span_tag.get_text(strip=True)
            
            if not device_name:
                continue
            
            # 标准化设备名称
            normalized_device = DeviceNameNormalizer.normalize_device_name(device_name)
            
            # 计算相似度分数
            score = DeviceNameNormalizer.calculate_name_similarity(normalized_target, normalized_device)
            
            logger.info(f"候选设备: {device_name} (标准化: {normalized_device}) - 相似度: {score:.2f}")
            
            if score > best_score:
                best_score = score
                best_match = link
        
        if best_match:
            device_name = best_match.get_text(strip=True)
            if not device_name:
                span_tag = best_match.find('span')
                if span_tag:
                    device_name = span_tag.get_text(strip=True)
            logger.info(f"✅ 最佳匹配: {device_name} (相似度: {best_score:.2f})")
            return best_match
        
        # 如果没有好的匹配，返回第一个
        logger.warning(f"⚠️ 未找到好的匹配，使用第一个设备")
        return device_links[0]
    
    @staticmethod
    def infer_brand_from_model(model_code):
        """从型号代码推断品牌"""
        model_lower = model_code.lower()
        
        brand_patterns = {
            'Samsung': [r'^sm-', r'galaxy'],
            'Motorola': [r'^moto', r'motorola'],
            'ZTE': [r'^zte'],
            'LG': [r'^lm-'],
            'Huawei': [r'^alt-', r'huawei'],
            'Xiaomi': [r'^mi ', r'redmi'],
            'OPPO': [r'^cph'],
            'Vivo': [r'^v\d+'],
            'Hisense': [r'hisense'],
            'Tecno': [r'tecno'],
            'Cubot': [r'kingkong'],
            'Ulefone': [r'tank'],
            'Wiko': [r'^w-'],
            'Stellar': [r'stellar'],
            'Shark': [r'shark'],
            'Logic': [r'logic'],
        }
        
        for brand, patterns in brand_patterns.items():
            for pattern in patterns:
                if re.search(pattern, model_lower):
                    return brand
        
        return 'Unknown'
    
    @staticmethod
    def clean_device_name(device_name):
        """清理设备名称"""
        if not device_name:
            return device_name
        
        # 移除多余的空格
        device_name = ' '.join(device_name.split())
        
        # 移除常见的后缀
        suffixes_to_remove = [
            ' - Full phone specifications',
            ' specifications',
            ' specs',
            ' review',
            ' price',
            ' features'
        ]
        
        for suffix in suffixes_to_remove:
            if device_name.endswith(suffix):
                device_name = device_name[:-len(suffix)]
        
        return device_name.strip()
    
    @staticmethod
    def extract_model_variants(device_name):
        """提取设备变体信息"""
        variants = []
        
        # 存储容量变体
        storage_pattern = r'(\d+)\s*(GB|TB)'
        storage_matches = re.findall(storage_pattern, device_name, re.IGNORECASE)
        if storage_matches:
            variants.extend([f"{size}{unit}" for size, unit in storage_matches])
        
        # RAM变体
        ram_pattern = r'(\d+)\s*GB\s*RAM'
        ram_matches = re.findall(ram_pattern, device_name, re.IGNORECASE)
        if ram_matches:
            variants.extend([f"{ram}GB RAM" for ram in ram_matches])
        
        # 网络变体
        if '5G' in device_name.upper():
            variants.append('5G')
        elif '4G' in device_name.upper():
            variants.append('4G')
        
        # 版本变体
        version_patterns = [
            r'Plus|Pro|Max|Mini|Lite|SE',
            r'\((\d{4})\)',  # 年份
        ]
        
        for pattern in version_patterns:
            matches = re.findall(pattern, device_name, re.IGNORECASE)
            variants.extend(matches)
        
        return list(set(variants))  # 去重
    
    @staticmethod
    def is_valid_device_name(device_name):
        """验证设备名称是否有效"""
        if not device_name or device_name.strip() == '':
            return False
        
        # 过滤明显无效的名称
        invalid_patterns = [
            r'^Unknown$',
            r'^N/A',
            r'^TBD',
            r'^Coming Soon',
            r'^\s*',
        ]
        
        for pattern in invalid_patterns:
            if re.match(pattern, device_name, re.IGNORECASE):
                return False
        
        # 至少包含字母
        if not re.search(r'[a-zA-Z]', device_name):
            return False
        
        return True