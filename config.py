import os
from dotenv import load_dotenv

# .env 파일이 존재하면 해당 파일의 환경 변수를 로드합니다.
load_dotenv()

# 환경 변수에서 "GOOGLE_MAPS_API_KEY" 값을 가져옵니다.
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
