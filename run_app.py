#!/usr/bin/env python3
"""
Flask应用启动脚本
"""

import os
import sys

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ai_movie.web import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)