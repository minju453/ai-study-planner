import sys
import os

# 프로젝트 루트 디렉터리를 sys.path의 최우선(0번)으로 등록
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app import app

# Vercel WSGI entry point
app = app
