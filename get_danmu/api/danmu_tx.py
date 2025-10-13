import re
import sys
import time
import json
# import pandas as pd
import requests

class TencentFetcher():
    """腾讯视频弹幕抓取器（简洁版）"""
    STEP_MS = 30000
    MAX_DURATION_MS = 7200000
    RETRY_COUNT = 3

    def __init__(self, url,proxy):
        super().__init__()
        self.url = url
        self.proxy=proxy
        self.proxies = {
"http": self.proxy,
"https": self.proxy,
} if proxy else None

    def fetch_page_html(self):
        """缓存页面 HTML"""
        if hasattr(self, "_page_html"):
            return self._page_html
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(self.url, headers=headers, timeout=10,proxies=self.proxies)
            resp.raise_for_status()
            resp.encoding='utf-8'
            self._page_html = resp.text
        except Exception:
            self._page_html = ""
        return self._page_html

    def extract_video_info_from_page(self):
        """从 HTML 直接匹配 currentVideoInfo 后的 vid/duration/title"""
        if hasattr(self, "_video_info"):
            return self._video_info

        info = {"vid": None, "duration": self.MAX_DURATION_MS, "title": "弹幕"}
        html = self.fetch_page_html()

        idx = html.find('currentVideoInfo')
        if idx == -1:
            print("[WARN] 页面中未找到 currentVideoInfo")
            self._video_info = info
            return info

        snippet = html[idx:idx+2000]
        snippet = snippet.replace('undefined', 'null')  # 容错

        # 匹配 vid
        m_vid = re.search(r'"vid"\s*:\s*"([^"]+)"', snippet)
        if m_vid:
            info["vid"] = m_vid.group(1)

        # 匹配 duration
        m_duration = re.search(r'"duration"\s*:\s*(\d+)', snippet)
        if m_duration:
            info["duration"] = int(m_duration.group(1)) * 1000

        # 匹配 title

        m = re.search(r'<meta\s+property="og:title"\s+content="(.*?)"\s*/?>', html)
        if m:
            info["title"] = m.group(1)
        else:
            m2 = re.search(r'<title>(.*?)</title>', html)
            if m2:
                info["title"] = m2.group(1)
        if info.get("title",None):
            title_data=info["title"].split('_')
            if len(title_data)>=5:
                info["title"]=title_data[0]+' 第'+title_data[1]+'集'
            else:
                info["title"]=title_data[0]

        self._video_info = info
        return info

    def get_video_info(self):
        """返回文件名信息"""
        return {"title": self.extract_video_info_from_page().get("title")}

    def get_video_duration(self):
        """返回视频时长（毫秒）"""
        return self.extract_video_info_from_page().get("duration", self.MAX_DURATION_MS)

    def run(self,start_second=None,end_second=None,progress_callback=None):
        """执行弹幕抓取任务"""
        info = self.extract_video_info_from_page()
        self.vid = info.get("vid")
        duration = info.get("duration", self.MAX_DURATION_MS)
        if not self.vid:
            raise "无法提取腾讯视频ID"
            # return

        danmu = []
        # print(start_second,end_second)
        total_steps = max((duration + self.STEP_MS - 1) // self.STEP_MS, 1)
        if end_second:
            total_steps = max((end_second*1000 + self.STEP_MS - 1) // self.STEP_MS, 1)
            duration=end_second*1000
        current_step = 0
        if start_second:
            current_step=start_second*1000 // self.STEP_MS
        start = current_step*self.STEP_MS
        # start=0
        # print(current_step,start)

        while start < duration:
            # end = min(start + self.STEP_MS, duration)
            end =start + self.STEP_MS
            api_url = f"https://dm.video.qq.com/barrage/segment/{self.vid}/t/v1/{start}/{end}"
            block = []
            for attempt in range(self.RETRY_COUNT):
                try:
                    resp = requests.get(api_url, timeout=5,proxies=self.proxies)
                    resp.raise_for_status()
                    try:
                        data = resp.json()
                    except Exception:
                        data = {}
                    block = data.get("barrage_list", []) if isinstance(data, dict) else []
                    break
                except Exception:
                    if attempt == self.RETRY_COUNT - 1:
                        block = []

            for item in block:
                # 弹幕样式处理
                color = 16777215
                mode = 1
                content_style = item.get("content_style", {})
                style = {}
                if isinstance(content_style, dict):
                    style = content_style
                elif isinstance(content_style, str):
                    try:
                        style = json.loads(content_style)
                    except Exception:
                        style = {}
                try:
                    if "gradient_colors" in style and style["gradient_colors"]:
                        color = int(style["gradient_colors"][0], 16)
                    elif "color" in style:
                        color = int(style["color"], 16)
                    if style.get("position") == 1:
                        mode = 5
                except Exception:
                    pass

                try:
                    timestamp = int(float(item.get("create_time", time.time())))
                except Exception:
                    timestamp = int(time.time())
                try:
                    time_offset = int(float(item.get("time_offset", 0)))
                except Exception:
                    time_offset = 0

                content = item.get("content", "")
                if not isinstance(content, str):
                    content = str(content) if content is not None else ""

                danmu.append({
                    "time_offset": time_offset,
                    "mode": mode,
                    "font_size": 25,
                    "color": color,
                    "timestamp": timestamp,
                    "content": content,
                    'cid':item.get("id", 0)
                })

            current_step += 1
            if progress_callback:
                progress_callback(current=current_step,total=total_steps)

            start = end


        return danmu,duration/1000,info.get("title")
