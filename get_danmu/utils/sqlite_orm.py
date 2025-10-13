from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime


# 初始化基础模型类
Base = declarative_base()

# 定义数据模型
class AnimeEpisode(Base):
    __tablename__ = 'anime_episodes'
    
    id = Column(Integer, primary_key=True)
    episodeId = Column(Integer, nullable=False, unique=True, autoincrement=True)
    animeId = Column(Integer, nullable=True)
    animeTitle = Column(String(255), nullable=False)
    episodeTitle = Column(String(255), nullable=True)
    startDate = Column(DateTime, default=datetime.now, nullable=False)
    file = Column(String(255))
    fileName = Column(String(255), nullable=False, index=True)
    imageUrl = Column(String(512), nullable=True)
    api = Column(String(20), nullable=True)
    api_info = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<AnimeEpisode(id='{self.id}', animeTitle='{self.animeTitle}')>"

class SQLiteORM:
    def __init__(self, db_name:str='anime_files'):
        self.engine = create_engine(f'sqlite:///{db_name}', echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def filter_episodes(self, fileName=None, api=None, animeTitle=None,id=None):
        """
        多条件过滤查询
        :param fileName: 文件名包含的关键词
        :param api: API包含的关键词
        :param animeTitle: 动画标题包含的关键词
        :return: 匹配的记录列表
        """
        query = self.session.query(AnimeEpisode)
        
        # 逐个添加过滤条件
        if id:
            return query.filter(AnimeEpisode.id==id).first()
        if fileName:
            query = query.filter(AnimeEpisode.fileName.like(f'%{fileName}%'))
        if api:
            query = query.filter(AnimeEpisode.api.like(f'%{api}%'))
        if animeTitle:
            query = query.filter(AnimeEpisode.animeTitle.like(f'%{animeTitle}%'))
        query = query.filter(AnimeEpisode.api_info.like('%id%'))
            
        return query.order_by(AnimeEpisode.id.asc()).all()

    def delete_by_id(self, episode_id):
        """
        通过ID删除记录
        :param episode_id: 要删除的记录ID
        :return: 成功返回True，失败返回False
        """
        try:
            episode = self.session.query(AnimeEpisode).filter_by(id=episode_id).first()
            if not episode:
                print(f"未找到ID为{episode_id}的记录")
                return False
                
            self.session.delete(episode)
            self.session.commit()
            print(f"成功删除ID为{episode_id}的记录")
            return True
        except Exception as e:
            self.session.rollback()
            print(f"删除失败：{str(e)}")
            return False
        
    def get_lang_id(self):
        query = self.session.query(AnimeEpisode).order_by(AnimeEpisode.episodeId.desc()).first()
        if not query:
            return 1
        return query.episodeId

    def update_by_id(self, episode_id, **kwargs):
        """
        通过ID修改记录
        :param episode_id: 要修改的记录ID
        :param kwargs: 要更新的字段和值（如animeTitle='新标题', api='new_api'）
        :return: 成功返回True，失败返回False
        """
        try:
            episode = self.session.query(AnimeEpisode).filter_by(id=episode_id).first()
            if not episode:
                print(f"未找到ID为{episode_id}的记录")
                return False
                
            # 允许更新的字段列表（防止修改不允许的字段）
            allowed_fields = [
                 'animeTitle', 'episodeTitle', 'file', 
                'fileName', 'imageUrl', 'api', 'api_info'
            ]
            
            # 更新字段
            for key, value in kwargs.items():
                if key in allowed_fields:
                    setattr(episode, key, value)
                else:
                    print(f"警告：不允许更新的字段'{key}'已忽略")
                
            self.session.commit()
            print(f"成功更新ID为{episode_id}的记录")
            return True
        except Exception as e:
            self.session.rollback()
            print(f"更新失败：{str(e)}")
            return False
    
    def add_episode(self, **kwargs):
        """
        添加新的动画剧集记录
        :param kwargs: 包含字段的字典，必须包含animeTitle和fileName
        :return: 成功返回创建的对象，失败返回None
        """
        try:
            # 验证必填字段
            required_fields = ['animeTitle', 'fileName']
            for field in required_fields:
                if field not in kwargs or not kwargs[field]:
                    raise ValueError(f"缺少必填字段: {field}")

            # 构建新记录对象
            new_episode = AnimeEpisode(
                animeTitle=kwargs['animeTitle'],
                fileName=kwargs['fileName'],
                # 可选字段
                animeId=kwargs.get('animeId'),
                episodeTitle=kwargs.get('episodeTitle'),
                episodeId=kwargs.get('episodeId'),
                startDate=kwargs.get('startDate', datetime.now()),
                file=kwargs.get('file'),
                imageUrl=kwargs.get('imageUrl'),
                api=kwargs.get('api'),
                api_info=kwargs.get('api_info')
            )

            # 保存到数据库
            self.session.add(new_episode)
            self.session.commit()
            print(f"成功添加记录：ID={new_episode.id}, 标题={new_episode.animeTitle}")
            return new_episode

        except Exception as e:
            self.session.rollback()
            print(f"添加失败：{str(e)}")
            return None

    def close(self):
        self.session.close()
        print("数据库会话已关闭")