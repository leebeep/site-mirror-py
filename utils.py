import os
import requests
import hashlib
from urllib.parse import urlparse

from settings import main_url, headers, proxies, output_path

main_site = ''
def get_main_site():
    global main_site
    if main_site == '':
        main_site = urlparse(main_url).netloc
    return main_site

def request_get_async(url, refer):
    '''
    协程形式发起get请求
    return: requests.get()的结果
    '''
    try:
        _headers = headers.copy()
        _headers['Referer'] = refer
        resp = requests.get(url=url, verify=True, headers=_headers, proxies=proxies)
        return (1, resp)
    except requests.exceptions.ConnectionError as err:
        print('连接异常: ', err)
        return (0, err)
    except Exception as err:
        print('请求失败: ', err)
        return (0, err)

def save_file_async(file_path, file_name, byte_content):
    '''
    写入文件, 事先创建目标目录
    '''
    path = output_path + file_path
    if not path.endswith('/'): path = path + '/'
    if not os.path.exists(path): os.makedirs(path)

    try:
        file = open(path + file_name, "wb")
        file.write(byte_content)
        file.close()
        return (1, None)
    except IOError as err:
        print('save Error: ', err, 'path: ', path, 'name: ', file_name)
        return (0, err)

special_chars = {
    '\\': 'xg',
    ':': 'mh',
    '*': 'xh',
    '?': 'wh',
    '<': 'xy',
    '>': 'dy',
    '|': 'sx',
    ' ': 'kg'
}

def convLongPath(file_path, file_name):
    if len(file_name) > 128:
        file_name = hashlib.sha1(file_name).hexdigest()
    if len(file_path) > 128:
        file_path = file_path[0] + hashlib.sha1(file_path).hexdigest()
    return file_path, file_name

def trans_to_local_link(url):
    '''
    @param
        url: 待处理的url
    @return
        file_path: 目标文件的存储目录, 相对路径(不以/开头), 为""时, 表示当前目录
        file_name: 目标文件名称
        local_path: 本地文件存储路径, 用于写入本地html文档中的link/script/img/a等标签的链接属性
    '''
    ## 对于域名为host的url, 资源存放目录为output根目录, 而不是域名文件夹. 默认不设置主host
    main_site = get_main_site()

    urlObj = urlparse(url)
    origin_host = urlObj.netloc
    origin_path = urlObj.path

    local_path = origin_path
    ## 替换url中的特殊字符, 因为存储在本地的文件名称不能包含特殊字符 
    for k, v in special_chars.items():
        if k in local_path: local_path = local_path.replace(k, v)

    # url除去最后的/
    if local_path.endswith('/'): local_path += 'index.html'

    ## 如果该url就是这个站点域名下的，那么无需新建域名目录存放
    ## 如果是其他站点的(需要事先开启允许下载其他站点的配置), 
    ## 则要将资源存放在以站点域名为名的目录下, 路径中仍然需要保留域名部分
    if origin_host != main_site: local_path = origin_host + local_path

    file_name = os.path.basename(local_path)
    file_path = os.path.dirname(local_path)
    # 如果文件名或文件路径过长
    ## file_path, file_name = convLongPath(file_path, file_name)

    if origin_host != main_site: local_path = '/' + local_path

    return file_path, file_name, local_path
