import re
from urllib.parse import urljoin, urlparse, urldefrag

from pyquery import PyQuery

from settings import outsite_asset
from utils import logger, empty_link_pattern, get_main_site, url_filter
from transform import trans_to_local_link

def get_page_charset(page_content):
    '''
    从页面内容中获取编码类型, 默认为utf-8
    '''
    pq = PyQuery(page_content)
    charset = 'utf-8'
    meta1 = pq('meta[http-equiv]').attr('content')
    meta2 = pq('meta[charset]').attr('charset')
    if meta1 is not None:
        res = re.findall(r'charset\s*=\s*(\S*)\s*;?', meta1)
        if len(res) != 0: charset = res[0]
    if meta2 is not None: charset = meta2
    return charset

def parse_linking_pages(pq_selector, task, callback = None): 
    '''
    分别解析页面中的a, iframe等元素的链接属性, 
    得到http(s)://式的url, 并调用callback入队列.
    注意: pq_selector为PyQuery选择器, 引用类型, 因为此函数中会修改元素链接为本地文件路径, 
        不可以直接传递string类型的页面内容.
    '''
    a_list = pq_selector('a')
    _parse_linking_pages(a_list, 'href', task, callback=callback)

def _parse_linking_pages(node_list, attr_name, task, callback = None):
    '''
    处理页面中a标签, 将页面本身的url与a标签中的地址计算得到实际可访问的url, 然后加入队列.
    同时修改原页面内容中a标签的链接属性值, 使得这些链接可指向下载到本地的html文件.
    '''
    main_site = get_main_site()
    for node_item in node_list:
        url_attr = PyQuery(node_item).attr(attr_name)
        if url_attr is None or re.search(empty_link_pattern, url_attr): continue

        ## 拼接url并忽略url中的井号
        full_url = urljoin(origin_url, url_attr)
        full_url = urldefrag(full_url).url
        ## 如果不满足过滤规则则跳过
        if not url_filter(full_url, url_type='page'): continue

        ## 重设链接地址为本地路径
        local_link = trans_to_local_link(full_url, 'page')
        PyQuery(node_item).attr(attr_name, local_link)
        new_task = {
            'url': full_url,
            'url_type': 'page',
            'refer': task['url'],
            'depth': task['depth'] + 1,
            'failed_times': 0,
        }
        if callback: callback(new_task)

def parse_linking_assets(pq_selector, task, callback = None): 
    '''
    分别解析页面中的link, script, img等元素的链接属性, 
    得到http(s)://式的url, 并调用callback入队列.
    注意: pq_selector为PyQuery选择器, 引用类型, 因为此函数中会修改元素链接为本地文件路径, 
        不可以直接传递string类型的页面内容.
    '''
    link_list = pq_selector('link')
    _parse_linking_assets(link_list, 'href', task, callback)

    script_list = pq_selector('script')
    _parse_linking_assets(script_list, 'src', task, callback)

    img_list = pq_selector('img')
    _parse_linking_assets(img_list, 'src', task, callback)

def _parse_linking_assets(node_list, attr_name, task, callback):
    main_site = get_main_site()
    for node_item in node_list:
        url_attr = PyQuery(node_item).attr(attr_name)
        if url_attr is None or re.search(empty_link_pattern, url_attr): 
            continue

        ## 拼接url并忽略url中的井号
        full_url = urljoin(task['url'], url_attr)
        full_url = urldefrag(full_url).url
        ## 如果不满足过滤规则则跳过
        if not url_filter(full_url, url_type='asset'): continue

        ## 重设链接地址为本地路径
        local_link = trans_to_local_link(full_url, 'asset')
        PyQuery(node_item).attr(attr_name, local_link)
        new_task = {
            'url': full_url,
            'url_type': 'asset',
            'refer': task['url'],
            'depth': task['depth'] + 1,
            'failed_times': 0,
        }
        if callback: callback(new_task)

def parse_css_file(content, task, callback = None):
    '''
    处理css文件中对静态资源的引用, 
    将引用的静态资源加入队列, 
    再转换为本地地址后返回css文件内容(byte类型)
    '''
    ## css中可能包含url属性,或者是background-image属性的引用路径, 
    ## 格式可能为url('./bg.jpg'), url("./bg.jpg"), url(bg.jpg)
    ## 如下， import_list可能是[('', '', 'bg.jpg'), ('', '', 'logo.png')]
    ## 元组中前两个空格表示匹配到的都是url(bg.jpg)这种形式的属性
    import_pattern = r'url\(\'(.*?)\'\)|url\(\"(.*?)\"\)|url\((.*?)\)'
    match_list = re.findall(import_pattern, content)
    for match_item in match_list:
        for match_url in match_item:
            ## url属性的匹配模式有3种, 只有一种会被匹配上, 另外两种就是空
            ## 如果为空, 或是引入了base64数据, 就跳过不进行处理
            if match_url == '' \
                or match_url.startswith('data') \
                or re.search(empty_link_pattern, match_url): 
                continue

            full_url = urljoin(task['url'], match_url)
            ## 如果不满足过滤规则则跳过
            if not url_filter(full_url, url_type='asset'): continue
            local_link = trans_to_local_link(full_url, 'asset')
            new_task = {
                'url': full_url,
                'url_type': 'asset',
                'refer': task['url'],
                'depth': task['depth'] + 1,
                'failed_times': 0,
            }
            if callback: callback(new_task)
            content = content.replace(match_url, local_link)
    return content.encode('utf-8')
