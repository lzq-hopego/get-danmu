import time
import math
import xmltodict
import zlib  # 解压
import requests

class IqiyiFetcher():
    """爱奇艺弹幕抓取器"""
    MAX_DURATION = 7200  # 2小时，单位: 秒


    def __init__(self, url:str,proxy:str):
        super().__init__()
        self.url = url
        self.proxy=proxy
        self.proxies = {
"http": self.proxy,
"https": self.proxy,
} if proxy else None
    

    def extract_video_id(self):
        """从URL中提取tvid"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": getattr(self, "url", ""),
            }
            ts = int(time.time() * 1000)
            url = f"https://www.iqiyi.com/prelw/player/lw/lwplay/accelerator.js?format=json&timestamp={ts}"
            resp = requests.get(url, headers=headers, timeout=8,proxies=self.proxies)
            resp.raise_for_status()
            data = resp.json()
            tvid = str(data.get("tvid", ""))
            if not tvid.isdigit():
                return ""
            return tvid
        except Exception:
            return ""

    def get_duration(self, tvid):
        """获取视频时长，异常时返回0"""
        url = f"https://pcw-api.iqiyi.com/video/video/baseinfo/{tvid}?t={int(time.time())}"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            resp = requests.get(url, headers=headers, timeout=8,proxies=self.proxies)
            resp.raise_for_status()
            data = resp.json()
            duration = int(data.get("data", {}).get("durationSec", 0))
            if duration > 0:
                return duration
            return 0
        except Exception:
            return 0  # 网络异常时返回0

    def fetch_danmaku_segment(self, tvid, part):
        """获取单段弹幕数据"""
        try:
            if not tvid or len(tvid) < 4:
                return []
            xx = tvid[-4:-2]
            yy = tvid[-2:]
            url = f"https://cmts.iqiyi.com/bullet/{xx}/{yy}/{tvid}_300_{part}.z"
            resp = requests.get(url, timeout=8,proxies=self.proxies)
            if resp.status_code != 200 or not resp.content:
                return []
            try:
                raw = zlib.decompress(resp.content)
            except Exception:
                return []
            try:
                d = xmltodict.parse(raw)
            except Exception:
                return []

            danmu_data = d.get("danmu", {})
            data_data = danmu_data.get("data", {})
            entries = data_data.get("entry", [])
            if not entries:
                return []
            if isinstance(entries, dict):
                entries = [entries]
            danmakus = []
            for entry in entries:
                bullets = entry.get("list", {}).get("bulletInfo", [])
                if not bullets:
                    continue
                if isinstance(bullets, dict):
                    bullets = [bullets]
                for b in bullets:
                    # 弹幕基础字段
                    try:
                        val = int(b.get("position", 1))
                        if val == 0:
                            mode = 1
                        else:
                            mode = 5
                    except Exception:
                        mode = 1
                    try:
                        font_size_val = int(b.get("font", 25))
                        font_size = {
                            14: 25,
                            20: 30,
                            30: 36,
                            0: 20,
                            2: 18,
                        }.get(font_size_val, 25)
                    except Exception:
                        font_size = 25
                    try:
                        time_offset = float(b.get("showTime", 0)) * 1000
                    except Exception:
                        time_offset = 0
                    try:
                        color_raw = b.get("color", "FFFFFF")
                        if not isinstance(color_raw, str):
                            color_raw = str(color_raw)
                        color = int(color_raw.strip("#"), 16)
                    except Exception:
                        color = 0xFFFFFF
                    try:
                        content = b.get("content", "")
                        if not isinstance(content, str):
                            content = str(content)
                    except Exception:
                        content = ""
                    danmakus.append({
                        "time_offset": time_offset,
                        "mode": mode,
                        "font_size": font_size,
                        "color": color,
                        "timestamp": int(time.time()),
                        "content": content
                    })
            return danmakus
        except Exception:
            return []
        
    def get_video_info(self):
        """
        获取视频信息，返回字典，至少包含 'title' 键
        """
        try:
            tvid = self.extract_video_id()
            if not tvid:
                return {"title": "弹幕"}
            
            info_url = f"https://mesh.if.iqiyi.com/player/lw/video/playervideoinfo?id={tvid}&locale=cn_s"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(info_url, headers=headers, timeout=8,proxies=self.proxies)
            resp.raise_for_status()
            data = resp.json().get("data", {})

            # 视频标题优先使用 vn（集标题），没有则用 an（剧名）
            title = data.get("vn") or data.get("an") or "弹幕"
            return {"title": title}
        except Exception:
            return {"title": "弹幕"}

    def run(self,start_second:int=None,end_second:int=None,progress_callback:object=None):
        """执行抓取任务"""
        try:
            title=self.get_video_info().get('title','')
            tvid = self.extract_video_id()
            start=1
            if start_second:
                start=start_second//300+1
            if not end_second:
                if not tvid:
                    print("无法获取 tvid")
                    return
                duration = self.get_duration(tvid)
            else:
                duration=end_second

            if not isinstance(duration, (int, float)) or duration <= 0:
                print("无法获取视频时长，默认抓取2小时弹幕")
                duration = self.MAX_DURATION

            total_parts = max(1, math.ceil(duration / 300))
            all_danmakus = []
            print(start,total_parts)
            for part in range(start, total_parts+1):
                part_data = self.fetch_danmaku_segment(tvid, part)
                if isinstance(part_data, list):
                    all_danmakus.extend(part_data)
                
                if progress_callback:
                    progress_callback(part,total_parts)
            return all_danmakus,duration,title
        except Exception as e:
            raise f"爱奇艺弹幕抓取出错: {str(e)}"
