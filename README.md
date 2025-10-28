# get-danmu：多平台弹幕获取与服务工具

get-danmu 是一款基于 Python 开发的命令行工具，专注于**弹幕获取、本地存储与服务搭建**，支持腾讯爱奇艺优酷B站芒果平台，可满足私人影视库的弹幕需求。核心特性包括多平台适配、灵活的数据存储、高效的弹幕服务，适合个人学习与私人使用。

## 一、支持平台

已适配 5 大主流视频平台，覆盖大部分影视内容场景：

- 腾讯视频

- 爱奇艺

- 优酷（**必须提供 Cookie** 才能获取弹幕）

- B 站（**建议提供 Cookie** 以获取完整弹幕）

- 芒果 TV

## 二、环境要求

- 运行环境：Python 3.7 及以上版本
- 硬件条件:  需要注意不同架构系统的第三方包的兼容情况

### 安装
- 一键安装: `pip install get-danmu`—— 推荐，新版本会优先分发到python第三方包管理器仓库上 [get-danmu](https://pypi.org/project/get-danmu/)，有闲时间会更新github仓库代码
- 源码安装：下载本仓库后需提前安装工具所需 Python 依赖（建议通过 pip install -r requirements.txt 安装，具体依赖列表见项目根目录的 requirements.txt 文件），然后使用`pip install .`进行安装

## 三、核心功能使用指南

### 1. 弹幕获取与本地保存

直接获取指定视频的弹幕，保存到当前目录或自定义路径，支持时间范围筛选与格式指定。

#### 基础命令

```
# 方式1：直接指定视频URL
get-danmu [视频URL]
# 方式2：交互式输入视频URL（执行后按提示输入） #推荐
get-danmu
# 简写：可用 get-dm 替代 get-danmu（例：get-dm [视频URL]）
```

#### 可选参数说明

| 参数                          | 格式要求                                    | 功能描述                                                     |
| ----------------------------- | ------------------------------------------- | ------------------------------------------------------------ |
| --start 时间                  | 分钟：秒（如 5:30）或 分钟。秒（如 5.5）    | 指定弹幕获取的**开始时间**（仅获取该时间点之后的弹幕）       |
| --end 时间                    | 同 --start                                  | 指定弹幕获取的**结束时间**（仅获取该时间点之前的弹幕）       |
| --cookie [文件路径]           | 本地 Cookie 文本文件路径（如 ./cookie.txt） | 导入平台 Cookie，用于获取完整弹幕（优酷必传，B 站建议传）    |
| --resettime / -R              | 无额外参数                                  | 弹幕时间校正（需先指定 --start）：消除视频片头导致的弹幕时间偏移（例：原 5 分钟弹幕从 3 分钟开始，校正后为 2 分钟） |
| --savepath [路径] / -s [路径] | 本地文件夹路径（如 ./danmu_files）          | 指定弹幕文件的**保存目录**（默认保存在当前运行目录）         |
| --type [格式]                 | 可选 xml /csv（默认 csv）                   | 指定弹幕文件的**存储格式**（csv 读取速度更快，更适合后续服务调用） |
| -S                            | 无额外参数                                  | 将弹幕同时存入本地数据库（需先通过 --db 指定数据库路径，仅支持 csv 格式） |

#### 示例

```
# 1. 获取B站视频弹幕，指定Cookie，保存为csv格式到 ./my_danmu 目录，cookie直接去浏览器复制请求头那一大串cookie字符即可不要带回车和空行
get-danmu https://www.bilibili.com/bangumi/play/ep1633643?spm_id_from=333.337.0.0 --cookie ./bilibili_cookie.txt --savepath ./my_danmu --type csv

# 2. 获取腾讯视频弹幕，仅获取3分20秒到20分的弹幕
get-danmu https://v.qq.com/x/cover/mcv8hkc8zk8lnov/j4100jwv4qo.html --start 3:20 --end 20:00
```

### 2. 本地数据库配置

使用 SQLite 本地文件数据库管理弹幕数据，弹幕文件会自动存储到数据库目录下的 danmu_data 子目录（首次指定路径时自动创建）。

#### 命令格式

```
# 指定数据库存储路径（首次使用需执行，后续可直接调用其他功能）
get-danmu --db [数据库路径]
# 示例：将数据库保存在 E:\danmu_database 目录，要带绝对路径不要带相对路径，其他系统也同理
get-danmu --db E:\danmu_database
```

### 3. 数据库弹幕管理

对已存入数据库的弹幕进行二次筛选（如调整时间范围）或更新，参数与「弹幕获取」功能一致。

#### 命令格式

```
get-danmu --data
```

#### 支持参数

--start、--end、--cookie、--resettime / -R（参数说明同「1. 弹幕获取与本地保存」）

#### 示例

```
# 更新数据库中某视频的弹幕，校正时间（从2分钟开始的弹幕修正为0起点）
get-danmu --data --start 2:00 --resettime --cookie ./bilibili_cookie.txt
```

### 4. 代理配置

支持通过代理获取弹幕（适用于网络环境限制场景），可快速配置或清除代理。

#### 命令格式

```
# 1. 配置代理（示例：使用本地 8080 端口的 HTTP 代理）
get-danmu --proxy http://localhost:8080

# 2. 清除已配置的代理（仅执行 --proxy 无地址即可）
get-danmu --proxy
```

### 5. 清除所有配置

一键清空工具的所有本地配置（包括数据库路径、代理设置等），恢复初始状态。

#### 命令格式

```
get-danmu --clear
```
### 6. 配置备份弹幕服务器
> 因为不可能所有弹幕都要自己手动去下载，毕竟真的很累，由于作者太懒，而有些电视剧剧集又臭又长还多又有些年头，所以无需最新的弹幕，因此部署一个[danmu_api](https://github.com/huangxd-/danmu_api)服务器，本地再运行本脚本的弹幕服务器，即可补充本地弹幕不足，比如这个剧集有55集，使用本脚本保存了3集剩下的会由本脚本让你的播放器重定向的danmu_api服务器上实现了剩下的52集的弹幕，所以会优先给你的播放器返回本地的弹幕，那么有了danmu_api是不是本脚本就无用了?错，本脚本能让你手动获取到视频最新的弹幕，也可手动一条命令更新弹幕，也可获取较老视频的弹幕，较老的视频danmu_api提供的弹幕量太少只有几百，所以本脚本的优势是和danmu_api互补，配置命令如下：
```
get-danmu --redirect http://[danmu_api服务器ip或域名]:9321/密钥
get-danmu --redirect http://1.1.1.1:9321/getdanmu         #示例
get-danmu --redirect   #不传递参数,则清除配置
```

### 7. 弹幕服务搭建（核心功能）

搭建与「[api.dandanplay.net](https://api.dandanplay.net)」兼容的弹幕服务器，解决私人影视库（电影 / 电视剧）的弹幕需求（[api.dandanplay.net](https://api.dandanplay.net) 仅覆盖动漫且更新不及时）。

#### 核心优势

- **兼容性**：接口设计与 [api.dandanplay.net](https://api.dandanplay.net) 完全一致，可直接对接依赖该接口的影视库工具（如 Jellyfin、Emby 等），目前已适配Hills、Yamby或者其他支持自定义添加的dandanplay格式的软件，已测试中完美适配`Hills、Yamby`

- **性能**：处理 1 万条以内弹幕耗时 ≈ 0.1 秒，10-15 万条热门电影弹幕耗时 ≈ 0.5 秒

- **灵活性**：支持通过 --data 手动更新数据库弹幕，弥补无法自动更新的不足

#### 命令格式

##### 第一次搭建
1. 需要先指定数据库存储位置
```
# 指定数据库存储路径（首次使用需执行，后续可直接调用其他功能）
get-danmu --db [数据库路径]
# 示例：将数据库保存在 E:\danmu_database 目录，要带绝对路径不要带相对路径，其他系统也同理
get-danmu --db E:\danmu_database
```

2. 获取弹幕并存储到数据库中需要指定`-S`参数
```
#获取腾讯视频弹幕并存储到数据库中
get-danmu https://v.qq.com/x/cover/mcv8hkc8zk8lnov/j4100jwv4qo.html -S
```

3. 开启服务器
```
# 启动服务器（默认端口 80）
get-danmu --runserver
# 自定义端口（示例：使用 8088 端口启动服务）
get-danmu --runserver 8088
```
> 后续再添加弹幕时无需再指定数据库存放位置，可直接运行服务器，服务器没有提供web管理，只提供了本地的交互式管理`get-danmu --data`
- 重置数据库存放位置后，需要你先移动数据库文件和弹幕数据到指定路径，还需要手动修改数据库中的file字段，建议使用sql语句去修改因为默认提供`get-danmu --data`不具备批量修改的能力

##### 添加API

现在就可以在Hills和Yamby上添加弹幕api地址了，直接添加你运行服务器的ip即可，例如你服务器ip为`192.168.1.3`，使用的默认端口`80`，那么直接添加`http://192.168.1.3`即可享用弹幕服务器了


#### 操作说明

- 退出服务器：按下 Ctrl + C 即可终止服务
- 服务验证：启动后可通过 http://127.0.0.1:[端口] 访问（或本机ip访问）


#### 安全提示

- **禁止在生产环境或公网部署**：代码未经过安全审查，无日志系统，无法抵御网络攻击

- **仅限本地私人使用**：建议在家庭局域网内搭建，避免暴露公网


## 四、在你的代码中调用
> 本库可以在你的代码中导入运行
-  一共提供了五个运行接口

- 导入解析核心
```
from get_danmu.api.danmu_tx import TencentFetcher
from get_danmu.api.danmu_iqiyi import IqiyiFetcher
from get_danmu.api.danmu_mgtv import MgtvFetcher
from get_danmu.api.danmu_bilibili import BilibiliFetcher
from get_danmu.api.danmu_youku import YoukuFetcher
```
- 初始化
```
tx=TencentFetcher(url=url,proxy=proxies)
iqiyi=IqiyiFetcher(url=url,proxy=proxies)
mgtv=MgtvFetcher(url=url,proxy=proxies)
```
> url为视频链接
> proxies为代理配置，类型应为字典类型，示例如下
```
{
    'http': 'http://127.0.0.1:7890'
}
```
- 需要cookie的接口初始化
```
yk=YoukuFetcher(url=url,proxy=proxies,cookie=cookies)
bili=BilibiliFetcher(url=url,proxy=proxies,cookie=cookies)
```
> url为视频链接
> proxies为代理配置，类型应为字典类型，例子同上
> cookies为请求头cookie对于yk接口来说涉及加密为必要参数，类型为字符串而不是字典类型

- run获取视频弹幕
```
danmu_data,duration,title=tx.run(
    start_second=self.start_second,
    end_second=self.end_second,
    progress_callback=update_progress  
)
```
> 各个接口都有run方法，所传递的参数都一致
> start_second为开始时间，即从哪一秒开始，单位秒，类型为int，可以省略为None，默认为从第0秒开始
> end_second为结束时间，即从哪一秒结束，单位秒，类型为int，可以省略为None，默认为从剧集最后一秒结束
> progress_callback回调函数，会返回当前进度current和总任务个数total，自己计算一下就有进度的百分比了，可以省略为None
> 该方法会返回三个数据，第一个为danmu_data,duration,title，数据如下
```
danmu_data=[{
    "time_offset": time_offset, #float or int 弹幕出现时间
    "mode": mode, #int 类型，一共三种，1-普通弹幕，4-底部弹幕，5-顶部弹幕
    "font_size": 25, #int 字体大小
    "color": color, #int 32位字体颜色
    "timestamp": time, #datetime 弹幕发送时间，如果该平台未提供则会使用现在的时间填充
    "content": content #str 弹幕内容
}]
duration=10 #int 单位为秒
title='' #str 该剧集的标题
```



## 五、更新记录
- 2025-10-28：发布 v0.3.4版本  增加对danmu_api的支持，修正本地数据管理时连续操作后丢失数据的bug
- 2025-10-12：发布 v0.3.2 版本 修正api更新处理逻辑，修正web服务返回数据的标准化使得更多的平台支持
- 2025-10-11：发布 v0.2.0 版本 修正core处理逻辑
- 2025-10-10：发布 v0.0.1 版本（初代版本），完成核心功能

## 六、开源声明

1. 本工具仅用于**个人学习与研究**，**禁止任何商业用途**（包括但不限于盈利性服务、企业内部使用等）

2. 工具所使用的接口均来源于公开网络，若涉及第三方平台（如腾讯视频、B 站等）权益，请联系维护者删除相关代码

3. 如因违规使用（如商业用途、侵权、违反平台规则等）产生法律纠纷，均由使用者自行承担，与工具维护者无关

4. 若发现侵权或违规使用情况，请通过维护者邮箱联系，会在 3 个工作日内处理

5. 除去上述要求外，还需遵守本项目的开源协议

## 七、致谢
- 核心弹幕解析接口-优酷接口思路来源于 [DanmuTools](https://github.com/Hamlin-Xu/DanmuTools)
- 弹幕数据标准化采用[dandanplay](https://api.dandanplay.net/swagger/index.html)


## 八、项目信息

- 项目创建者：李先生

- 项目维护者：李先生

- 维护者邮箱：[3101978435@qq.com](mailto:3101978435@qq.com)

- 开源目的：提供私人影视库弹幕解决方案，促进 Python 命令行工具开发技术的学习与交流


## 九、统计信息

[![Star History Chart](https://api.star-history.com/svg?repos=lzq-hopego/get-danmu&type=Date)](https://www.star-history.com/#lzq-hopego/get-danmu&Date)

