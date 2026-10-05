import sys
import os

# 상위 디렉터리(루트)의 app.py를 안전하게 참조하도록 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
