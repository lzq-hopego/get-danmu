
import requests,re,math,time

request=requests.Session()

class MgtvFetcher():
    """芒果TV弹幕抓取器"""


    def __init__(self, url:str,proxy:str):
        super().__init__()
        self.url = url
        self.proxy=proxy
        self.proxies = {
"http": self.proxy,
"https": self.proxy,
} if proxy else None
        
    def run(self,start_second:int=None,end_second:int=None,progress_callback:object=None):
        """执行抓取任务"""

        

        cid,vid=re.findall(r'b/(.*?).html',self.url)[0].split(r'/')

        html=request.get(f"https://pcweb.api.mgtv.com/player/vinfo?video_id={vid}&cid={cid}",proxies=self.proxies)
        html_data=html.json()

        title=html_data['data']['clip_name']+' '+html_data['data']['t2']
        duration=html_data['data']['duration']

        start=0
        if start_second:
            start=start_second//60
        if end_second:
            duration=end_second


        video_info_url=f"https://galaxy.bz.mgtv.com/getctlbarrage?version=8.1.48&abroad=0&vid={vid}&cid={cid}"
        html=request.get(video_info_url,proxies=self.proxies)
        html_data=html.json()
        mgtv_dm_api='https://bullet-ws.hitv.com/'+html_data['data']['cdn_version']

        total_steps=math.ceil(int(duration)/60)
        data_upload=[]

        for i in range(start,total_steps):
            html_dm=request.get(mgtv_dm_api+f'/{i}.json',proxies=self.proxies)
            try:
                dm_data=html_dm.json()['data']['items']
            except:
                print(f'{i}分钟弹幕无法被解析!')
                continue
            for j in dm_data:
                if j['type']==0:
                    mode=1
                elif j['type']==3:
                    mode=5
                else:
                    mode=1
                v2_color=j.get('v2_color',None)
                color=16777215
                if v2_color:
                    color=v2_color['color_left']['r']*256*256+v2_color['color_left']['g']*256+v2_color['color_left']['b']
                data_upload.append({
                        "time_offset": int(j['time']),
                        "mode": mode,
                        "font_size": 25,
                        "color": color,
                        "timestamp": int(time.time()),
                        "content": j.get("content", "")
                    })


            if progress_callback:
                progress_callback(i,total_steps-1)
            # time.sleep(0.1)
        
        return data_upload,duration*60,title
