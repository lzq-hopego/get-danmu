import math,time
import requests,re
from get_danmu.utils import dm_pb2
from google.protobuf import text_format

my_seg = dm_pb2.DmSegMobileReply()


id_pattern = re.compile(r'^id:\s+(\d+)$', re.MULTILINE)
progress_pattern = re.compile(r'^progress:\s+(\d+)$', re.MULTILINE)
content_pattern = re.compile(r'^content:\s+"([^"]+)"$', re.MULTILINE)
color_pattern = re.compile(r'^color:\s+(\d+)$', re.MULTILINE)
mode_pattern = re.compile(r'^mode:\s+(\d+)$', re.MULTILINE)



class BilibiliFetcher():
    """B站弹幕抓取器"""


    def __init__(self, url:str,proxy:str,cookie:str=''):
        super().__init__()
        self.url = url
        self.proxy=proxy
        self.proxies = {
"http": self.proxy,
"https": self.proxy,
} if proxy else None
        self.headers={
            'user-agent':'''Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'''
            ,'cookie':''
            }
        self.headers['cookie']=cookie

    def get_video_info(self):
        """
        获取视频的 cid (弹幕 ID)
        """
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(self.url, headers=self.headers,proxies=self.proxies)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch video page: {response.status_code}")
        html = response.text

        # 提取 cid
        cid_match = re.search(r'"cid":(\d+),', html)
        cid = cid_match.group(1) if cid_match else None

        # 提取标题
        title_match = re.search(r'<meta itemProp="name" content="([^"]+)"', html)
        title = title_match.group(1) if title_match else ""

        time_length=re.search(r'"timelength":(\d+)', html)
        time_length = int(time_length.group(1)) if time_length else 0
        
        video_data = {"cid": cid, "title": title,'time_length':time_length}
        return video_data
    


# oid='1110706533'

# url = 'https://api.bilibili.com/x/v2/dm/wbi/web/seg.so'
# ?type=1&oid=1110706533&pid=560622601&segment_index=1

    def run(self,start_second:int=None,end_second:int=None,progress_callback:object=None):
        video_data = self.get_video_info()
        cid=video_data.get('cid')
        title=video_data.get('title')
        time_length=video_data.get('time_length')

        segment_index=math.ceil(time_length/360000)
        current_segment_index=1

        if start_second:
            current_segment_index=start_second//360+1
        if end_second:
            segment_index=math.ceil(end_second/360)
        # print(segment_index,time_length)
        id=0
        data_upload=[]

        while True:
            params = {
                'type':1,         #弹幕类型
                'oid':cid,    #cid
                'segment_index':current_segment_index #弹幕分段
            }
            
            resp = requests.get('https://api.bilibili.com/x/v2/dm/wbi/web/seg.so',params,headers=self.headers,proxies=self.proxies)
            
            if resp.status_code!=200:
                break
            data = resp.content
            my_seg.ParseFromString(data)
            
            

            for i in my_seg.elems:
                id+=1
                parse_data = text_format.MessageToString(i, as_utf8=True)
                progress_match = progress_pattern.search(parse_data)
                content_match = content_pattern.search(parse_data)
                color_match = color_pattern.search(parse_data)
                mode_match = mode_pattern.search(parse_data)
                if not progress_match:
                    continue
                if not content_match:
                    continue
                data_upload.append({
                        "time_offset": int(progress_match.group(1)),
                        "mode": mode_match.group(1),
                        "font_size": 25,
                        "color": color_match.group(1) if color_match else 16777215,
                        "timestamp": int(time.time()),
                        "content": content_match.group(1)
                    })

            # print(parse_data)
            if progress_callback:
                progress_callback(current_segment_index,segment_index)
            # print(current_segment_index)

            current_segment_index+=1
            if current_segment_index>segment_index:
                break
            
        return data_upload,time_length/1000,title.replace('&amp;nbsp;',' ')
