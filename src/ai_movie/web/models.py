from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_login import UserMixin

# 从app模块导入db实例以避免循环导入
from . import db

bcrypt = Bcrypt()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        """设置密码哈希"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """验证密码哈希"""
        return bcrypt.check_password_hash(self.password_hash, password)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # 核心内容字段
    input_text = db.Column(db.Text, nullable=False, comment='用户原始输入文本')
    title = db.Column(db.String(255), nullable=False, default="未命名视频", comment='视频标题')
    copywriting = db.Column(db.Text, nullable=False, default="", comment='生成的文案内容')
    
    # 视频相关字段
    video_url = db.Column(db.String(255), nullable=True, comment='视频文件URL')
    status = db.Column(db.String(20), default='pending', comment='总体状态')
    video_error = db.Column(db.Text, nullable=True, comment='错误信息')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    
    # 视频生成进度字段
    parsing_started_at = db.Column(db.DateTime, nullable=True)
    parsing_completed_at = db.Column(db.DateTime, nullable=True)
    parsing_status = db.Column(db.String(20), default="pending")

    storyboard_started_at = db.Column(db.DateTime, nullable=True)
    storyboard_completed_at = db.Column(db.DateTime, nullable=True)
    storyboard_status = db.Column(db.String(20), default="pending")

    generation_started_at = db.Column(db.DateTime, nullable=True)
    generation_completed_at = db.Column(db.DateTime, nullable=True)
    generation_status = db.Column(db.String(20), default="pending")

    concatenation_started_at = db.Column(db.DateTime, nullable=True)
    concatenation_completed_at = db.Column(db.DateTime, nullable=True)
    concatenation_status = db.Column(db.String(20), default="pending")

    oss_upload_started_at = db.Column(db.DateTime, nullable=True)
    oss_upload_completed_at = db.Column(db.DateTime, nullable=True)
    oss_upload_status = db.Column(db.String(20), default="pending")
    
    # 建立与用户模型的关系
    user = db.relationship('User', backref=db.backref('videos', lazy=True))