"""
スウェーデンボルグ相応の辞典 — FastAPI バックエンド
Claude Opus 4.6 + ストリーミング + プロンプトキャッシュ
"""

import json
import os
from pathlib import Path

import anthropic
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="スウェーデンボルグ相応の辞典")

# 辞典データを起動時に読み込む
DICT_PATH = Path(__file__).parent / "data" / "dictionary.json"
with open(DICT_PATH, encoding="utf-8") as f:
    DICTIONARY = json.load(f)

# 辞典の全エントリをテキスト形式にまとめる（システムプロンプトに埋め込む）
def build_dict_text() -> str:
    lines = ["【スウェーデンボルグ相応の辞典データ】\n"]
    for entry in DICTIONARY["entries"]:
        lines.append(f"◆ {entry['word']}")
        lines.append(f"  字義: {entry['literal']}")
        lines.append(f"  霊的内意: {entry['spiritual']}")
        lines.append(f"  価値の転換: {entry['value_shift']}")
        lines.append(f"  典拠: {entry['reference']}")
        lines.append(f"  分類: {entry['category']}\n")
    return "\n".join(lines)

DICT_TEXT = build_dict_text()

SYSTEM_PROMPT = f"""あなたはエマニュエル・スウェーデンボルグの「相応の原理」に精通した霊的案内人です。

スウェーデンボルグは、聖書のすべての言葉には字義的意味（外的意味）の奥に霊的内意（内的意味）があり、
自然界のあらゆるものは霊的世界の何かに「相応」していると教えました。

以下の辞典データを参照しながら、ユーザーの質問に答えてください：

{DICT_TEXT}

【応答の指針】
1. 字義的意味と霊的内意を明確に区別して説明する
2. 「価値の転換」を具体的に示す（例：「○○は△△ではなく、実は□□を意味する」）
3. 典拠となるスウェーデンボルグの著作や聖書箇所を引用する
4. 日本語で、温かく分かりやすい言葉で説明する
5. 辞典にない言葉も、相応の原理に従って考察する

スウェーデンボルグの主な著作：天界の秘義(AC)、天界と地獄(HH)、神の愛と知恵(DLW)、黙示録の解説(AE)
"""

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY is not set")
client_ai = anthropic.AsyncAnthropic(api_key=api_key)


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


async def stream_response(request: ChatRequest):
    """Claude API からストリーミングレスポンスを生成"""
    messages = request.history.copy()
    messages.append({"role": "user", "content": request.message})

    async with client_ai.messages.stream(
        model="claude-opus-4-6",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # 辞典データをキャッシュ
            }
        ],
        messages=messages,
    ) as stream:
        async for event in stream:
            if event.type == "content_block_delta":
                if event.delta.type == "text_delta":
                    # SSE 形式で送信
                    yield f"data: {json.dumps({'text': event.delta.text}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


@app.post("/api/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        stream_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/dictionary")
async def get_dictionary():
    """辞典データをJSONで返す"""
    return DICTIONARY


@app.get("/api/search")
async def search_dictionary(q: str):
    """キーワードで辞典を検索"""
    q_lower = q.lower()
    results = [
        e for e in DICTIONARY["entries"]
        if q_lower in e.get("word", "").lower()
        or q_lower in e.get("spiritual", "").lower()
        or q_lower in e.get("literal", "").lower()
        or q_lower in e.get("category", "").lower()
    ]
    return {"results": results, "count": len(results)}


# 静的ファイル（モバイルUI）
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    return FileResponse(str(static_dir / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
