import os
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from sqlalchemy.exc import SQLAlchemyError
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from get_danmu.api.danmu_bilibili import BilibiliFetcher
from get_danmu.api.danmu_iqiyi import IqiyiFetcher
from get_danmu.api.danmu_youku import YoukuFetcher
from get_danmu.api.danmu_mgtv import MgtvFetcher
from get_danmu.api.danmu_tx import TencentFetcher
# 导入数据模型和ORM类
from get_danmu.utils.sqlite_orm import SQLiteORM, AnimeEpisode
# 处理不同rich版本的兼容性
try:
    from rich.progress import PercentageColumn
    has_percentage_column = True
except ImportError:
    has_percentage_column = False



class DanmuDataManager:
    def __init__(self, db_path: str = "", proxy=None, cookie_path=None,resettime=None):
        self.console = Console()
        if not db_path:
            self.console.print("❌ 数据库路径不能为空", style="red")
        self.db = SQLiteORM(db_name=db_path)
        self.current_results = []  # 存储当前检索结果

        # 处理Cookie
        self.cookies = None
        if cookie_path:
            self._load_cookies(cookie_path)
        
        # 处理代理，确保是字符串或None
        self.proxy = None
        if proxy is not None:
            if isinstance(proxy, str) and proxy.strip():
                self.proxy = proxy.strip()
            else:
                self.console.print(f"[yellow]警告: 无效的代理配置，将忽略[/yellow]")
        self.proxies = self._get_proxy_dict()

        # 是否重置开始时间
        self.resettime=resettime

        

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
            self.console.print(f"[yellow]警告: 代理格式无效 - {str(e)}，将不使用代理[/yellow]")
            return None

    def _load_cookies(self,cookie_path):
        """加载cookie文件，确保参数正确"""
        try:
            # 验证路径是字符串
            if not isinstance(cookie_path, str) or not cookie_path.strip():
                self.console.print(f"[yellow]警告: 无效的Cookie路径，将忽略[/yellow]")
                return
            cookie_path = cookie_path.strip()
            # 检查文件是否存在
            if not os.path.exists(cookie_path):
                self.console.print(f"[yellow]警告: Cookie文件不存在 - {cookie_path}[/yellow]")
                return
            # 读取cookie文件
            with open(cookie_path, 'r', encoding='utf-8') as f:
                self.cookies = f.read().strip()
            self.console.print(f"[green]成功加载Cookie[/green]")
        except Exception as e:
            self.console.print(f"[yellow]加载Cookie时出错: {str(e)}，将忽略Cookie[/yellow]")
            self.cookies = None

    def print_welcome(self):
        """显示欢迎界面"""
        welcome_text = Text("📊 弹幕数据管理工具", style="bold magenta")
        welcome_text.append("\n请按照提示进行操作，输入 'q' 退出", style="dim")
        self.console.print(Panel(welcome_text, expand=False))

    def display_records(self, records:AnimeEpisode):
        """用表格展示记录"""
        if not records:
            self.console.print("⚠️ 没有找到匹配的记录", style="yellow")
            return

        table = Table(title="检索结果", show_header=True, header_style="bold blue")
        table.add_column("ID", style="dim", width=5)
        table.add_column("动画标题", width=25)
        table.add_column("文件名", width=30)
        table.add_column("剧集ID", width=8)
        table.add_column("API", width=10)
        table.add_column("添加时间", width=18)

        for record in records:
            table.add_row(
                str(record.id),
                record.animeTitle,
                record.fileName,
                str(record.episodeId),
                record.api or "无",
                record.startDate.strftime("%Y-%m-%d %H:%M")
            )

        self.console.print(table)
        self.current_results = records  # 保存当前结果用于后续操作

    def search_by_filename(self):
        """根据文件名检索记录"""
        self.console.print("\n🔍 文件名检索", style="bold green")
        filename = Prompt.ask("请输入文件名关键词", default="")
        
        if not filename.strip():
            self.console.print("❌ 关键词不能为空", style="red")
            return

        try:
            with self.console.status("正在检索数据库...", spinner="dots"):
                results = self.db.filter_episodes(fileName=filename)
            self.console.print(f"✅ 找到 {len(results)} 条匹配记录", style="green")
            self.display_records(results)
        except SQLAlchemyError as e:
            self.console.print(f"❌ 检索失败: {str(e)}", style="red")

    def modify_record(self):
        """修改指定记录"""
        if not self.current_results:
            self.console.print("⚠️ 请先执行检索操作", style="yellow")
            return

        try:
            record_id = Prompt.ask("请输入要修改的记录ID", default="")
            if not record_id.isdigit():
                self.console.print("❌ ID必须是数字", style="red")
                return

            record = self.db.filter_episodes(id=int(record_id))
            if not record:
                self.console.print(f"❌ 未找到ID为 {record_id} 的记录", style="red")
                return

            # 显示当前记录信息
            self.console.print("\n当前记录信息:", style="bold blue")
            self.display_records([record])

            # 选择要修改的字段
            self.console.print("\n可修改的字段: \[animeTitle, episodeTitle, fileName, file, imageUrl, api, api_info]")
            field = Prompt.ask("请输入要修改的字段名", default="").strip()
            
            allowed_fields = ['animeTitle', 'episodeTitle', 'fileName', 'file', 'imageUrl', 'api', 'api_info']
            if field not in allowed_fields:
                self.console.print(f"❌ 不允许修改的字段: {field}", style="red")
                return

            # 获取新值
            current_value = getattr(record, field, "")
            new_value = Prompt.ask(f"请输入新值 (当前: {current_value})", default=str(current_value))

            # 确认修改
            if Confirm.ask(f"确定要将 {field} 修改为 {new_value} 吗?"):
                with self.console.status("正在更新记录...", spinner="dots"):
                    success = self.db.update_by_id(int(record_id), **{field: new_value})
                if success:
                    self.console.print("✅ 记录更新成功", style="green")
                    # 刷新当前结果列表
                    self.current_results = self.db.filter_episodes(
                        fileName=self.current_results[0].fileName if self.current_results else ""
                    )
                else:
                    self.console.print("❌ 记录更新失败", style="red")

        except SQLAlchemyError as e:
            self.console.print(f"❌ 操作失败: {str(e)}", style="red")

    def delete_record(self):
        """删除指定记录"""
        if not self.current_results:
            self.console.print("⚠️ 请先执行检索操作", style="yellow")
            return

        try:
            record_id = Prompt.ask("请输入要删除的记录ID", default="")
            if not record_id.isdigit():
                self.console.print("❌ ID必须是数字", style="red")
                return

            record = self.db.filter_episodes(id=int(record_id))
            if not record:
                self.console.print(f"❌ 未找到ID为 {record_id} 的记录", style="red")
                return

            # 确认删除
            if Confirm.ask(f"确定要删除 ID为 {record_id} 的记录吗?\n标题: {record.animeTitle}", default=False):
                with self.console.status("正在删除记录...", spinner="dots"):
                    success = self.db.delete_by_id(int(record_id))
                if success:
                    self.console.print("✅ 记录删除成功", style="green")
                    # 刷新当前结果列表
                    self.current_results = self.db.filter_episodes(
                        fileName=self.current_results[0].fileName if self.current_results else ""
                    )
                    self.display_records(self.current_results)
                else:
                    self.console.print("❌ 记录删除失败", style="red")

        except SQLAlchemyError as e:
            self.console.print(f"❌ 操作失败: {str(e)}", style="red")

    def update_local_file(self):
        """触发本地文件更新（由用户自行实现具体逻辑）"""
        if not self.current_results:
            self.console.print("⚠️ 请先执行检索操作", style="yellow")
            return

        try:
            record_id = Prompt.ask("请输入要更新本地文件的记录ID", default="")
            if not record_id.isdigit():
                self.console.print("❌ ID必须是数字", style="red")
                return

            record = self.db.filter_episodes(id=int(record_id))
            if not record:
                self.console.print(f"❌ 未找到ID为 {record_id} 的记录", style="red")
                return

            self.console.print(Panel(
                f"即将更新本地文件关联的记录:\n"
                f"ID: {record.id}\n"
                f"文件名: {record.fileName}\n"
                f"文件路径: {record.file or '未设置'}",
                title="本地文件更新",
                border_style="cyan"
            ))

            if Confirm.ask("确认执行本地文件更新操作吗?", default=False):
                # 这里仅作为占位，实际逻辑由用户实现
                # print(record.file,record.api_info,self.cookies,self.proxies)
                video_url=record.api_info.get('id',None)
                start_second=record.api_info.get('start_second',None)
                end_second=record.api_info.get('end_second',None)
                if start_second==0:start_second=None
                if end_second==0:end_second=None
                if not video_url:
                    self.console.print(f"❌ 操作失败: 数据库缺少关键参数无法更新", style="red")
                
                # print(record.file,video_url,start_second,end_second)
                self.download_danmu(url=video_url,save_file_path=record.file,
                                    start_second=start_second,end_second=end_second)


                # self.console.print("\n[italic]提示: 此处应添加本地文件更新的具体逻辑[/italic]", style="blue")
                self.console.print("✅ 本地文件更新完成", style="green")

        except Exception as e:
            self.console.print(f"❌ 操作失败: {str(e)}", style="red")

    def download_danmu(self,url:str='',save_file_path:str='',start_second=None,end_second=None):
            if 'v.qq.com' in url:
                danmu_api=TencentFetcher(url=url,proxy=self.proxies)
            elif 'bilibili.com' in url:
                if not self.cookies:
                    self.console.print("[yellow]警告:获取BiliBili时需要指定有效的Cookie路径,以获取更多弹幕[/yellow]")
                danmu_api=BilibiliFetcher(url=url,proxy=self.proxies,cookie=self.cookies)
            elif 'mgtv.com' in url:
                danmu_api=MgtvFetcher(url=url,proxy=self.cookies)
            elif 'iqiyi.com' in url:
                danmu_api=IqiyiFetcher(url=url,proxy=self.cookies)
            elif 'youku.com' in url:
                if not self.cookies:
                    self.console.print("[red]错误:获取优酷时必须指定有效的Cookie路径[/red]")
                    return
                danmu_api=YoukuFetcher(url=url,proxy=self.proxies,cookie=self.cookies)
            else:
                self.console.print("[yellow]警告:无法更新的接口[/yellow]")
                return

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
                danmu_data,duration,title = danmu_api.run(
                    start_second=start_second,
                    end_second=end_second,
                    progress_callback=update_progress  # 传递进度回调
                )
                
                # 5. 完成后更新状态
                progress.update(task, description="[green]弹幕获取完成", completed=progress.tasks[task].total)
            self.console.print(f"[green]成功获取 {len(danmu_data)} 条弹幕[/green]")
            self._save_as_csv(save_file_path, danmu_data)

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
    def show_menu(self):
        """显示主菜单"""
        menu = Table(show_header=False, box=None)
        menu.add_row("[1] 🔍 检索文件名", "[2] ✏️ 修改记录")
        menu.add_row("[3] 🗑️ 删除记录", "[4] 💾 更新本地文件")
        menu.add_row("\[q] 🚪 退出", "")
        
        self.console.print("\n[bold cyan]请选择操作:[/bold cyan]")
        self.console.print(menu)
        return Prompt.ask("输入选项", default="1").strip().lower()

    def run(self):
        """运行主程序"""
        self.print_welcome()
        try:
            while True:
                choice = self.show_menu()
                if choice == '1':
                    self.search_by_filename()
                elif choice == '2':
                    self.modify_record()
                elif choice == '3':
                    self.delete_record()
                elif choice == '4':
                    self.update_local_file()
                elif choice in ('q', 'quit', 'exit'):
                    self.console.print("\n👋 感谢使用，再见！", style="bold green")
                    break
                else:
                    self.console.print("❌ 无效的选项，请重新输入", style="red")
        finally:
            self.db.close()