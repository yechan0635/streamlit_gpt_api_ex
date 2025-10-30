import os
import time
import re
import PyPDF2
from docx import Document

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ================== 공통 설정 ==================
st.set_page_config(page_title="AI Voice Studio", layout="centered")
load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("🚨 OpenAI API Key가 설정되지 않았습니다. .env 파일을 확인해 주세요.")
client = OpenAI(api_key=OPENAI_API_KEY)

# 세션 히스토리 초기화
if "clips" not in st.session_state:
    st.session_state["clips"] = []  # [{path, voice, fmt, ts, text, source}]

OUTPUT_DIR = "output_audio"
os.makedirs(OUTPUT_DIR, exist_ok=True)

VOICE_OPTIONS = ['alloy', 'ash', 'coral', 'echo', 'fable', 'onyx', 'nova', 'sage', 'shimmer']

def safe_filename(name: str) -> str:
    return re.sub(r"[^0-9a-zA-Z._-]+", "_", name)

# =============== 공통 유틸 ===============
def save_audio_bytes(b: bytes, voice: str, fmt: str, prefix: str) -> str:
    ts = int(time.time())
    fname = safe_filename(f"{prefix}_{voice}_{ts}.{fmt}")
    path = os.path.join(OUTPUT_DIR, fname)
    with open(path, "wb") as f:
        f.write(b)
    return path

def tts(text: str, voice: str, response_format: str = "mp3") -> bytes:
    """
    OpenAI TTS 호출. response_format 사용 (format 아님!)
    """
    resp = client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
        response_format=response_format
    )
    return resp.content

def translate_text(text: str, target_language_name: str) -> str:
    """
    Chat Completions 기반 간단 번역 (저비용/빠른 응답을 원할 때 gpt-4o-mini 권장)
    """
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"You are a translator. Translate the user's sentence into {target_language_name}. Return only the translation."},
            {"role": "user", "content": text}
        ],
        temperature=0,
        max_tokens=1000
    )
    return resp.choices[0].message.content.strip()

def recommend_voice_by_rules(prompt: str) -> str:
    """
    간단 규칙 기반 보이스 추천 (3-1_voice.py에서 확장)
    """
    if any(w in prompt for w in ["꿈", "희망", "용기", "행복", "응원", "화이팅"]):
        return "nova"
    if any(w in prompt for w in ["어둠", "위기", "전쟁", "공포", "슬픔"]):
        return "onyx"
    if any(w in prompt for w in ["사랑", "추억", "감성", "그리움"]):
        return "fable"
    if any(w in prompt for w in ["기술", "로봇", "미래", "데이터", "AI"]):
        return "echo"
    if any(w in prompt for w in ["공지", "안내", "설명", "기업", "매뉴얼"]):
        return "sage"
    return "alloy"

def recommend_voice_by_llm(text: str) -> str:
    """
    LLM 기반 보이스 추천 (3-3_voice_test.py 아이디어를 chat.completions로 안전화)
    반드시 VOICE_OPTIONS 중 하나만 반환하도록 지시
    """
    system_prompt = (
        "너는 텍스트를 읽기 좋은 음성을 골라주는 어시스턴트야.\n"
        "반드시 아래 목록 중 하나만 소문자로 출력해.\n"
        "목록: alloy, ash, coral, echo, fable, onyx, nova, sage, shimmer.\n"
        "설명/공지/안내/매뉴얼/기업 공지 → sage 또는 alloy\n"
        "교육/학습/튜토리얼 → nova\n"
        "아이/이야기/동화/따뜻한 톤 → fable\n"
        "밝고 경쾌 → coral\n"
        "기타는 alloy\n"
        "다른 말 하지 마. 이유도 말하지 마. 하나만."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"이 텍스트에 어울리는 음성을 골라줘:\n{text}"}
        ],
        temperature=0
    )
    voice = resp.choices[0].message.content.strip().lower()
    if voice not in VOICE_OPTIONS:
        voice = "alloy"
    return voice

# ================== UI: 탭 구성 ==================
st.title("🎙️ AI Voice Studio")
tabs = st.tabs(["🗣️ 텍스트 → 오디오", "📊 보고서 업로드 → 요약 → 오디오", "📜 생성 히스토리"])

# ============== 탭 1: 텍스트 → 오디오 ==============
with tabs[0]:
    st.subheader("🗣️ 텍스트 → 오디오 (번역/보이스 자동추천 포함)")
    st.caption("원문 언어로 바로 생성하거나, 선택 언어로 번역 후 생성할 수 있어요.")

    colA, colB = st.columns([3, 2])
    with colA:
        default_text = "포기하지 않는 간절한 꿈은 꼭 이루어집니다."
        user_prompt = st.text_area("스크립트 입력", value=default_text, height=160)

    with colB:
        st.markdown("**보이스 선택 모드**")
        mode = st.radio(
            label="",
            options=["수동 선택", "룰 기반 추천", "LLM 기반 추천"],
            horizontal=False,
            index=1
        )
        manual_voice = st.selectbox("수동 선택 시 보이스", VOICE_OPTIONS, index=VOICE_OPTIONS.index("alloy"))

        st.markdown("**번역 옵션**")
        do_translate = st.checkbox("선택 언어로 번역 후 TTS", value=False)
        languages = {
            "한국어": "Korean",
            "영어": "English",
            "일본어": "Japanese",
            "중국어(간체)": "Chinese (Simplified)",
            "스페인어": "Spanish",
            "프랑스어": "French",
        }
        target_lang_name = st.selectbox("번역 대상 언어", list(languages.keys()), index=0)
        out_fmt = st.radio("오디오 포맷", ["mp3", "wav"], index=0, horizontal=True)

    if st.button("🔊 오디오 생성"):
        if not user_prompt.strip():
            st.warning("스크립트를 입력해 주세요.")
        else:
            try:
                # 1) 보이스 결정
                if mode == "수동 선택":
                    voice = manual_voice
                elif mode == "룰 기반 추천":
                    voice = recommend_voice_by_rules(user_prompt)
                else:
                    with st.spinner("AI가 어울리는 보이스를 고르는 중…"):
                        voice = recommend_voice_by_llm(user_prompt)

                # 2) 번역 (선택)
                final_text = user_prompt
                if do_translate:
                    with st.spinner("번역 중…"):
                        final_text = translate_text(user_prompt, languages[target_lang_name])

                # 3) TTS
                with st.spinner("음성 생성 중…"):
                    audio_bytes = tts(final_text, voice=voice, response_format=out_fmt)

                # 4) 저장/재생/다운로드
                path = save_audio_bytes(audio_bytes, voice=voice, fmt=out_fmt, prefix="tts")
                st.success(f"✅ 생성 완료: {os.path.basename(path)} (voice={voice})")
                st.audio(path, format=f"audio/{out_fmt}")
                with open(path, "rb") as f:
                    st.download_button("⬇️ 다운로드", data=f.read(), file_name=os.path.basename(path), mime=f"audio/{out_fmt}")

                # 히스토리 기록
                st.session_state["clips"].append({
                    "path": path, "voice": voice, "fmt": out_fmt, "ts": int(time.time()),
                    "text": final_text[:120] + ("..." if len(final_text) > 120 else ""),
                    "source": "text"
                })

            except Exception as e:
                st.error("오디오 생성 중 오류가 발생했습니다.")
                st.exception(e)

# ============== 탭 2: 보고서 업로드 → 요약 → 오디오 ==============
with tabs[1]:
    st.subheader("📊 컨설턴트용 리포트 자동 요약 & 오디오 브리핑")
    st.caption("PDF / DOCX / TXT를 업로드하면 한국어로 핵심 요약 후 오디오로 만들어드립니다.")

    uploaded_file = st.file_uploader("보고서를 업로드하세요", type=["pdf", "docx", "txt"])
    # 보이스 선택(수동) + 안내
    sel_voice = st.selectbox("보이스 선택", VOICE_OPTIONS, index=VOICE_OPTIONS.index("nova"))
    out_fmt2 = st.radio("오디오 포맷", ["mp3", "wav"], index=0, horizontal=True, key="fmt2")

    text = ""
    if uploaded_file is not None:
        with st.spinner("파일을 읽는 중입니다…"):
            try:
                ext = uploaded_file.name.split(".")[-1].lower()
                if ext == "pdf":
                    reader = PyPDF2.PdfReader(uploaded_file)
                    text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
                elif ext == "docx":
                    doc = Document(uploaded_file)
                    text = " ".join([p.text for p in doc.paragraphs])
                elif ext == "txt":
                    text = uploaded_file.read().decode("utf-8")
            except Exception as e:
                st.error("파일을 읽는 중 오류가 발생했습니다.")
                st.exception(e)
                text = ""

        if len(text) < 100:
            st.warning("본문 내용이 너무 짧습니다. 파일을 확인해 주세요.")
        else:
            st.success(f"본문 길이: {len(text)}자")
            if st.checkbox("본문 미리보기"):
                st.text_area("본문 일부", value=text[:2000], height=200)

            if st.button("🧭 한국어 요약 생성"):
                with st.spinner("AI가 컨설팅 요약을 작성 중입니다…"):
                    try:
                        # 한국어 컨설팅 요약
                        summary_prompt = f"""
                        아래는 컨설팅 보고서 본문 일부입니다.
                        핵심 경영 인사이트, 시사점, 권고사항 중심으로
                        20줄 이내의 한국어 핵심 요약문을 작성해주세요.
                        불필요한 전문용어나 영어 표현은 지양하고,
                        경영진이 이해하기 쉽게 간결한 문체로 정리해주세요.

                        본문:
                        {text[:12000]}
                        """
                        summary_resp = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "너는 맥킨지 출신의 전략 컨설턴트다. 모든 답변은 반드시 한국어로 작성한다."},
                                {"role": "user", "content": summary_prompt}
                            ],
                            temperature=0.4,
                        )
                        summary_text = summary_resp.choices[0].message.content.strip()

                        st.markdown("**🧭 핵심 요약 결과**")
                        st.write(summary_text)

                        # TTS 변환
                        st.info("요약 내용을 음성으로 변환합니다…")
                        audio_bytes = tts(summary_text, voice=sel_voice, response_format=out_fmt2)

                        path = save_audio_bytes(audio_bytes, voice=sel_voice, fmt=out_fmt2, prefix="summary_brief")
                        st.success(f"✅ 생성 완료: {os.path.basename(path)} (voice={sel_voice})")
                        st.audio(path, format=f"audio/{out_fmt2}")
                        with open(path, "rb") as f:
                            st.download_button("⬇️ 오디오 브리핑 다운로드", data=f.read(),
                                               file_name=os.path.basename(path), mime=f"audio/{out_fmt2}")

                        # 히스토리 저장
                        st.session_state["clips"].append({
                            "path": path, "voice": sel_voice, "fmt": out_fmt2, "ts": int(time.time()),
                            "text": summary_text[:120] + ("..." if len(summary_text) > 120 else ""),
                            "source": "report"
                        })

                    except Exception as e:
                        st.error("요약/오디오 생성 중 오류가 발생했습니다.")
                        st.exception(e)

# ============== 탭 3: 생성 히스토리 ==============
with tabs[2]:
    st.subheader("📜 생성 히스토리")
    if not st.session_state["clips"]:
        st.info("아직 생성된 오디오가 없습니다.")
    else:
        for i, clip in enumerate(reversed(st.session_state["clips"]), start=1):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(
                    f"**{i}. Voice:** {clip['voice']} | "
                    f"**시간:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(clip['ts']))} | "
                    f"**출처:** { '텍스트' if clip.get('source')=='text' else '보고서'}"
                )
                st.caption(clip["text"])
                st.audio(clip["path"], format=f"audio/{clip['fmt']}")
            with col2:
                with open(clip["path"], "rb") as f:
                    st.download_button("다운로드", data=f.read(),
                                       file_name=os.path.basename(clip["path"]),
                                       mime=f"audio/{clip['fmt']}",
                                       key=f"dl_{clip['ts']}")
    