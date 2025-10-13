import re
from flask import Flask, request, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime
import os, time, csv
import ujson

# 初始化 SQLAlchemy（先不绑定 app，后续动态关联）
db = SQLAlchemy()

# 定义数据模型（与原逻辑一致）
class AnimeEpisode(db.Model):
    __tablename__ = 'anime_episodes'
    
    id = db.Column(db.Integer, primary_key=True)
    episodeId = db.Column(db.Integer, nullable=False, unique=True, autoincrement=True)
    animeId = db.Column(db.Integer, nullable=True)
    animeTitle = db.Column(db.String(255), nullable=False)
    episodeTitle = db.Column(db.String(255), nullable=True)
    startDate = db.Column(db.DateTime, default=datetime.now, nullable=False)
    file = db.Column(db.String(255))
    fileName = db.Column(db.String(255), nullable=False, index=True)
    imageUrl = db.Column(db.String(512), nullable=True)
    api = db.Column(db.String(20), nullable=True)
    api_info = db.Column(db.JSON, nullable=True)

# 自定义快速JSON响应函数（原逻辑保留）
def fast_json(data, status_code=200):
    try:
        json_str = ujson.dumps(data, ensure_ascii=False)
        response = Response(
            json_str,
            status=status_code,
            mimetype='application/json; charset=utf-8'
        )
        response.headers['Cache-Control'] = 'public, max-age=60'
        return response
    except Exception as e:
        return Response(
            ujson.dumps({"error": f"序列化失败: {str(e)}"}),
            status=500,
            mimetype='application/json'
        )



# 路由注册函数（将路由绑定到指定 app）
def register_routes(app):
    # 评论查询接口
    @app.route("/api/v2/comment/<episodeId>", methods=["GET"])
    def get_comments(episodeId):
        # 保持原有实现...
        starttime = time.time()
        try:
            episode = AnimeEpisode.query.with_entities(AnimeEpisode.file)\
                        .filter_by(episodeId=episodeId).first()
            
            if not episode or not episode.file or not os.path.exists(episode.file):
                return fast_json({"count": 0, "comments": []})
            
            comments = []
            file_path = episode.file
            
            with open(file_path, 'r', encoding='utf-8-sig', buffering=65536) as f:
                reader = csv.DictReader(f)
                
                field_set = set(reader.fieldnames or [])
                if not {'cid', 'p', 'm'}.issubset(field_set):
                    missing = {'cid', 'p', 'm'} - field_set
                    return fast_json({
                        "count": 0,
                        "comments": [],
                        "error": f"CSV缺少字段: {missing}"
                    })
                
                for row in reader:
                    try:
                        comments.append({
                            'cid': int(row['cid']),
                            'p': row['p'].strip(),
                            'm': row['m'].strip()
                        })
                    except (ValueError, TypeError, KeyError):
                        continue
            count = len(comments)
            print(f"数据量: {count}, 耗时: {time.time() - starttime:.4f}秒")
            
            return fast_json({
                "count": count,
                "comments": comments
            })
            
        except Exception as e:
            return fast_json({
                "count": 0,
                "comments": [],
                "error": f"服务器错误: {str(e)}"
            })

    # 文件名匹配接口（修复原代码缩进错误）
    @app.route("/api/v2/match", methods=["POST"])
    def match_file():
        try:
            # print(f"当前数据库地址: {app.config['SQLALCHEMY_DATABASE_URI']}")
            data = request.get_json()
            
            if not data or "fileName" not in data:
                return fast_json({
                    "errorCode": 2,
                    "success": True,
                    "errorMessage": "请求缺少fileName参数",
                    "isMatched": False,
                    "matches": []
                })
            
            file_name = data["fileName"]
            print(f"匹配文件名: {file_name}")
            
            matches = AnimeEpisode.query.filter(
                AnimeEpisode.fileName.like(f'%{file_name}%')
            ).with_entities(
                AnimeEpisode.episodeId, AnimeEpisode.animeId, 
                AnimeEpisode.animeTitle, AnimeEpisode.episodeTitle,
                AnimeEpisode.imageUrl, AnimeEpisode.api, AnimeEpisode.api_info
            ).all()
            print(f"匹配结果数量: {len(matches)}")
            
            if not matches:
                return fast_json({
                    "errorCode": 1,
                    "success": True,
                    "errorMessage": "未找到匹配的文件",
                    "isMatched": False,
                    "matches": []
                })
            
            match_items = [{
                "episodeId": item[0],
                "animeId": item[1],
                "animeTitle": item[2],
                "episodeTitle": item[3],
                "type": "tvseries",
                "imageUrl": item[4],
                "api": item[5],
                "api_info": item[6]
            } for item in matches]

            return fast_json({
                "errorCode": 0,
                "success": True,
                "errorMessage": "",
                "isMatched": True,
                "matches": match_items
            })
        
        except Exception as e:
            return fast_json({
                "errorCode": 500,
                "success": False,
                "errorMessage": f"服务器错误: {str(e)}",
                "isMatched": False,
                "matches": []
            })
    # 动漫搜索接口
    @app.route("/api/v2/search/anime", methods=["GET"])
    def search_anime():
        try:
            keyword = request.args.get('keyword', '').strip()
            
            if not keyword:
                return fast_json({
                    "errorCode": 1,
                    "success": False,
                    "errorMessage": "请提供搜索关键词",
                    "animes": []
                })
            
            # 1. 数据库查询：保留核心字段，按fileName排序（便于后续处理）
            query = AnimeEpisode.query.filter(
                AnimeEpisode.fileName.like(f'%{keyword}%')
            ).with_entities(
                AnimeEpisode.animeId, AnimeEpisode.animeTitle,
                AnimeEpisode.imageUrl, AnimeEpisode.startDate,
                AnimeEpisode.fileName
            ).order_by(
                AnimeEpisode.fileName
            ).all()
            
            if not query:
                return fast_json({
                    "errorCode": 0,
                    "success": True,
                    "errorMessage": "未找到匹配结果",
                    "animes": []
                })
            
            # 2. 核心逻辑：按「E分割后的基础名称（含季标识）」去重，合并集数
            animes_result = []  # 最终结果列表
            existing_bangumi_ids = set()  # 用于快速判断bangumiId是否已存在（去重）
            
            for item in query:
                animeId, animeTitle, imageUrl, startDate, fileName = item
                
                # 2.1 按"E"分割fileName，提取「基础名称+季标识」（如"爱人错过 S1E1"→"爱人错过 S1"）
                # split("E")[-2] 取E前面的部分（避免fileName含多个E的情况）
                split_by_E = fileName.split("E")
                if len(split_by_E) >= 2:
                    # 有E分隔（含集数）：取E前面的部分作为基础（如"S1E1"→"S1"）
                    base_with_season = split_by_E[-2].strip()
                else:
                    # 无E分隔（无明确集数）：直接用原fileName作为基础
                    base_with_season = fileName.strip()
                
                # 2.2 提取季标识（S+数字，如"S1"）和中文季数（如"S1"→"第1季"）
                # 遍历split后的单词，找包含"S"且后面跟数字的部分（如"爱人错过 S1"→"S1"）
                season_tag = ""  # 季标识（如"S1"）
                chinese_season = ""  # 中文季数（如"第1季"）
                for part in base_with_season.split():
                    if part.startswith(("S", "s")) and len(part) > 1 and part[1:].isdigit():
                        season_tag = part.upper()  # 统一转为大写（s1→S1）
                        season_num = part[1:]  # 提取数字（如"S1"→"1"）
                        chinese_season = f"第{season_num}季"  # 转为中文季数
                        break  # 找到第一个季标识即可（避免多个S的情况）
                
                # 2.3 生成bangumiId（核心去重键：基础名称+季标识）
                # 若有季标识，bangumiId=基础名称+季标识（如"爱人错过 S1"）
                # 若无季标识，bangumiId=基础名称（如"爱人错过"）
                bangumi_id = base_with_season if season_tag else base_with_season
                
                # 2.4 处理去重：若bangumiId已存在，仅累加集数；否则新增记录
                if bangumi_id in existing_bangumi_ids:
                    # 已存在：找到对应记录，集数+1
                    for result_item in animes_result:
                        if result_item["bangumiId"] == bangumi_id:
                            result_item["episodeCount"] += 1
                            result_item["startDate"] = startDate.strftime("%Y-%m-%d")
                            if imageUrl:
                                result_item["imageUrl"]=imageUrl
                            break
                else:
                    # 不存在：新增记录
                    # 处理开播时间（转为字符串，无则为空）
                    start_date_str = startDate.strftime("%Y-%m-%d") if startDate else ""
                    # 处理标题：原标题+中文季数（如"爱人错过"+"第1季"→"爱人错过 第1季"）
                    final_title = f"{animeTitle.strip()} {chinese_season}".strip()
                    # 处理海报图：优先用当前记录的imageUrl，无则为空
                    final_image_url = imageUrl.strip() if imageUrl else ""
                    
                    new_item = {
                        "animeId": animeId or 0,  # 无animeId时用0兜底
                        "bangumiId": bangumi_id,  # 核心：去重的键（如"爱人错过 S1"）
                        "animeTitle": final_title,  # 带中文季数的标题（如"爱人错过 第1季"）
                        "type": "tvseries",
                        "typeDescription": chinese_season or "无明确季数",  # 季数描述
                        "imageUrl": final_image_url,
                        "startDate": start_date_str,
                        "episodeCount": 1,  # 初始集数为1（当前记录算1集）
                        "rating": 0,
                        "isFavorited": True
                    }
                    
                    animes_result.append(new_item)
                    existing_bangumi_ids.add(bangumi_id)  # 加入去重集合
            
            # 3. （可选）按季数排序（如"S1"→"S2"→"S3"，避免乱序）
            def sort_by_season_num(item):
                # 从bangumiId中提取季数数字（如"S1"→1，无则0）
                for part in item["bangumiId"].split():
                    if part.startswith("S") and part[1:].isdigit():
                        return int(part[1:])
                return 0
            
            animes_result.sort(key=sort_by_season_num)
            
            # 4. 返回结果
            return fast_json({
                "errorCode": 0,
                "success": True,
                "errorMessage": "",
                "animes": animes_result,
                "totalSeasons": len(animes_result)  # 新增：返回总季数，便于前端展示
            })
            
        except Exception as e:
            return fast_json({
                "errorCode": 500,
                "success": False,
                "errorMessage": f"搜索失败: {str(e)}",
                "animes": []
            })

    # 剧集搜索接口
    @app.route("/api/v2/bangumi/<keyword>", methods=["GET"])
    def search_bangumi(keyword):
        # 调整查询，包含fileName字段
        query = AnimeEpisode.query.filter(
                AnimeEpisode.fileName.like(f'%{keyword}%')
            ).with_entities(
                AnimeEpisode.episodeId, 
                AnimeEpisode.episodeTitle, 
                AnimeEpisode.animeTitle,
                AnimeEpisode.fileName  # 新增fileName用于提取season和episode信息
            ).order_by(
                func.cast(
                    func.substr(AnimeEpisode.episodeTitle, 2, func.length(AnimeEpisode.episodeTitle) - 2),
                    db.Integer
                )
            ).all()
        
        # 处理查询结果，提取seasonId和episodeNumber
        episodes = []
        for item in query:
            episode_id, episode_title, anime_title, file_name = item
            
            # 初始化默认值
            season_id = "1"  # 默认第一季
            episode_number = ""
            
            # 从fileName中提取seasonId (S后面的数字)和episodeNumber (E后面的数字)
            if file_name:
                # 提取Sx部分 (如S1, S2)
                s_match = re.search(r'S(\d+)', file_name, re.IGNORECASE)
                if s_match:
                    season_id = s_match.group(1)  # 获取S后面的数字
                
                # 提取Exx部分 (如E1, E23)
                e_match = re.search(r'E(\d+)', file_name, re.IGNORECASE)
                if e_match:
                    episode_number = e_match.group(1)  # 获取E后面的数字
            
            # 构建单集数据
            episodes.append({
                "seasonId": season_id,
                "episodeId": episode_id,
                "episodeTitle": episode_title if episode_title else anime_title,
                "episodeNumber": episode_number
            })
        
        # 返回修改后的JSON结构
        return fast_json({
            "errorCode": 0,
            "success": True,
            "errorMessage": "error",
            "bangumi": {
                "episodes": episodes
            }
        })

# 对外提供的核心函数：创建 Flask 应用
def create_danmu_app(db_path='sqlite:///danmu_data.db', compress_level=6):
    """
    创建弹幕服务 Flask 应用
    
    Args:
        db_path: SQLite 数据库 URI（如 'sqlite:///C:/test/db.db' 或 'sqlite:///:memory:'）
        compress_level: 压缩级别（默认6，若不需要压缩可设为None）
    
    Returns:
        Flask 应用实例
    """
    # 初始化 Flask 应用
    app = Flask(__name__)
    
    # 配置应用
    app.config['SQLALCHEMY_DATABASE_URI'] = db_path  # 自定义数据库地址
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭不必要的修改跟踪
    if compress_level is not None:
        app.config['COMPRESS_LEVEL'] = compress_level  # 压缩配置（可选）
    
    # 初始化数据库（绑定 app）
    db.init_app(app)
    
    # 注册所有路由
    register_routes(app)
    
    # 创建数据库表（确保表存在）
    with app.app_context():
        db.create_all()
        print(f"数据库初始化完成，地址: {db_path}")
    
    return app






# 保留独立运行能力（直接运行该文件时生效）
if __name__ == "__main__":
    # 默认配置：数据库在当前目录，端口80
    app = create_danmu_app(
        db_path='sqlite:///danmu_data.db',  # 默认数据库地址
        compress_level=6
    )
    app.run(host="0.0.0.0", port=80, debug=True, threaded=True)