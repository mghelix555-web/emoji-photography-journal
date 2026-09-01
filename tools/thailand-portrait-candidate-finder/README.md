# Thailand Portrait Candidate Finder

Threads の公開投稿から、タイでポートレート撮影・TFP・コラボに関心がありそうな成人候補を探すための補助ツールです。

## Important policy

- 公開投稿だけを検索します。
- 顔・写真から年齢、国籍、民族、性別などを推測しません。
- 未成年と明示されている、または未成年を強く示す公開記述があるアカウントは除外します。
- 成人であることを外見から判断しません。DM前にプロフィール等で成人であることを手動確認してください。
- 「撮影OK」を断定しません。公開投稿にある TFP / collab / model / portrait などの明示的シグナルを基に優先度を付けるだけです。
- 候補一覧は公開GitHubへコミットしません。`output/` は `.gitignore` 対象です。

## Meta Threads API

このツールは Meta Threads API の `keyword_search` を使います。
必要権限の中心は `threads_keyword_search` です。

API host:

```text
https://graph.threads.net
```

## Setup

Python 3.11+ 推奨。

```bash
cd tools/thailand-portrait-candidate-finder
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
$env:THREADS_ACCESS_TOKEN="YOUR_LONG_LIVED_TOKEN"
python finder.py
```

オプション:

```powershell
python finder.py --search-type RECENT --limit 25
python finder.py --config config.json
```

## Output

`output/` に次を生成します。

- `candidates_latest.csv`
- `candidates_latest.md`
- `raw_posts_latest.json`

候補はスコア順です。

### Columns

- `username`
- `score`
- `adult_status`
- `matched_queries`
- `signals`
- `latest_text`
- `permalink`
- `timestamp`

`adult_status=manual_check_required` の候補は、DM前に成人であることをプロフィール等で確認してください。

## Ranking idea

高得点:

- TFP / collab / collaboration / model call
- `หาช่างภาพ`（カメラマン募集）
- `ถ่ายแบบ`（モデル撮影）
- `อยากถ่ายรูป`（写真を撮りたい）
- Bangkok / กรุงเทพ / Chiang Mai / เชียงใหม่ などタイ国内ロケーション
- portrait / photographer / model 関連語

除外・強い警告:

- 明示的に 18 歳未満と書かれている投稿
- school / high school / ม.ปลาย 等、未成年の可能性が高い自己記述

## Recommended workflow

1. Threads API で候補発見
2. 上位候補だけInstagram/Threadsプロフィールを手動確認
3. 成人確認
4. 撮影作例・活動内容を確認
5. 個別にタイ語DMを作成
6. 返信がない相手への連投・大量DMはしない

このツールは候補探索の補助であり、本人の同意を予測・保証するものではありません。
