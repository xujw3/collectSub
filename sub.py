import requests


def postdata(data):
    json_data = {
        'name': 'otc',
        'displayName': '',
        'form': '',
        'mergeSources': '',
        'ignoreFailedRemoteSub': True,
        'icon': 'https://raw.githubusercontent.com/cc63/ICON/main/icons/ClashMeta.png',
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
        ],
        'tag': [
            '第三方',
        ],
        'source': 'remote',
        'url': data,
        'content': '',
        'ua': '',
        'subscriptionTags': [],
        'display-name': '',
    }
    apiurl = os.getenv("APIURL")
    response = requests.patch(
        f'{apiurl}/otc',
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
