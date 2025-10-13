import re
import os
import time
from pathlib import Path
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console
from get_danmu.utils.sqlite_orm import SQLiteORM
from get_danmu.utils.app import create_danmu_app


# 处理不同rich版本的兼容性
try:
    from rich.progress import PercentageColumn
    has_percentage_column = True
except ImportError:
    has_percentage_column = False

console = Console()
# Web服务类
class DanmuWebServer:
    def __init__(self, port:int=80, db_path=""):
        self.port = port
        self.db_path = db_path
        
        # 用户可在此初始化Flask应用
        # self.app = Flask(__name__)

    def run(self):
        """启动Web服务，实际逻辑由用户实现"""
        # console.print(f"[green]Web弹幕服务启动中，端口: {self.port}")
        console.print(f"[green]数据库路径: {self.db_path}")
        # console.print("[yellow]提示: 请在DanmuWebServer类中实现Flask后端逻辑")
        # 确保目录存在
        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path)
        
        self.db_path=str(Path(self.db_path)).replace("\\", "/")
        # 拼接数据库文件完整路径
        custom_db_path = "sqlite:///"+self.db_path+ '/danmu_data.db'
        print(custom_db_path)
        custom_port = self.port
        app = create_danmu_app(
            db_path=custom_db_path,  # 传入自定义数据库地址
            compress_level=None  # 若不需要压缩，可改为 compress_level=None
        )
        app.run(
                host="0.0.0.0",  # 允许外部访问
                port=custom_port,  # 自定义端口
                debug=False,  # 生产环境建议关闭 debug
                threaded=True  # 开启多线程处理请求
            )

class DanmuGetter:
    def __init__(self, url, proxy=None, cookie_path=None,resettime=False,db_path:str='',save_to_db:bool=False):
        """
        初始化弹幕获取器
        
        参数:
            url: 视频URL（字符串）
            proxy: 代理服务器（字符串或None）
            cookie_path: cookie文件路径（字符串或None）
        """
        self.db_path = db_path
        self.save_to_db=save_to_db



        # 确保URL是字符串类型
        if not isinstance(url, str) or not url.strip():
            raise ValueError("URL必须是有效的字符串")
        self.url = url.strip()
        
        # 处理代理，确保是字符串或None
        self.proxy = None
        if proxy is not None:
            if isinstance(proxy, str) and proxy.strip():
                self.proxy = proxy.strip()
            else:
                console.print(f"[yellow]警告: 无效的代理配置，将忽略[/yellow]")

        proxies = self._get_proxy_dict()
        
        # 处理Cookie
        self.cookies = None
        if cookie_path:
            self._load_cookies(cookie_path)
        
        # 时间范围（秒）
        self.start_second = None
        self.end_second = None

        # 是否重置开始时间
        self.resettime=resettime
        
        # 输出配置
        self.data_type = "csv"  # 默认csv格式
        self.save_path = os.getcwd()
        
        # 确保保存目录存在
        Path(self.save_path).mkdir(parents=True, exist_ok=True)

        #输出api平台
        self.api='未知'

        # 选择api
        if 'v.qq.com' in self.url:
            from get_danmu.api.danmu_tx import TencentFetcher
            self.fetcher = TencentFetcher(url=self.url,proxy=proxies)
            self.api='腾讯视频'
        elif 'bilibili.com' in self.url:
            if not self.cookies:
                console.print("[yellow]警告:获取BiliBili时需要指定有效的Cookie路径,以获取更多弹幕[/yellow]")
                # return
            from get_danmu.api.danmu_bilibili import BilibiliFetcher
            self.fetcher = BilibiliFetcher(url=self.url,proxy=proxies,cookie=self.cookies)
            self.api='BiliBili'

        elif 'iqiyi.com' in self.url:
            from get_danmu.api.danmu_iqiyi import IqiyiFetcher
            self.fetcher = IqiyiFetcher(url=self.url,proxy=proxies)
            self.api='爱奇艺'
        elif 'youku.com' in self.url:
            if not self.cookies:
                console.print("[red]错误:获取优酷时必须指定有效的Cookie路径[/red]")
                return
            from get_danmu.api.danmu_youku import YoukuFetcher
            self.fetcher = YoukuFetcher(url=self.url,proxy=proxies,cookie=self.cookies)
            self.api='优酷'
        elif 'mgtv.com' in self.url:
            from get_danmu.api.danmu_mgtv import MgtvFetcher
            self.fetcher = MgtvFetcher(url=self.url,proxy=proxies)
            self.api='芒果TV'
            

    def _load_cookies(self, cookie_path):
        """加载cookie文件，确保参数正确"""
        try:
            # 验证路径是字符串
            if not isinstance(cookie_path, str) or not cookie_path.strip():
                console.print(f"[yellow]警告: 无效的Cookie路径，将忽略[/yellow]")
                return
                
            cookie_path = cookie_path.strip()
            # 检查文件是否存在
            if not os.path.exists(cookie_path):
                console.print(f"[yellow]警告: Cookie文件不存在 - {cookie_path}[/yellow]")
                return
                
            # 读取cookie文件
            with open(cookie_path, 'r', encoding='utf-8') as f:
                self.cookies = f.read().strip()
                
            # 解析为字典格式
            # self.cookies = {}
            # for line in cookie_content.split(';'):
            #     line = line.strip()
            #     if '=' in line:
            #         key, value = line.split('=', 1)
            #         self.cookies[key.strip()] = value.strip()
                    
            console.print(f"[green]成功加载Cookie[/green]")
            
        except Exception as e:
            console.print(f"[yellow]加载Cookie时出错: {str(e)}，将忽略Cookie[/yellow]")
            self.cookies = None

    def set_time_range(self, start_second, end_second):
        """设置时间范围，确保参数是整数或None"""
        # 验证开始时间
        if start_second is not None:
            try:
                # 转换为整数
                start_second = int(start_second)
                if start_second < 0:
                    raise ValueError("开始时间不能为负数")
                self.start_second = start_second
            except (ValueError, TypeError):
                console.print(f"[yellow]警告: 无效的开始时间，将忽略[/yellow]")
        
        # 验证结束时间
        if end_second is not None:
            try:
                # 转换为整数
                end_second = int(end_second)
                if end_second < 0:
                    raise ValueError("结束时间不能为负数")
                self.end_second = end_second
            except (ValueError, TypeError):
                console.print(f"[yellow]警告: 无效的结束时间，将忽略[/yellow]")
        
        # 验证时间范围有效性
        if self.start_second is not None and self.end_second is not None:
            if self.start_second >= self.end_second:
                console.print(f"[yellow]警告: 开始时间应小于结束时间，将交换两者[/yellow]")
                self.start_second, self.end_second = self.end_second, self.start_second

    def set_data_type(self, data_type):
        """设置数据类型，只允许csv和xml"""
        if isinstance(data_type, str) and data_type.strip().lower() in ['csv', 'xml']:
            self.data_type = data_type.strip().lower()
            console.print(f"[green]输出格式设置为: {self.data_type}[/green]")
        else:
            console.print(f"[yellow]警告: 无效的数据类型，使用默认值 'csv'[/yellow]")
            self.data_type = "csv"

    def set_save_path(self, save_path):
        """设置保存路径，确保是字符串且目录存在"""
        if not isinstance(save_path, str) or not save_path.strip():
            console.print(f"[yellow]警告: 无效的保存路径，使用默认路径[/yellow]")
            return
            
        save_path = save_path.strip()
        try:
            Path(save_path).mkdir(parents=True, exist_ok=True)
            self.save_path = save_path
            console.print(f"[green]保存路径设置为: {save_path}[/green]")
        except Exception as e:
            console.print(f"[yellow]警告: 无效的保存路径 - {str(e)}，使用默认路径[/yellow]")

    def _get_proxy_dict(self):
        """将代理转换为requests库需要的格式"""
        if not self.proxy:
            return None
            
        try:
            # 确保代理是字符串
            if not isinstance(self.proxy, str) or not self.proxy.strip():
                return None
                
            proxy_str = self.proxy.strip()
            # 检查是否包含协议
            if not proxy_str.startswith(('http://', 'https://')):
                proxy_str = f'http://{proxy_str}'
                
            return {
                'http': proxy_str,
                'https': proxy_str
            }
        except Exception as e:
            console.print(f"[yellow]警告: 代理格式无效 - {str(e)}，将不使用代理[/yellow]")
            return None

    def _save_as_csv_sqlite(self, danmu_data,title):
        try:
            if not os.path.exists(self.db_path):
                os.makedirs(self.db_path)
        except:
            console.print(f"[red]错误: 请使用get-danmu --db path 指定数据库存放位置后再运行方可保存至数据库[/red]")
            self._save_as_csv(self.save_path, danmu_data)
            return 
        self.db_path=str(Path(self.db_path)).replace("\\", "/")
        # 拼接数据库文件完整路径
        self.custom_db_path = self.db_path+ '/danmu_data.db'

        file_path=self.db_path+'/danmu_data/'
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        match=re.search(r'第(\d+)话|第(\d+)集',title)
        try:
            number = match.group(1) if match.group(1) else match.group(2)
            animeTitle=title.split(match.group(0))[0].rstrip()
        except:
            number=None
            animeTitle=title.split()[0]
        
        if not number:
            file_name=animeTitle
        else:
            file_name=animeTitle+f' S1E{int(number)}'
        
        file_name_queren=console.input(f'[yellow]确认文件名:[/yellow][green]{file_name}[/green]\n请输入文件名(回车代表确认):')
        if file_name_queren:
            file_name=file_name_queren
            animeTitle=file_name.split()[0]
            try:number=file_name.split('E')[1]
            except:number=None

        episodeTitle=animeTitle
        if number:
            episodeTitle=f'第{int(number)}集'


        db_orm = SQLiteORM(db_name=self.custom_db_path)
        episodeId=int(db_orm.get_lang_id())+1

        self._save_as_csv(file_path+f"{file_name}.csv", danmu_data)
        self.save_path=file_path+f"{file_name}.csv"
        db_orm.add_episode(animeTitle=animeTitle,fileName=file_name
                       ,animeId=episodeId,episodeId=episodeId,episodeTitle=episodeTitle,file=file_path+f"{file_name}.csv"
                       ,imageUrl='',api=self.api,api_info={"id":self.url,"start_time":self.start_second if self.start_second else 0,'end_time':self.end_second if self.end_second else 0})

        # print(file_path,title,number,animeTitle,episodeId,file_name,episodeTitle)
        # AnimeEpisode

    def _save_as_csv(self, file_path, danmu_data):
        """将弹幕数据保存为CSV格式"""
        id=1
        with open(file_path, 'w', encoding='utf-8-sig') as f:
            # 写入表头
            f.write("cid,p,m\n")
            # 写入数据
            for item in danmu_data:
                if self.resettime and self.start_second:
                    time_offset=item["time_offset"]/1000-self.start_second
                    if time_offset<=0:
                        continue
                else:
                    time_offset=item["time_offset"]/1000
                f.write(f"""{id},"{time_offset:.3f},{item['mode']},{item['color']},[get-danmu]{id}",{item['content']}\n""")
                id+=1

    def _save_as_xml(self, file_path, danmu_data):
        """将弹幕数据保存为XML格式"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<i><chatserver>chat.bilibili.com</chatserver><chatid>10000</chatid><mission>0</mission><maxlimit>8000</maxlimit><source>e-r</source>')
            for item in danmu_data:
                f.write('<d p="')
                if self.resettime and self.start_second:
                    time_offset=item["time_offset"]/1000-self.start_second
                    if time_offset<=0:
                        continue
                else:
                    time_offset=item["time_offset"]/1000

                f.write(f'''{time_offset:.3f},{item["mode"]},{item["font_size"]},{item["color"]},
                {item.get("timestamp", int(time.time()))},0,0,0">{item['content']}''')

                f.write('</d>')

            f.write('</i>')

    def run(self):
        try:
            # 准备参数
            
            
            
            # 配置进度条组件
            progress_columns = [
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                PercentageColumn() if has_percentage_column else TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("剩余时间:"),
                TimeRemainingColumn(),
            ]
            
            # 创建进度条
            with Progress(*progress_columns, transient=True) as progress:

                #  创建进度任务（初始total设为100，后续会更新）
                task = progress.add_task("[cyan]正在获取弹幕...", total=100)
                
                # 进度回调函数
                def update_progress(current, total):
                    # 更新总任务量（首次调用时设置正确的total）
                    if progress.tasks[task].total != total:
                        progress.update(task, total=total)
                    # 更新当前进度
                    progress.update(task, completed=current)
                
                # 4. 调用Fetcher并传入回调函数
                danmu_data,duration,title = self.fetcher.run(
                    start_second=self.start_second,
                    end_second=self.end_second,
                    progress_callback=update_progress  # 传递进度回调
                )
                
                # 5. 完成后更新状态
                progress.update(task, description="[green]弹幕获取完成", completed=progress.tasks[task].total)
            
            # # 生成保存路径并保存文件（与之前相同）
            filename = f"{title}.{self.data_type}"
            save_path = os.path.join(self.save_path, filename)
            self.save_path=save_path
            console.print(f"[green]成功获取 {len(danmu_data)} 条弹幕[/green]")
            # self.end_second=duration
            
            # test
            # danmu_data=[]
            # title='云深不知梦 第1话 血色婚礼'
            # save_path=self.db_path

            
            if self.save_to_db:
                self._save_as_csv_sqlite(danmu_data,title)
            else:
                if self.data_type == 'csv':
                    self._save_as_csv(save_path, danmu_data)
                else:
                    self._save_as_xml(save_path, danmu_data)
            


            return {
                'count': len(danmu_data),
                'save_path': self.save_path
            }
            
        except Exception as e:
            console.print(f"[red]错误: {str(e)}[/red]")
            raise

