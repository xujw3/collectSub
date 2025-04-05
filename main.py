import yaml
import requests
import base64
import re
import time
import random
import concurrent.futures
import logging
from typing import List, Dict, Any, Tuple
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 超时设置
TIMEOUT = 5

def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    return config

def save_config(config_path: str, config: Dict[str, Any]) -> None:
    """保存配置文件"""
    with open(config_path, 'w', encoding='utf-8') as file:
        yaml.dump(config, file, allow_unicode=True)

def is_valid_subscription(url: str) -> bool:
    """检查订阅链接是否有效"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        
        # 检查HTTP状态码
        if response.status_code != 200:
            logger.warning(f"链接返回非200状态码: {url}, 状态码: {response.status_code}")
            return False
        
        # 尝试解码内容，验证是否为有效的Base64编码
        try:
            content = response.text.strip()
            # 简单验证是否为Base64编码的内容
            if content and len(content) % 4 == 0:
                decoded = base64.b64decode(content)
                # 检查解码后的内容是否包含节点信息的关键字
                text = decoded.decode('utf-8', errors='ignore')
                if 'vmess://' in text or 'trojan://' in text or 'ss://' in text or 'ssr://' in text:
                    return True
            logger.warning(f"链接内容格式不正确: {url}")
            return False
        except Exception as e:
            logger.warning(f"解码失败: {url}, 错误: {e}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"请求失败: {url}, 错误: {e}")
        return False

def check_subscriptions(config: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """检查所有订阅链接的有效性，并返回清理后的配置和删除的链接数量"""
    if 'subscribe' not in config:
        return config, 0
    
    invalid_count = 0
    valid_subscriptions = []
    
    print(f"开始检查 {len(config['subscribe'])} 个订阅链接...")
    
    # 使用线程池加速检查过程
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(is_valid_subscription, url): url for url in config['subscribe']}
        
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                is_valid = future.result()
                if is_valid:
                    valid_subscriptions.append(url)
                else:
                    invalid_count += 1
                    logger.info(f"发现无效链接: {url}")
            except Exception as e:
                logger.error(f"检查链接时出错: {url}, 错误: {e}")
                invalid_count += 1
    
    # 更新配置
    config['subscribe'] = valid_subscriptions
    
    print(f"完成检查。删除了 {invalid_count} 个无效链接，保留了 {len(valid_subscriptions)} 个有效链接。")
    return config, invalid_count

def collect_subscriptions(config_path: str = 'config.yaml') -> None:
    """收集订阅并更新配置文件"""
    # 加载配置
    config = load_config(config_path)
    
    # 检查并清理失效的订阅链接
    updated_config, removed_count = check_subscriptions(config)
    
    # 保存更新后的配置
    save_config(config_path, updated_config)
    
    if removed_count > 0:
        print(f"已删除 {removed_count} 个失效的订阅链接并更新配置文件")
    else:
        print("所有订阅链接都有效，无需更新配置文件")

if __name__ == "__main__":
    try:
        collect_subscriptions()
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
