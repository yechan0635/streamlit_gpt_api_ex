import io
import PyPDF2
from docx import Document
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import time


# .env 파일 경로 지정 
load_dotenv(override=True)
# Open AI API 키 설정하기
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(
    api_key = OPENAI_API_KEY
)


# 세션 상태 초기화
if "clips" not in st.session_state:
    st.session_state["clips"] = []

# ================= 보고서 업로드 및 자동 요약 =================
st.divider()
st.header("📊 컨설턴트용 리포트 자동 요약 & 오디오 브리핑")

uploaded_file = st.file_uploader("보고서를 업로드하세요 (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

# 인공지능 성우 선택 박스를 생성.
# 공식 문서 참고: https://platform.openai.com/docs/guides/text-to-speech
options = ['alloy', 'ash', 'coral', 'echo', 'fable', 'onyx', 'nova', 'sage', 'shimmer']
selected_option = st.selectbox("성우를 선택하세요:", options)


if uploaded_file is not None:
    with st.spinner("파일을 읽는 중입니다..."):
        text = ""
        file_type = uploaded_file.name.split(".")[-1].lower()

        try:
            if file_type == "pdf":
                reader = PyPDF2.PdfReader(uploaded_file)
                text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
            elif file_type == "docx":
                doc = Document(uploaded_file)
                text = " ".join([para.text for para in doc.paragraphs])
            elif file_type == "txt":
                text = uploaded_file.read().decode("utf-8")
        except Exception as e:
            st.error("파일을 읽는 중 오류가 발생했습니다.")
            st.exception(e)
            text = ""

    # 본문 확인
    if len(text) < 100:
        st.warning("본문 내용이 너무 짧습니다. 다시 확인해주세요.")
    else:
        st.success(f"본문 길이: {len(text)}자")
        if st.checkbox("본문 미리보기"):
            st.text_area("본문 일부", value=text[:2000], height=200)

        # ===== 요약 생성 =====
        if st.button("요약 생성하기"):
            with st.spinner("AI가 컨설팅 요약을 작성 중입니다..."):
                try:
                    summary_prompt = f"""
                    아래는 컨설팅 보고서 본문 일부입니다.
                    핵심 경영 인사이트, 시사점, 권고사항 중심으로
                    20줄 이내의 한국어 핵심 요약문을 작성해주세요.
                    불필요한 전문용어나 영어 표현은 지양하고, 
                    경영진이 이해하기 쉽게 간결한 문체로 정리해주세요.
                    \n\n본문:\n{text[:20000]}
                    """
                    summary_resp = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "너는 맥킨지 출신의 전략 컨설턴트다. concise하고 논리적인 요약문을 작성한다."},
                            {"role": "user", "content": summary_prompt}
                        ],
                        temperature=0.4,
                    )
                    summary_text = summary_resp.choices[0].message.content.strip()

                    st.subheader("🧭 핵심 요약 결과")
                    st.write(summary_text)

                    # ===== TTS 변환 =====
                    st.info("요약 내용을 음성으로 변환합니다...")
                    tts_bytes = client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=summary_text,
                        response_format="mp3"
                    ).content

                    os.makedirs("output_audio", exist_ok=True)
                    audio_path = f"output_audio/summary_brief_{int(time.time())}.mp3"
                    with open(audio_path, "wb") as f:
                        f.write(tts_bytes)

                    st.audio(audio_path, format="audio/mp3")
                    with open(audio_path, "rb") as f:
                        st.download_button("⬇️ 오디오 브리핑 다운로드", data=f, file_name="summary_brief.mp3")

                    # 세션 히스토리 기록 (기존 clips에도 추가 가능)
                    st.session_state["clips"].append({
                        "path": audio_path,
                        "voice": "nova",
                        "fmt": "mp3",
                        "ts": int(time.time()),
                        "text": summary_text[:120] + ("..." if len(summary_text) > 120 else ""),
                        "srt_path": None
                    })

                except Exception as e:
                    st.error("요약 생성 중 오류가 발생했습니다.")
                    st.exception(e)

    