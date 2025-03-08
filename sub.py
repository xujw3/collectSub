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
        'subUserinfo': 'upload=1000000000000; download=1000000000000; total=100000000000000; expire=4115721600; reset_day=1; plan_name=VIP1; app_url=https://087iu0np-substore.hf.space',
        'proxy': '',
        'tag': [
            '第三方',
        ],
        'subscriptionTags': [],
        'source': 'remote',
        'url': data,
        'content': '',
        'ua': 'Clash',
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

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped_line = line.strip()

            if stripped_line == '-- sub_list --':
                in_sub_list = True
            elif stripped_line.startswith('--') and in_sub_list:
                break  # 遇到下一个段落，停止提取
            elif in_sub_list and stripped_line:
                sub_list.append(stripped_line)

    # 使用 '\n' 作为分隔符
    return '\n'.join(sub_list)


if __name__ == "__main__":
    path = "./config_sub_store.txt"
    print(postdata(getdata(path)).text)
