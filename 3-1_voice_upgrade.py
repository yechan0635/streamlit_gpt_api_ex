import os
import time
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# ====== 기본 설정 ======
load_dotenv(override=True)
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

st.title("OpenAI's Text-to-Audio Response")

# 데모 이미지
st.image(
    "https://wikidocs.net/images/page/215361/%EC%9D%B8%EA%B3%B5%EC%A7%80%EB%8A%A5%EC%84%B1%EC%9A%B0.jpg",
    width=200
)

# ====== 프리셋 & 옵션 ======
voice_options = ['alloy', 'ash', 'coral', 'echo', 'fable', 'onyx', 'nova', 'sage', 'shimmer']
selected_voice = st.selectbox("성우(Voice)를 선택하세요", voice_options, index=0)

preset = st.selectbox(
    "프리셋 선택(선택 시 아래 입력란에 자동 채움)",
    ["직접 입력", "격려/모티베이션", "안심/케어", "공지/안내"],
    index=0
)

presets_text = {
    "격려/모티베이션": "포기하지 않는 간절한 꿈은 반드시 이루어집니다. 오늘도 한 걸음 전진해요!",
    "안심/케어": "괜찮아요. 지금의 속도로 충분합니다. 잠시 숨을 고르고 다시 시작해봐요.",
    "공지/안내": "안내 말씀드립니다. 잠시 후 서비스 점검이 시작됩니다. 이용에 참고 부탁드립니다."
}

default_text = presets_text.get(preset, "포기하지 않는 간절한 꿈은 꼭 이루어집니다.")
user_prompt = st.text_area("인공지능 성우가 읽을 스크립트", value=default_text, height=180)
st.caption(f"글자 수: {len(user_prompt)}")

fmt = st.radio("오디오 포맷", ["mp3", "wav"], horizontal=True)

# 저장 경로
OUTPUT_DIR = "output_audio"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 세션 히스토리 초기화
if "clips" not in st.session_state:
    st.session_state["clips"] = []  # [{path, voice, ts, text}]

# ====== 생성 버튼 ======
if st.button("Generate Audio"):
    if not user_prompt.strip():
        st.warning("스크립트를 입력해주세요.")
    else:
        try:
            with st.spinner("음성을 생성하는 중입니다…"):
                # OpenAI TTS 호출
                audio_response = client.audio.speech.create(
                    model="tts-1",
                    voice=selected_voice,
                    input=user_prompt,
                    format=fmt  # mp3 또는 wav
                )

                # 저장 파일명
                ts = int(time.time())
                filename = f"dub_{selected_voice}_{ts}.{fmt}"
                out_path = os.path.join(OUTPUT_DIR, filename)

                # 저장
                audio_bytes = audio_response.content
                with open(out_path, "wb") as f:
                    f.write(audio_bytes)

                st.success(f"생성 완료: {out_path}")
                st.audio(out_path, format=f"audio/{fmt}")

                # 다운로드 버튼
                with open(out_path, "rb") as f:
                    st.download_button(
                        label="⬇️ 파일 다운로드",
                        data=f.read(),
                        file_name=filename,
                        mime=f"audio/{fmt}"
                    )

                # 세션 히스토리에 추가
                st.session_state["clips"].append({
                    "path": out_path,
                    "voice": selected_voice,
                    "ts": ts,
                    "text": user_prompt[:120] + ("..." if len(user_prompt) > 120 else "")
                })

        except Exception as e:
            st.error("오류가 발생했습니다. 아래 내용을 참고하세요.")
            st.exception(e)

st.divider()

# ====== 생성 히스토리 ======
st.subheader("📜 생성 히스토리")
if not st.session_state["clips"]:
    st.info("아직 생성된 오디오가 없습니다.")
else:
    for i, clip in enumerate(reversed(st.session_state["clips"]), start=1):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{i}. Voice:** {clip['voice']} | **시간:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(clip['ts']))}")
            st.caption(clip["text"])
            st.audio(clip["path"], format=f"audio/{fmt}")
        with col2:
            with open(clip["path"], "rb") as f:
                st.download_button(
                    label="다운로드",
                    data=f.read(),
                    file_name=os.path.basename(clip["path"]),
                    mime=f"audio/{fmt}",
                    key=f"dl_{clip['ts']}"
                )

    