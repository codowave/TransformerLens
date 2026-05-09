"""
スウェーデンボルグ相応の辞典 — FastAPI バックエンド
Claude Opus 4.6 + ストリーミング + プロンプトキャッシュ
"""

import json
import logging
import os
import re
from pathlib import Path

import anthropic
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from lexicon.lexicon_router import router as lexicon_router
from lexicon.biblical_lexicon import verify_verse, lookup_verse, lookup_word
from correspondence.correspondence_lookup import build_correspondence_context

log = logging.getLogger(__name__)

app = FastAPI(title="スウェーデンボルグ相応の辞典")
app.include_router(lexicon_router, prefix="/api/lexicon")

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

【原語照合に関する厳守事項】
ユーザーメッセージに verified_lexicon_context が含まれている場合、それを原語・Strong's・節内出現に関する一次根拠として扱うこと。
照合済みコンテキストに存在しないヘブライ語・ギリシャ語を、その節に出現すると断定してはならない。
存在しない場合は「照合上、その語は当該節に確認できない」と明示し、内意・相応の考察と原語事実を必ず分離すること。

【内意照合に関する厳守事項】
ユーザーメッセージに verified_correspondence_context が含まれている場合、照合状態を必ず確認してから応答すること。

照合状態の三値を厳密に区別する:
  found       : インデックスに記述が存在する → その内容を根拠として引用してよい
  not_found   : 索引範囲内だが対応記述なし → 「索引済み範囲に直接記述なし」と明示してから考察する
  unavailable : 索引未整備 → 「この節の索引は未整備」と明示し、記憶による相応断定をしてはならない

「索引に見つからない」と「スウェーデンボルグが言及していない」は異なる。
状態が unavailable または not_found のとき、「スウェーデンボルグはこの節について述べていない」と断定してはならない。
"""

# ---------------------------------------------------------------------------
# Lexicon context injection
# ---------------------------------------------------------------------------
_OSIS_RE    = re.compile(r'\b([1-3]?[A-Z][a-z]+(?:[A-Z][a-z]+)?)\.(\d+)\.(\d+)\b')
_BIBLE_RE   = re.compile(r'\b([1-3]?[A-Z][a-z]+(?:[A-Z][a-z]+)?)\s+(\d+):(\d+)\b')
_STRONGS_RE = re.compile(r'\b([HG]\d+[a-z]?)\b', re.IGNORECASE)


def _extract_refs(text: str) -> list[str]:
    refs: set[str] = set()
    for m in _OSIS_RE.finditer(text):
        refs.add(m.group(0))
    for m in _BIBLE_RE.finditer(text):
        refs.add(f"{m.group(1)}.{m.group(2)}.{m.group(3)}")
    return list(refs)


def _extract_strongs(text: str) -> list[str]:
    return list({m.group(1).upper() for m in _STRONGS_RE.finditer(text)})


def build_lexicon_context(text: str) -> str:
    """Extract Bible refs and Strong's IDs from user text, query the lexicon,
    and return a verified_lexicon_context block to inject into the prompt.
    Returns empty string when no refs are detected or data is unavailable.
    """
    refs = _extract_refs(text)
    strongs_ids = _extract_strongs(text)
    if not refs and not strongs_ids:
        return ""

    lines = ["【verified_lexicon_context — 本文照合済み原語データ】"]

    # verse × strongs cross-verification
    for ref in refs:
        for sid in strongs_ids:
            try:
                r = verify_verse(ref, sid)
                status = "存在 ✓" if r["contains"] else "不在 ✗"
                lines.append(f"  {ref} / {sid}: {status}  (出現数={r['occurrences']})")
                for w in r.get("words", []):
                    lines.append(
                        f"    surface={w['surface']}  translit={w['translit']}  morph={w['morph']}"
                    )
            except Exception as exc:
                log.debug("verify_verse(%s, %s) skipped: %s", ref, sid, exc)

    # verse-only lookup when no Strong's given
    if refs and not strongs_ids:
        for ref in refs:
            try:
                verse = lookup_verse(ref)
                flat = [s for w in verse.words for s in w.strongs]
                lines.append(f"  {ref} ({verse.language}) Strong's sequence: {flat}")
            except Exception as exc:
                log.debug("lookup_verse(%s) skipped: %s", ref, exc)

    # Strong's dictionary entries
    for sid in strongs_ids:
        try:
            entry = lookup_word(sid)
            lemma = entry.get("lemma", "")
            xlit  = entry.get("xlit") or entry.get("translit") or ""
            defn  = (entry.get("strongs_def") or "")[:150]
            lines.append(f"  {sid}: {lemma} ({xlit}) — {defn}")
        except Exception as exc:
            log.debug("lookup_word(%s) skipped: %s", sid, exc)

    return "\n".join(lines) if len(lines) > 1 else ""

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

    refs = _extract_refs(request.message)

    lexicon_ctx = build_lexicon_context(request.message)
    correspondence_ctx = "\n\n".join(
        ctx for ref in refs
        if (ctx := build_correspondence_context(ref))
    )

    injected_parts = [request.message]
    if lexicon_ctx:
        injected_parts.append(lexicon_ctx)
    if correspondence_ctx:
        injected_parts.append(correspondence_ctx)
    messages.append({"role": "user", "content": "\n\n".join(injected_parts)})

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
