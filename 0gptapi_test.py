from dotenv import load_dotenv
import os
from openai import OpenAI

# .env 파일의 내용을 로드
load_dotenv(override=True)

# 환경 변수 가져오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# openai api 인증 및 OpenAI 객체 생성
client = OpenAI(api_key=OPENAI_API_KEY)

# 챗 컴플리션 실행
completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "너는 IT전문가야."},
        {"role": "user", "content": "전 세계에서 가장 많이 사용하는 프로그래밍 언어는 뭐야?"}
    ]
)

# 결과 출력
print(completion.choices[0].message)