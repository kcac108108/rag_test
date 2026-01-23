import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 1. 환경 변수 로드
load_dotenv()

# 2. LLM 초기화 (설치가 잘 되었는지 확인)
try:
    llm = ChatOpenAI(model="gpt-4o-mini")
    response = llm.invoke("안녕? RAG 개발 환경 세팅 중이야.")
    print("성공적으로 응답을 받았습니다:")
    print(response.content)
except Exception as e:
    print(f"설정 중 오류가 발생했습니다: {e}")