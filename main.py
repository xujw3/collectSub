import asyncio
import aiohttp
import re
import yaml
import os
import base64
from urllib.parse import quote
from tqdm import tqdm
from loguru import logger

# 全局配置
RE_URL = r"https?://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]"
CHECK_NODE_URL_STR = "https://{}/sub?target={}&url={}&insert=false&config=config%2FACL4SSR.ini"
CHECK_URL_LIST = ['api.dler.io', 'sub.xeton.dev', 'sub.id9.cc', 'sub.maoxiongnet.com']

# -------------------------------
# 配置文件操作
# -------------------------------
def load_yaml_config(path_yaml):
    """读取 YAML 配置文件，如文件不存在则返回默认结构"""
    if os.path.exists(path_yaml):
        with open(path_yaml, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        config = {
            "机场订阅": [],
            "clash订阅": [],
            "v2订阅": [],
            "开心玩耍": [],
            "tgchannel": []
        }
    return config

def save_yaml_config(config, path_yaml):
    """保存配置到 YAML 文件"""
    with open(path_yaml, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)

def get_config_channels(config_file='config.yaml'):
    """
    从配置文件中获取 Telegram 频道链接，
    将类似 https://t.me/univstar 转换为 https://t.me/s/univstar 格式
    """
    config = load_yaml_config(config_file)
    tgchannels = config.get('tgchannel', [])
    new_list = []
    for url in tgchannels:
        parts = url.strip().split('/')
        if parts:
            channel_id = parts[-1]
            new_list.append(f'https://t.me/s/{channel_id}')
    return new_list

# -------------------------------
# 异步 HTTP 请求辅助函数
# -------------------------------
async def fetch_content(url, session, method='GET', headers=None, timeout=15):
    """获取指定 URL 的文本内容"""
    try:
        async with session.request(method, url, headers=headers, timeout=timeout) as response:
            if response.status == 200:
                text = await response.text()
                return text
            else:
                logger.warning(f"URL {url} 返回状态 {response.status}")
                return None
    except Exception as e:
        logger.error(f"请求 {url} 异常: {e}")
        return None

# -------------------------------
# 频道抓取及订阅检查
# -------------------------------
async def get_channel_urls(channel_url, session):
    """从 Telegram 频道页面抓取所有订阅链接，并过滤无关链接"""
    content = await fetch_content(channel_url, session)
    if content:
        # 提取所有 URL，并排除包含“//t.me/”或“cdn-telegram.org”的链接
        all_urls = re.findall(RE_URL, content)
        filtered = [u for u in all_urls if "//t.me/" not in u and "cdn-telegram.org" not in u]
        logger.info(f"从 {channel_url} 提取 {len(filtered)} 个链接")
        return filtered
    else:
        logger.warning(f"无法获取 {channel_url} 的内容")
        return []

async def sub_check(url, session):
    """
    检查订阅链接的有效性：
      - 判断响应头中的 subscription-userinfo 用于机场订阅
      - 判断内容中是否包含 'proxies:' 判定 clash 订阅
      - 尝试 base64 解码判断 v2 订阅（识别 ss://、ssr://、vmess://、trojan://）
    返回一个字典：{"url": ..., "type": ..., "info": ...}
    """
    headers = {'User-Agent': 'ClashforWindows/0.18.1'}
    try:
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status == 200:
                text = await response.text()
                result = {"url": url, "type": None, "info": None}
                # 判断机场订阅（检查流量信息）
                sub_info = response.headers.get('subscription-userinfo')
                if sub_info:
                    nums = re.findall(r'\d+', sub_info)
                    if len(nums) >= 3:
                        upload, download, total = map(int, nums[:3])
                        unused = (total - upload - download) / (1024 ** 3)
                        if unused > 0:
                            result["type"] = "机场订阅"
                            result["info"] = f"可用流量: {round(unused, 2)} GB"
                            return result
                # 判断 clash 订阅
                if "proxies:" in text:
                    result["type"] = "clash订阅"
                    return result
                # 判断 v2 订阅，通过 base64 解码检测
                try:
                    sample = text[:64]
                    decoded = base64.b64decode(sample).decode('utf-8', errors='ignore')
                    if any(proto in decoded for proto in ['ss://', 'ssr://', 'vmess://', 'trojan://']):
                        result["type"] = "v2订阅"
                        return result
                except Exception:
                    pass
                # 若都不满足，则返回未知类型但视为有效
                result["type"] = "未知订阅"
                return result
            else:
                logger.warning(f"订阅检查 {url} 返回状态 {response.status}")
                return None
    except Exception as e:
        logger.error(f"订阅检查 {url} 异常: {e}")
        return None

# -------------------------------
# 节点有效性检测（根据多个检测入口）
# -------------------------------
async def url_check_valid(url, target, session):
    """
    通过遍历多个检测入口检查订阅节点有效性，
    如果任一检测返回状态 200，则认为该节点有效。
    """
    encoded_url = quote(url, safe='')
    for check_base in CHECK_URL_LIST:
        check_url = CHECK_NODE_URL_STR.format(check_base, target, encoded_url)
        try:
            async with session.get(check_url, timeout=15) as resp:
                if resp.status == 200:
                    return url
        except Exception:
            continue
    return None

# -------------------------------
# 主流程：更新订阅与合并
# -------------------------------
async def update_today_sub(session):
    """
    从 Telegram 频道获取最新订阅链接，
    返回一个去重后的 URL 列表
    """
    tg_channels = get_config_channels('config.yaml')
    all_urls = []
    for channel in tg_channels:
        urls = await get_channel_urls(channel, session)
        all_urls.extend(urls)
    return list(set(all_urls))

async def check_subscriptions(urls):
    """
    异步检查所有订阅链接的有效性，
    返回检查结果列表，每个结果为字典 {url, type, info}
    """
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [sub_check(url, session) for url in urls]
        for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="订阅筛选"):
            res = await coro
            if res:
                results.append(res)
    return results

async def check_nodes(urls, target):
    """
    异步检查每个订阅节点的有效性，
    返回检测有效的节点 URL 列表
    """
    valid_urls = []
    async with aiohttp.ClientSession() as session:
        tasks = [url_check_valid(url, target, session) for url in urls]
        for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="节点检测"):
            res = await coro
            if res:
                valid_urls.append(res)
    return valid_urls

def write_url_list(url_list, file_path):
    """将 URL 列表写入文本文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(url_list))
    logger.info(f"已保存 {len(url_list)} 个链接到 {file_path}")

# -------------------------------
# 主函数入口
# -------------------------------
async def main():
    config_path = 'config.yaml'
    config = load_yaml_config(config_path)

    # 使用单个 ClientSession 获取 Telegram 频道订阅链接
    async with aiohttp.ClientSession() as session:
        today_urls = await update_today_sub(session)
    logger.info(f"从 Telegram 频道获得 {len(today_urls)} 个链接")

    # 异步检查订阅链接的有效性
    sub_results = await check_subscriptions(today_urls)
    # 根据检查结果按类型分类
    subs   = [res["url"] for res in sub_results if res and res["type"] == "机场订阅"]
    clash  = [res["url"] for res in sub_results if res and res["type"] == "clash订阅"]
    v2     = [res["url"] for res in sub_results if res and res["type"] == "v2订阅"]
    play   = [f'{res["info"]} {res["url"]}' for res in sub_results if res and res["type"] == "机场订阅" and res["info"]]

    # 合并并更新配置（与原有数据合并）
    config["机场订阅"] = sorted(list(set(config.get("机场订阅", []) + subs)))
    config["clash订阅"] = sorted(list(set(config.get("clash订阅", []) + clash)))
    config["v2订阅"] = sorted(list(set(config.get("v2订阅", []) + v2)))
    config["开心玩耍"] = sorted(list(set(config.get("开心玩耍", []) + play)))
    save_yaml_config(config, config_path)
    logger.info("配置文件已更新。")

    # 写入订阅存储文件（包含流量信息和机场订阅链接）
    sub_store_file = config_path.replace('.yaml', '_sub_store.txt')
    content = "-- play_list --\n\n" + "\n".join(play) + "\n\n-- sub_list --\n\n" + "\n".join(subs)
    with open(sub_store_file, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info(f"订阅存储文件已保存至 {sub_store_file}")

    # 检测“机场订阅”中节点的有效性（例如目标 target 为 "loon"）
    valid_nodes = await check_nodes(subs, "loon")
    valid_file = config_path.replace('.yaml', '_loon.txt')
    write_url_list(valid_nodes, valid_file)

if __name__ == '__main__':
    asyncio.run(main())
