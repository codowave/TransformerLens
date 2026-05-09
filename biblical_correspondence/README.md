# スウェーデンボルグ相応の辞典

聖書の言葉の霊的内意（相応）をリアルタイムで参照・対話できるモバイル対応Webアプリ。

## 機能

- **💬 AIチャット** — Claude Opus 4.6がスウェーデンボルグの相応の原理に基づいてリアルタイム回答（ストリーミング）
- **📖 辞典ブラウズ** — 60以上のエントリをカテゴリ・キーワードで検索
- **📱 PWA対応** — Androidの「ホーム画面に追加」でアプリとして使用可能

## セットアップ

```bash
cd biblical_correspondence
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"
python app.py
```

ブラウザで `http://localhost:8000` を開く。

## Androidスマホでの使い方

1. 同じWi-Fiに接続したPCでサーバーを起動
2. Androidの Chrome で `http://[PCのIPアドレス]:8000` を開く
3. メニュー → 「ホーム画面に追加」でアプリとしてインストール

または、Railway / Renderなどにデプロイして外部からアクセス。

## スウェーデンボルグの主要典拠

| 略号 | 著作名 |
|------|--------|
| AC | 天界の秘義 (Arcana Coelestia) |
| HH | 天界と地獄 (Heaven and Hell) |
| DLW | 神の愛と知恵 (Divine Love and Wisdom) |
| AE | 黙示録の解説 (Apocalypse Explained) |
