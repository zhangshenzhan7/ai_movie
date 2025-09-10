# Flask应用初始化模块
import os
from flask import Flask, jsonify
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# 导入新的配置和异常处理模块
from ..core.config import config
from ..core.exceptions import VideoGenerationException
from ..core.logging_config import setup_logging, get_logger

app_logger = get_logger(__name__)

# 初始化SQLAlchemy和Migrate
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    # 显式配置模板和静态文件目录
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir,
                static_url_path='/static')
    
    # 验证配置
    try:
        config.validate_all()
        app_logger.info("配置验证成功")
    except Exception as e:
        app_logger.error(f"配置验证失败: {str(e)}", error=e)
        raise
    
    # 使用新的配置管理系统
    app.config.update(config.get_flask_config())
    
    # 根据配置选择是否初始化数据库
    if config.database.use_database:
        app_logger.info("启用MySQL数据库模式")
        # 初始化数据库和扩展
        db.init_app(app)
        migrate.init_app(app, db)
        login_manager.init_app(app)
        login_manager.login_view = 'main.login'
        login_manager.login_message = '请先登录以访问此页面。'
        
        # 测试数据库连接
        with app.app_context():
            from sqlalchemy import text
            try:
                with db.engine.connect() as connection:
                    connection.execute(text('SELECT 1'))
                app_logger.info("数据库连接成功")
                
                # 创建表（如果不存在）
                db.create_all()
                app_logger.info("数据库表初始化完成")
                
            except Exception as db_error:
                app_logger.error(f"数据库连接失败: {str(db_error)}")
                raise VideoGenerationException(
                    f"数据库连接失败: {str(db_error)}",
                    error_code="DATABASE_CONNECTION_ERROR",
                    details={"database_uri": config.database.uri}
                )
        
        @login_manager.user_loader
        def load_user(user_id):
            # 在函数内部导入User模型以避免循环导入
            from .models import User
            return User.query.get(int(user_id))
        
        @login_manager.unauthorized_handler
        def unauthorized():
            return jsonify({
                "error": "请先登录以访问此资源",
                "status": "failed"
            }), 401
    else:
        app_logger.info("数据库功能已禁用，仅支持基本功能")
        # 不初始化数据库相关组件，但不提供用户认证功能
    
    # 全局异常处理器
    @app.errorhandler(VideoGenerationException)
    def handle_video_generation_error(e):
        app_logger.error(f"视频生成异常: {e.message}", 
                        error_code=e.error_code, 
                        details=e.details)
        return jsonify(e.to_dict()), 400
    
    @app.errorhandler(500)
    def handle_internal_error(e):
        app_logger.error(f"内部服务器错误: {str(e)}", error=e)
        return jsonify({
            "error": "内部服务器错误",
            "status": "failed"
        }), 500
    
    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({
            "error": "资源未找到",
            "status": "failed"
        }), 404
    
    # 初始化日志系统
    setup_logging()
    
    # 注册蓝图
    from .routes import main
    app.register_blueprint(main)
    
    app_logger.info("Flask应用初始化完成")
    
    return app

"""
Web application module for AI Movie Generator

Contains Flask application, models, routes and templates.
"""

from .models import User, Video
from .routes import main

__all__ = [
    "User",
    "Video", 
    "main",
]
