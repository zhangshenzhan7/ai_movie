import logging
import os
import threading
import uuid
from datetime import datetime

import dashscope

# 第三方库导入
from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

# 本地模块导入
from .models import User, Video, db
from ..utils.utils import (
    concatenate_videos_with_audio,
    generate_copywriting,
    generate_storyboard,
    generate_video_scenes,
    generate_voiceovers,
    parse_user_input,
    upload_to_oss_wrapper,
)

# 新增导入
from ..core.config import config
from ..core.exceptions import (
    VideoGenerationException, 
    APIException, 
    ValidationException, 
    ConfigurationException,
    DatabaseException
)
from ..core.logging_config import get_logger
from ..core.validation import (
    VideoGenerationRequest,
    VideoGenerationWithImageRequest, 
    UserRegistrationRequest,
    UserLoginRequest,
    PaginationRequest,
    validate_request_data
)

app_logger = get_logger(__name__)
workflow_logger = get_logger('workflow')

# 定义蓝图
main = Blueprint('main', __name__)

# 用于存储视频生成状态的内存字典（在生产环境中应使用数据库或缓存）
# 修改为使用数据库持久化存储状态，防止浏览器刷新导致任务失败
video_generation_status = {}

@main.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@main.route('/dashboard')
@login_required
def dashboard():
    """渲染仪表板页面"""
    return render_template('dashboard.html')

@main.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        # 使用Pydantic验证输入数据
        request_data = validate_request_data(UserRegistrationRequest, request.get_json())
        
        app_logger.log_request_start('/register', 'POST', 
                                   username=request_data.username, 
                                   email=request_data.email)
        
        # 检查用户是否已存在
        if User.query.filter_by(email=request_data.email).first():
            raise ValidationException(
                "该邮箱已被注册",
                error_code="EMAIL_ALREADY_EXISTS"
            )

        if User.query.filter_by(username=request_data.username).first():
            raise ValidationException(
                "该用户名已被使用",
                error_code="USERNAME_ALREADY_EXISTS"
            )

        # 创建新用户
        user = User()
        user.username = request_data.username
        user.email = request_data.email
        user.set_password(request_data.password)

        db.session.add(user)
        db.session.commit()
        
        app_logger.info("用户注册成功", 
                       user_id=user.id, 
                       username=user.username, 
                       email=user.email)

        return jsonify({
            "message": "注册成功",
            "status": "success"
        }), 201

    except (ValidationException, VideoGenerationException):
        db.session.rollback()
        raise  # 这些异常会被全局异常处理器处理
    except Exception as e:
        db.session.rollback()
        app_logger.log_exception("注册过程中出现错误", e)
        raise DatabaseException(
            "注册过程中出现错误",
            error_code="REGISTRATION_ERROR"
        )

@main.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        # 使用Pydantic验证输入数据
        request_data = validate_request_data(UserLoginRequest, request.get_json())
        
        app_logger.log_request_start('/login', 'POST', email=request_data.email)
        
        # 查找用户
        user = User.query.filter_by(email=request_data.email).first()

        # 验证用户和密码
        if not user or not user.check_password(request_data.password):
            app_logger.warning("登录失败", 
                              email=request_data.email, 
                              reason="邮箱或密码不正确")
            raise ValidationException(
                "邮箱或密码不正确",
                error_code="INVALID_CREDENTIALS"
            )

        # 登录用户
        login_user(user)
        
        app_logger.info("用户登录成功", 
                       user_id=user.id, 
                       username=user.username, 
                       email=user.email)

        return jsonify({
            "message": "登录成功",
            "status": "success",
            "username": user.username,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }), 200

    except (ValidationException, VideoGenerationException):
        raise  # 这些异常会被全局异常处理器处理
    except Exception as e:
        app_logger.log_exception("登录过程中出现错误", e)
        raise DatabaseException(
            "登录过程中出现错误",
            error_code="LOGIN_ERROR"
        )

@main.route('/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    try:
        user_id = current_user.id
        username = current_user.username
        
        logout_user()
        
        app_logger.info("用户登出成功", 
                       user_id=user_id, 
                       username=username)
        
        return jsonify({
            "message": "登出成功",
            "status": "success"
        }), 200
    except Exception as e:
        app_logger.log_exception("登出过程中出现错误", e)
        raise VideoGenerationException(
            "登出过程中出现错误",
            error_code="LOGOUT_ERROR"
        )

@main.route('/generate-video', methods=['POST'])
@login_required
def generate_video():
    try:
        # 使用Pydantic验证输入数据
        json_data = request.get_json()
        if not json_data:
            raise ValidationException(
                "请提供有效的JSON数据",
                error_code="INVALID_JSON_DATA"
            )
        
        # 处理字段名映射 (input -> input_text)
        if 'input' in json_data and 'input_text' not in json_data:
            json_data['input_text'] = json_data.pop('input')
            
        request_data = validate_request_data(VideoGenerationRequest, json_data)
        
        workflow_logger.log_task_start("video_generation", 
                                      user_id=current_user.id,
                                      input_text=request_data.input_text[:50] + "...",
                                      title=request_data.title)
        
        # 创建视频记录
        video = Video(
            user_id=current_user.id,
            input_text=request_data.input_text,
            status="pending",
            title=request_data.title,
            copywriting=request_data.input_text
        )
        db.session.add(video)
        db.session.commit()
        
        # 创建状态对象
        root_dir = os.path.join("/tmp", str(uuid.uuid4()))
        state = {
            "user_id": current_user.id,
            "input_text": request_data.input_text,
            "root_dir": root_dir,
            "video_id": video.id,
            "video_status": "pending"
        }
        
        # 初始化状态跟踪
        video_generation_status[video.id] = {
            "status": "pending",
            "progress": 0,
            "current_step": "starting",
            "details": "视频生成任务已启动"
        }
        
        # 更新数据库记录
        video.status = "pending"
        video.parsing_status = "pending"
        video.storyboard_status = "pending"
        video.generation_status = "pending"
        video.concatenation_status = "pending"
        video.oss_upload_status = "pending"
        db.session.commit()
        
        # 设置DashScope API Key
        api_key = request_data.dashscope_api_key or config.ai.dashscope_api_key
        if not api_key:
            workflow_logger.error("API密钥缺失", video_id=video.id)
            
            video_generation_status[video.id] = {
                "status": "failed",
                "progress": 0,
                "current_step": "api_key_check",
                "details": "Missing DashScope API Key"
            }
            video.status = "failed"
            video.video_error = "Missing DashScope API Key"
            db.session.commit()
            
            raise ConfigurationException(
                "Missing DashScope API Key",
                error_code="DASHSCOPE_API_KEY_MISSING"
            )
        
        # 设置API密钥
        dashscope.api_key = api_key
        os.environ["DASHSCOPE_API_KEY"] = api_key
            
        # 异步执行视频生成任务
        thread = threading.Thread(
            target=async_generate_video, 
            args=(state, api_key, video.id, current_app)
        )
        thread.start()
        
        workflow_logger.info("视频生成任务已启动", 
                           video_id=video.id,
                           user_id=current_user.id)
        
        return jsonify({
            "message": "Video generation started",
            "status": "pending",
            "video_id": video.id
        }), 202
        
    except (ValidationException, ConfigurationException, VideoGenerationException):
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        workflow_logger.log_exception("视频生成请求失败", e, user_id=current_user.id)
        raise VideoGenerationException(
            "视频生成请求失败",
            error_code="VIDEO_GENERATION_REQUEST_ERROR"
        )

@main.route('/generate-video-with-image', methods=['POST'])
@login_required
def generate_video_with_image():
    try:
        # 1. 解析用户输入
        title = request.form.get('title', '未命名视频')
        user_input = request.form.get('input')
        dashscope_api_key = request.form.get('dashscope_api_key')
        character_image = request.files.get('character_image')
        
        if not user_input:
            return jsonify({
                "error": "Missing input text",
                "status": "failed"
            }), 400
            
        # 2. 保存上传的图片
        character_image_path = None
        if character_image and character_image.filename:
            # 创建临时目录
            temp_dir = os.path.join("/tmp", "ai_movie_uploads")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 保存图片
            filename = secure_filename(character_image.filename)
            character_image_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{filename}")
            character_image.save(character_image_path)
            
        # 3. 创建视频记录
        video = Video(
            user_id=current_user.id,
            input_text=user_input,
            status="pending",
            title=title,  # 使用用户输入的标题
            copywriting=user_input  # 将用户输入作为初始文案
        )
        db.session.add(video)
        db.session.commit()
        
        # 4. 创建state对象并注入用户信息
        root_dir = os.path.join("/tmp", str(uuid.uuid4()))
        state = {
            "user_id": current_user.id,
            "input_text": user_input,
            "character_image_path": character_image_path,
            "root_dir": root_dir,
            "video_id": video.id,
            "video_status": "pending"
        }
        
        # 5. 初始化状态跟踪（存储到数据库中，防止浏览器刷新导致任务失败）
        video_generation_status[video.id] = {
            "status": "pending",
            "progress": 0,
            "current_step": "starting",
            "details": "视频生成任务已启动"
        }
        
        # 同时更新数据库记录
        video.status = "pending"
        video.parsing_status = "pending"
        video.storyboard_status = "pending"
        video.generation_status = "pending"
        video.concatenation_status = "pending"
        video.oss_upload_status = "pending"
        db.session.commit()
        
        # 6. 设置DashScope API Key（如果提供）
        if dashscope_api_key:
            dashscope.api_key = dashscope_api_key
            os.environ["DASHSCOPE_API_KEY"] = dashscope_api_key
        elif os.getenv('DASHSCOPE_API_KEY'):
            api_key = os.getenv('DASHSCOPE_API_KEY')
            if api_key:
                dashscope.api_key = api_key
                os.environ["DASHSCOPE_API_KEY"] = api_key
        else:
            video_generation_status[video.id] = {
                "status": "failed",
                "progress": 0,
                "current_step": "api_key_check",
                "details": "Missing DashScope API Key"
            }
            video.status = "failed"
            video.video_error = "Missing DashScope API Key"
            db.session.commit()
            return jsonify({
                "error": "Missing DashScope API Key",
                "status": "failed",
                "video_id": video.id
            }), 400
            
        # 7. 异步执行视频生成任务
        thread = threading.Thread(
            target=async_generate_video, 
            args=(state, dashscope_api_key, video.id, current_app)
        )
        thread.start()
        
        # 8. 返回视频ID，供客户端轮询状态
        return jsonify({
            "message": "Video generation started",
            "status": "pending",
            "video_id": video.id
        }), 202
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": str(e),
            "status": "failed"
        }), 500

def async_generate_video(state, dashscope_api_key, video_id, app):
    """异步执行视频生成任务"""
    with app.app_context():
        try:
            # 更新状态
            video_generation_status[video_id] = {
                "status": "processing",
                "progress": 10,
                "current_step": "parsing_input",
                "details": "正在解析用户输入"
            }
            
            # 更新数据库状态
            video = Video.query.get(video_id)
            if video:
                video.parsing_started_at = datetime.utcnow()
                video.parsing_status = "processing"
                db.session.commit()
            
            # 1. 解析用户输入内容
            parsed_content = parse_user_input(state["input_text"], dashscope_api_key)
            state.update(parsed_content)
            
            # 更新数据库状态
            if video:
                video.parsing_completed_at = datetime.utcnow()
                video.parsing_status = "completed"
                db.session.commit()
            
            # 更新状态
            video_generation_status[video_id] = {
                "status": "processing",
                "progress": 20,
                "current_step": "generating_copywriting",
                "details": "正在生成视频文案"
            }
            
            # 更新数据库状态
            if video:
                video.storyboard_started_at = datetime.utcnow()
                video.storyboard_status = "processing"
                db.session.commit()
            
            # 2. 生成视频文案
            copywriting_result = generate_copywriting(parsed_content.get("video_topic", parsed_content.get("expanded_description", "")), dashscope_api_key)
            state.update(copywriting_result)
            
            # 更新数据库中的标题和文案
            if video:
                video.title = copywriting_result.get("title", "未命名视频")
                video.copywriting = copywriting_result.get("copywriting", "")
                db.session.commit()
            
            # 更新状态，包含文案内容
            video_generation_status[video_id] = {
                "status": "processing",
                "progress": 30,
                "current_step": "generating_storyboard",
                "details": "正在生成分镜脚本",
                "title": copywriting_result.get("title", ""),
                "copywriting": copywriting_result.get("copywriting", "")
            }
            
            # 3. 生成分镜脚本
            storyboard = generate_storyboard(parsed_content, dashscope_api_key)
            state["storyboard"] = storyboard
            
            # 验证storyboard数据
            if not storyboard:
                raise Exception("未能生成有效的分镜脚本")
            
            # 更新数据库状态
            if video:
                video.storyboard_completed_at = datetime.utcnow()
                video.storyboard_status = "completed"
                db.session.commit()
            
            # 更新状态，包含分镜脚本
            video_generation_status[video_id] = {
                "status": "processing",
                "progress": 40,
                "current_step": "generating_voiceovers",
                "details": "正在生成音频文件",
                "title": copywriting_result.get("title", ""),
                "copywriting": copywriting_result.get("copywriting", ""),
                "storyboard": storyboard
            }
            
            # 更新数据库状态
            if video:
                video.generation_started_at = datetime.utcnow()
                video.generation_status = "processing"
                db.session.commit()
            
            # 4. 生成音频文件
            audio_files = generate_voiceovers(storyboard, state["root_dir"], dashscope_api_key)
            state["audio_files"] = audio_files
            
            # 更新状态，包含分镜脚本和语音信息
            video_generation_status[video_id] = {
                "status": "processing",
                "progress": 60,
                "current_step": "generating_video_scenes",
                "details": "正在生成视频场景",
                "title": copywriting_result.get("title", ""),
                "copywriting": copywriting_result.get("copywriting", ""),
                "storyboard": storyboard,
                "audio_files": audio_files
            }
            
            # 更新数据库状态
            if video:
                video.generation_started_at = datetime.utcnow()
                video.generation_status = "processing"
                db.session.commit()
            
            # 5. 生成视频场景
            video_segments = generate_video_scenes(state, dashscope_api_key)
            state["video_segments"] = [segment for segment in video_segments if segment is not None]
            
            # 更新状态
            video_generation_status[video_id] = {
                "status": "processing",
                "progress": 80,
                "current_step": "concatenating_videos",
                "details": "正在合并视频和音频",
                "title": copywriting_result.get("title", ""),
                "copywriting": copywriting_result.get("copywriting", ""),
                "storyboard": storyboard,
                "audio_files": audio_files
            }
            
            # 更新数据库状态
            if video:
                video.concatenation_started_at = datetime.utcnow()
                video.concatenation_status = "processing"
                db.session.commit()
            
            # 6. 合并视频和音频
            if state["video_segments"]:
                final_video_path = concatenate_videos_with_audio(
                    state["video_segments"], 
                    state.get("audio_files", []), 
                    state["root_dir"]
                )
                state["final_video_path"] = final_video_path
            else:
                raise Exception("没有生成任何视频片段")
            
            # 更新数据库状态
            if video:
                video.concatenation_completed_at = datetime.utcnow()
                video.concatenation_status = "completed"
                db.session.commit()
            
            # 更新状态
            video_generation_status[video_id] = {
                "status": "processing",
                "progress": 90,
                "current_step": "uploading_to_oss",
                "details": "正在上传到OSS",
                "title": copywriting_result.get("title", ""),
                "copywriting": copywriting_result.get("copywriting", ""),
                "storyboard": storyboard,
                "audio_files": audio_files
            }
            
            # 更新数据库状态
            if video:
                video.oss_upload_started_at = datetime.utcnow()
                video.oss_upload_status = "processing"
                db.session.commit()
            
            # 7. 上传到OSS
            if state["final_video_path"] and os.path.exists(state["final_video_path"]):
                oss_result = upload_to_oss_wrapper(state["final_video_path"], state)
                oss_url = oss_result.get("oss_url")
                if not oss_url:
                    raise Exception(oss_result.get("error", "上传到OSS失败"))
                
                # 更新数据库状态
                if video:
                    video.video_url = oss_url
                    video.status = "completed"
                    video.oss_upload_completed_at = datetime.utcnow()
                    video.oss_upload_status = "completed"
                    db.session.commit()
            else:
                raise Exception("最终视频文件不存在")
                
            # 更新状态
            video_generation_status[video_id] = {
                "status": "completed",
                "progress": 100,
                "current_step": "completed",
                "details": "视频生成完成",
                "video_url": oss_url,
                "title": copywriting_result.get("title", ""),
                "copywriting": copywriting_result.get("copywriting", ""),
                "storyboard": storyboard,
                "audio_files": audio_files
            }
            
        except Exception as e:
            # 更新数据库状态
            video = Video.query.get(video_id)
            if video:
                video.status = "failed"
                video.video_error = str(e)
                # 根据当前步骤更新相应的状态字段
                current_step = video_generation_status.get(video_id, {}).get("current_step")
                if current_step == "parsing_input":
                    video.parsing_status = "failed"
                    video.parsing_completed_at = datetime.utcnow()
                elif current_step in ["generating_copywriting", "generating_storyboard"]:
                    video.storyboard_status = "failed"
                    video.storyboard_completed_at = datetime.utcnow()
                elif current_step in ["generating_voiceovers", "generating_video_scenes"]:
                    video.generation_status = "failed"
                    video.generation_completed_at = datetime.utcnow()
                elif current_step == "concatenating_videos":
                    video.concatenation_status = "failed"
                    video.concatenation_completed_at = datetime.utcnow()
                elif current_step == "uploading_to_oss":
                    video.oss_upload_status = "failed"
                    video.oss_upload_completed_at = datetime.utcnow()
                db.session.commit()
                
            # 更新状态
            video_generation_status[video_id] = {
                "status": "failed",
                "progress": 100,
                "current_step": "error",
                "details": f"视频生成失败: {str(e)}"
            }
            workflow_logger.log_exception(f"Video generation failed for video {video_id}", e, video_id=video_id)

@main.route('/video-status/<int:video_id>', methods=['GET'])
@login_required
def get_video_status(video_id):
    """
    获取视频生成状态
    
    该接口用于轮询视频生成任务的当前状态和进度。
    
    参数:
    video_id (int): 视频ID
    
    返回:
    JSON对象，包含以下字段:
    - video_id: 视频ID
    - status: 当前状态 (pending, processing, completed, failed)
    - progress: 进度百分比 (0-100)
    - current_step: 当前步骤
    - details: 详细描述信息
    - title: 视频标题（仅在生成后）
    - copywriting: 视频文案（仅在生成后）
    - storyboard: 分镜脚本信息（仅在生成后）
    - audio_files: 语音文件信息（仅在生成后）
    - video_url: (仅在完成时) 视频的OSS URL
    
    状态说明:
    - pending: 任务已提交，等待处理
    - processing: 正在处理中
    - completed: 处理完成
    - failed: 处理失败
    
    步骤说明:
    - starting: 任务启动
    - parsing_input: 解析用户输入
    - generating_copywriting: 生成视频文案
    - generating_storyboard: 生成分镜脚本
    - generating_voiceovers: 生成音频文件
    - generating_video_scenes: 生成视频场景
    - concatenating_videos: 合并视频和音频
    - uploading_to_oss: 上传到OSS
    - completed: 完成
    - error: 错误
    """
    try:
        # 检查视频是否存在且属于当前用户
        video = Video.query.filter_by(id=video_id, user_id=current_user.id).first()
        if not video:
            return jsonify({
                "error": "Video not found or access denied",
                "status": "failed"
            }), 404
            
        # 获取状态信息 - 优先从内存获取，如果没有则从数据库构建
        status_info = video_generation_status.get(video_id)
        
        # 如果内存中没有状态信息，但任务仍在进行中，则从数据库构建状态
        if not status_info:
            if video.status == "pending" or video.status == "processing":
                # 从数据库中恢复状态
                status_info = {
                    "status": video.status,
                    "progress": calculate_progress_from_db(video),
                    "current_step": get_current_step_from_db(video),
                    "details": get_details_from_db(video)
                }
            elif video.status == "completed":
                # 任务已完成且状态信息不存在，构建完成状态
                status_info = {
                    "status": "completed",
                    "progress": 100,
                    "current_step": "completed",
                    "details": "视频生成完成",
                    "video_url": video.video_url
                }
            elif video.status == "failed":
                status_info = {
                    "status": "failed",
                    "progress": 100,
                    "current_step": "error",
                    "details": video.video_error or "视频生成失败"
                }
        
        # 如果仍然没有状态信息，使用默认值
        if not status_info:
            status_info = {
                "status": video.status,
                "progress": 100 if video.status == "completed" else 0,
                "current_step": "unknown",
                "details": "任务已完成或状态信息已清理"
            }
        
        response = {
            "video_id": video_id,
            "status": status_info["status"],
            "progress": status_info["progress"],
            "current_step": status_info["current_step"],
            "details": status_info["details"]
        }
        
        # 如果有标题和文案，添加到响应中
        if "title" in status_info:
            response["title"] = status_info["title"]
            
        if "copywriting" in status_info:
            response["copywriting"] = status_info["copywriting"]
            
        # 如果有分镜脚本，添加到响应中
        if "storyboard" in status_info:
            response["storyboard"] = status_info["storyboard"]
            
        # 如果有语音文件信息，添加到响应中
        if "audio_files" in status_info:
            response["audio_files"] = status_info["audio_files"]
        
        # 如果已完成，添加视频URL
        if status_info["status"] == "completed" and "video_url" in status_info:
            video_url = status_info["video_url"]
            # 确保视频URL是完整可访问的链接
            if video_url and not video_url.startswith(('http://', 'https://')):
                # 如果URL不是完整链接，添加基础URL前缀
                if video_url.startswith('/'):
                    # 如果是相对路径，尝试构建完整URL
                    video_url = request.host_url.rstrip('/') + video_url
            response["video_url"] = video_url
        elif video.status == "completed" and video.video_url:
            # 如果从数据库中获取状态，确保视频URL是完整链接
            video_url = video.video_url
            if video_url and not video_url.startswith(('http://', 'https://')):
                # 如果URL不是完整链接，添加基础URL前缀
                if video_url.startswith('/'):
                    # 如果是相对路径，尝试构建完整URL
                    video_url = request.host_url.rstrip('/') + video_url
            response["video_url"] = video_url
            
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "failed"
        }), 500

def calculate_progress_from_db(video):
    """根据数据库中的状态信息计算进度"""
    if video.status == "completed":
        return 100
    elif video.status == "failed":
        return 100
    
    progress = 0
    if video.parsing_status == "completed":
        progress += 20
    elif video.parsing_status == "processing":
        progress += 10
        
    if video.storyboard_status == "completed":
        progress += 20
    elif video.storyboard_status == "processing":
        progress += 10
        
    if video.generation_status == "completed":
        progress += 20
    elif video.generation_status == "processing":
        progress += 10
        
    if video.concatenation_status == "completed":
        progress += 20
    elif video.concatenation_status == "processing":
        progress += 10
        
    if video.oss_upload_status == "completed":
        progress += 20
    elif video.oss_upload_status == "processing":
        progress += 10
        
    return min(progress, 90)  # 最多90%，100%只在完成时设置

def get_current_step_from_db(video):
    """根据数据库中的状态信息获取当前步骤"""
    if video.parsing_status == "processing":
        return "parsing_input"
    elif video.storyboard_status == "processing":
        return "generating_storyboard"
    elif video.generation_status == "processing":
        return "generating_video_scenes"
    elif video.concatenation_status == "processing":
        return "concatenating_videos"
    elif video.oss_upload_status == "processing":
        return "uploading_to_oss"
    elif video.status == "completed":
        return "completed"
    elif video.status == "failed":
        return "error"
    else:
        return "unknown"

def get_details_from_db(video):
    """根据数据库中的状态信息获取详细描述"""
    if video.parsing_status == "processing":
        return "正在解析用户输入"
    elif video.storyboard_status == "processing":
        return "正在生成分镜脚本"
    elif video.generation_status == "processing":
        return "正在生成视频场景"
    elif video.concatenation_status == "processing":
        return "正在合并视频和音频"
    elif video.oss_upload_status == "processing":
        return "正在上传到OSS"
    elif video.status == "completed":
        return "视频生成完成"
    elif video.status == "failed":
        return video.video_error or "视频生成失败"
    else:
        return "任务正在处理中"

@main.route('/check-auth', methods=['GET'])
def check_auth():
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email
            }
        }), 200
    else:
        return jsonify({
            "authenticated": False
        }), 200

@main.route('/user/videos', methods=['GET'])
@login_required
def get_user_videos():
    """获取用户视频列表（分页）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        videos = Video.query.filter_by(user_id=current_user.id)\
            .order_by(Video.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        video_list = []
        for video in videos.items:
            # 尝试从copywriting中提取视频描述，如果不存在则使用默认文本
            description = "未命名视频"
            if video.copywriting:
                description = video.copywriting[:50] + "..." if len(video.copywriting) > 50 else video.copywriting
            elif video.title:
                description = video.title
            
            video_data = {
                "id": video.id,
                "status": video.status,
                "video_url": video.video_url,
                "created_at": video.created_at.isoformat() if video.created_at else None,
                "parsing_status": video.parsing_status,
                "storyboard_status": video.storyboard_status,
                "generation_status": video.generation_status,
                "concatenation_status": video.concatenation_status,
                "oss_upload_status": video.oss_upload_status,
                "video_error": video.video_error,
                "description": description,  # 添加视频描述
                "title": video.title,  # 添加视频标题
                "copywriting": video.copywriting  # 添加视频文案
            }
            
            # 确保视频URL是完整可访问的链接
            if video.video_url and not video.video_url.startswith(('http://', 'https://')):
                # 如果URL不是完整链接，添加基础URL前缀（这里需要根据实际情况调整）
                # 例如，如果是本地存储的视频文件，可能需要添加基础URL
                # 这里假设视频URL已经是完整的，实际部署时可能需要根据存储方式调整
                if video.video_url.startswith('/'):
                    # 如果是相对路径，尝试构建完整URL
                    video_data["video_url"] = request.host_url.rstrip('/') + video.video_url
            
            video_list.append(video_data)
        
        return jsonify({
            "videos": video_list,
            "pagination": {
                "page": videos.page,
                "pages": videos.pages,
                "per_page": videos.per_page,
                "total": videos.total
            },
            "status": "success"
        }), 200
        
    except Exception as e:
        app_logger.error(f"获取用户视频列表失败: {str(e)}")
        return jsonify({
            "error": "获取视频列表过程中出现错误",
            "status": "failed"
        }), 500

@main.route('/user/videos/<int:video_id>', methods=['GET'])
@login_required
def get_user_video(video_id):
    """获取用户单个视频详情"""
    try:
        video = Video.query.filter_by(id=video_id, user_id=current_user.id).first()
        if not video:
            return jsonify({
                "error": "视频不存在或无权访问",
                "status": "failed"
            }), 404
            
        video_data = {
            "id": video.id,
            "status": video.status,
            "video_url": video.video_url,
            "created_at": video.created_at.isoformat() if video.created_at else None,
            "parsing_status": video.parsing_status,
            "storyboard_status": video.storyboard_status,
            "generation_status": video.generation_status,
            "concatenation_status": video.concatenation_status,
            "oss_upload_status": video.oss_upload_status,
            "video_error": video.video_error,
            "parsing_started_at": video.parsing_started_at.isoformat() if video.parsing_started_at else None,
            "parsing_completed_at": video.parsing_completed_at.isoformat() if video.parsing_completed_at else None,
            "storyboard_started_at": video.storyboard_started_at.isoformat() if video.storyboard_started_at else None,
            "storyboard_completed_at": video.storyboard_completed_at.isoformat() if video.storyboard_completed_at else None,
            "generation_started_at": video.generation_started_at.isoformat() if video.generation_started_at else None,
            "generation_completed_at": video.generation_completed_at.isoformat() if video.generation_completed_at else None,
            "concatenation_started_at": video.concatenation_started_at.isoformat() if video.concatenation_started_at else None,
            "concatenation_completed_at": video.concatenation_completed_at.isoformat() if video.concatenation_completed_at else None,
            "oss_upload_started_at": video.oss_upload_started_at.isoformat() if video.oss_upload_started_at else None,
            "oss_upload_completed_at": video.oss_upload_completed_at.isoformat() if video.oss_upload_completed_at else None
        }
        
        # 确保视频URL是完整可访问的链接
        if video.video_url and not video.video_url.startswith(('http://', 'https://')):
            # 如果URL不是完整链接，添加基础URL前缀
            if video.video_url.startswith('/'):
                # 如果是相对路径，尝试构建完整URL
                video_data["video_url"] = request.host_url.rstrip('/') + video.video_url
        
        return jsonify({
            "video": video_data,
            "status": "success"
        }), 200
        
    except Exception as e:
        app_logger.error(f"获取视频详情失败: {str(e)}")
        return jsonify({
            "error": "获取视频详情过程中出现错误",
            "status": "failed"
        }), 500

@main.route('/user/videos/<int:video_id>', methods=['DELETE'])
@login_required
def delete_user_video(video_id):
    """删除用户视频"""
    try:
        video = Video.query.filter_by(id=video_id, user_id=current_user.id).first()
        if not video:
            return jsonify({
                "error": "视频不存在或无权访问",
                "status": "failed"
            }), 404
            
        db.session.delete(video)
        db.session.commit()
        
        return jsonify({
            "message": "视频删除成功",
            "status": "success"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"删除视频失败: {str(e)}")
        return jsonify({
            "error": "删除视频过程中出现错误",
            "status": "failed"
        }), 500

@main.route('/recent-videos', methods=['GET'])
@login_required
def get_recent_videos():
    """获取用户最近的视频列表"""
    try:
        # 获取最近5个视频
        videos = Video.query.filter_by(user_id=current_user.id)\
            .order_by(Video.created_at.desc())\
            .limit(5)\
            .all()
        
        video_list = []
        for video in videos:
            # 尝试从copywriting中提取视频描述，如果不存在则使用默认文本
            description = "未命名视频"
            if video.copywriting:
                description = video.copywriting[:50] + "..." if len(video.copywriting) > 50 else video.copywriting
            elif video.title:
                description = video.title
            
            video_data = {
                "id": video.id,
                "status": video.status,
                "video_url": video.video_url,
                "created_at": video.created_at.isoformat() if video.created_at else None,
                "parsing_status": video.parsing_status,
                "storyboard_status": video.storyboard_status,
                "generation_status": video.generation_status,
                "concatenation_status": video.concatenation_status,
                "oss_upload_status": video.oss_upload_status,
                "video_error": video.video_error,
                "description": description,  # 添加视频描述
                "title": video.title,  # 添加视频标题
                "copywriting": video.copywriting  # 添加视频文案
            }
            
            # 确保视频URL是完整可访问的链接
            if video.video_url and not video.video_url.startswith(('http://', 'https://')):
                # 如果URL不是完整链接，添加基础URL前缀
                if video.video_url.startswith('/'):
                    # 如果是相对路径，尝试构建完整URL
                    video_data["video_url"] = request.host_url.rstrip('/') + video.video_url
            
            video_list.append(video_data)
        
        return jsonify({
            "videos": video_list,
            "status": "success"
        }), 200
        
    except Exception as e:
        app_logger.error(f"获取最近视频列表失败: {str(e)}")
        return jsonify({
            "error": "获取最近视频列表过程中出现错误",
            "status": "failed"
        }), 500

@main.route('/video-stats', methods=['GET'])
@login_required
def get_video_stats():
    """获取用户视频统计信息"""
    try:
        # 获取总视频数
        total_videos = Video.query.filter_by(user_id=current_user.id).count()
        
        # 获取已完成视频数
        completed_videos = Video.query.filter_by(user_id=current_user.id, status="completed").count()
        
        return jsonify({
            "total_videos": total_videos,
            "completed_videos": completed_videos,
            "status": "success"
        }), 200
        
    except Exception as e:
        app_logger.error(f"获取视频统计信息失败: {str(e)}")
        return jsonify({
            "error": "获取视频统计信息过程中出现错误",
            "status": "failed"
        }), 500
