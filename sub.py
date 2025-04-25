import requests
import os

def postdata(data):
    json_data = {
        'name': 'hbgx',
        'displayName': 'github抓取',
        'form': '',
        'remark': '',
        'mergeSources': '',
        'ignoreFailedRemoteSub': True,
        'passThroughUA': False,
        'icon': 'https://raw.githubusercontent.com/cc63/ICON/main/icons/AMY.png',
        'process': [
            {
                'type': 'Quick Setting Operator',
                'args': {
                    'useless': 'DISABLED',
                    'udp': 'DEFAULT',
                    'scert': 'DEFAULT',
                    'tfo': 'DEFAULT',
                    'vmess aead': 'DEFAULT',
                },
            },
            {
                'type': 'Script Operator',
                'args': {
                    'content': 'https://raw.githubusercontent.com/xujw3/other/refs/heads/main/rename.js#flag&noCache&clear',
                    'mode': 'link',
                },
                'id': '36934923.422785416',
                'disabled': False,
            },
        ],
        'subUserinfo': 'upload=1000000000000; download=1000000000000; total=100000000000000; expire=4115721600; reset_day=1; plan_name=VIP1; app_url=https://sub.xujw.dpdns.org',
        'proxy': '',
        'tag': [
            '第三方',
        ],
        'subscriptionTags': [],
        'source': 'remote',
        'url': data,
        'content': '',
        'ua': 'Clash Verge/1.7.1',
        'display-name': 'github抓取',
    }
    apiurl = os.getenv("APIURL")
    response = requests.patch(
        f'{apiurl}/hbgx',
        json=json_data,
    )
    return response

def getdata(file_path):
    sub_list = []
    in_sub_list = False
    
    # 针对不同文件类型的处理
    file_name = os.path.basename(file_path)
    
    # 对于config_clash.txt、config_v2.txt和config-loon.txt使用相同的处理逻辑
    if file_name in ["config_clash.txt", "config_v2.txt", "config_loon.txt"]:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped_line = line.strip()
                if stripped_line:  # 只要不是空行就添加
                    sub_list.append(stripped_line)
    else:
        # 原有的处理逻辑（针对其他文件，如config_sub_store.txt）
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped_line = line.strip()
                if stripped_line == '-- sub_list --':
                    in_sub_list = True
                elif stripped_line.startswith('--') and in_sub_list:
                    break  # 遇到下一个段落，停止提取
                elif in_sub_list and stripped_line:
                    sub_list.append(stripped_line)
    
    return sub_list  # 返回列表而不是字符串，便于后续合并

if __name__ == "__main__":
    # 更新需要处理的文件列表，增加了config_v2.txt和config-loon.txt
    paths = ["./config_sub_store.txt", "./config_clash.txt", "./config_v2.txt", "./config_loon.txt"]
    combined_results = []
    
    # 收集所有结果
    for path in paths:
        if os.path.exists(path):  # 确保文件存在
            result = getdata(path)
            combined_results.extend(result)  # 使用extend合并列表
        else:
            print(f"警告: 文件 {path} 不存在，已跳过。")
    
    # 将合并后的结果转换为字符串
    final_result = '\n'.join(combined_results)
    print(postdata(final_result).text)
