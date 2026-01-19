# telegram-crawler
## How To Use

### Configuration settings
- [TELEGRAM]
    - Accesses(https://core.telegram.org/) and make Token
- [PROXY]
    - If you want to do the proxy, You can do it.
- [EXCEPT CHANNEL]
    - For example, except for the Default channel
- [OUTPUT]
    - `output_file`: JSON出力ファイルの保存先パス（`telegram_crawler_cron.py`のみ）
    - デフォルト: `telegram_messages.json`
    - 例: `output_file=output/telegram_messages.json`
    - **注意**: 実行時に日時（JST、形式: `YYYYMMDD_HHMMSS`）が自動的にファイル名の先頭に追加されます
    - 例: `output/telegram_messages.json` → `output/20260117_143000_telegram_messages.json`

### Dockerfile with Docker
```
$ docker image build -t telegram-crawler:v1 .

$ docker run --name  telegram-crawler -it telegram-crawler:v1
> Please enter your phone (or bot token): <phone number>
```

### Python in local 
```
$ python -V
Python 3.10.3

$ pip install --no-cache-dir -r requirements.txt

$ python telegram_crawler.py
> Please enter your phone (or bot token): <phone number>
```

### Cronで定期実行（Ubuntu/Linux）

#### 1. プロジェクトの配置場所

推奨配置場所：
- `/opt/telegram-crawler/` （システム全体で使用する場合）
- `/home/username/telegram-crawler/` （ユーザー専用の場合）

```bash
# プロジェクトを配置
sudo mkdir -p /opt/telegram-crawler
sudo cp -r telegram-crawler/* /opt/telegram-crawler/
cd /opt/telegram-crawler

# 依存関係のインストール
sudo pip3 install -r requirements.txt

# 初回実行（認証用）
sudo python3 telegram_crawler_cron.py
```

#### 2. Cronの設定

```bash
# Cron設定を編集
crontab -e

# 例: 毎時0分に実行
0 * * * * cd /opt/telegram-crawler && /usr/bin/python3 telegram_crawler_cron.py >> /var/log/telegram-crawler.log 2>&1

# 例: 30分ごとに実行
*/30 * * * * cd /opt/telegram-crawler && /usr/bin/python3 telegram_crawler_cron.py >> /var/log/telegram-crawler.log 2>&1

# 例: 毎日午前2時に実行
0 2 * * * cd /opt/telegram-crawler && /usr/bin/python3 telegram_crawler_cron.py >> /var/log/telegram-crawler.log 2>&1
```

#### 3. ログの確認

```bash
# 実行ログを確認
tail -f /var/log/telegram-crawler.log

# または、ユーザーディレクトリにログを保存する場合
# crontab -e で以下に変更:
# 0 * * * * cd /opt/telegram-crawler && /usr/bin/python3 telegram_crawler_cron.py >> ~/telegram-crawler.log 2>&1
```

#### 4. 注意事項

- **パスの指定**: Cronでは環境変数が限定的なため、`/usr/bin/python3`のように絶対パスを使用
- **作業ディレクトリ**: `cd /opt/telegram-crawler`で作業ディレクトリを指定（`config.ini`の読み込みのため）
- **権限**: セッションファイル（`CAnonBot.session`）や出力ファイルの書き込み権限を確認
- **環境変数**: 必要に応じてCronの環境変数を設定

## Output

### Output Format
プログラムは、取得したメッセージをJSON形式で標準出力に出力します。各メッセージは以下のフィールドを含みます：

- **channel_name**: チャンネル名
- **message_id**: メッセージID
- **message**: メッセージのテキスト内容
- **message_from_geo**: 位置情報（ある場合）
- **JST_send_time**: メッセージ送信時刻（JST形式: "YYYY/MM/DD HH:MM:SS"）
- **display_of_post_author**: 投稿者の表示名（チャンネル投稿の場合）
- **from_id**: 送信元のID（以下のいずれか）
  - `peerUser`: ユーザーID
  - `peerChat`: チャットID
  - `peerChannel`: チャンネルID
  - `anonymous`: 匿名（null）
- **sender_user**: 送信者情報（ボットでない場合）
  - `user_id`: ユーザーID
  - `username`: ユーザー名
  - `phone`: 電話番号
  - `Firstname`: 名
  - `Lastname`: 姓
- **bot**: ボットかどうか（true/false）

### Output Example

#### telegram_crawler.py (常時実行版)
```
> python telegram_crawler.py
('{\n'
 '  "1xxxxxxxxx": {\n'
 '    "channel_name": "xxxxx",\n'
 '    "message_id": 11111,\n'
 '    "message": "XXXXX",\n'
 '    "message_from_geo": null,\n'
 '    "JST_send_time": "2023/06/02 04:00:05",\n'
 '    "display_of_post_author": null,\n'
 '    "from_id": {\n'
 '      "peerUser": 1xxxxxxx\n'
 '    },\n'
 '    "sender_user": {\n'
 '      "user_id": 1xxxxxxx,\n'
 '      "username": "xxxx",\n'
 '      "phone": null,\n'
 '      "Firstname": "xxx",\n'
 '      "Lastname": null\n'
 '    },\n'
 '    "bot": false\n'
 '  }\n'
 '}')
...
```

#### telegram_crawler_cron.py (都度実行版)
```
> python telegram_crawler_cron.py
前回実行時刻: 2024-01-15 10:30:00+00:00
('{\n'
 '  "1xxxxxxxxx": {\n'
 '    "channel_name": "xxxxx",\n'
 '    "message_id": 11111,\n'
 '    "message": "XXXXX",\n'
 '    "message_from_geo": null,\n'
 '    "JST_send_time": "2024/01/15 14:35:20",\n'
 '    "display_of_post_author": null,\n'
 '    "from_id": {\n'
 '      "peerUser": 1xxxxxxx\n'
 '    },\n'
 '    "sender_user": {\n'
 '      "user_id": 1xxxxxxx,\n'
 '      "username": "xxxx",\n'
 '      "phone": null,\n'
 '      "Firstname": "xxx",\n'
 '      "Lastname": null\n'
 '    },\n'
 '    "bot": false\n'
 '  }\n'
 '}')
処理完了: 5件のメッセージを処理しました
```

### Output to File

#### telegram_crawler.py (常時実行版)
標準出力をファイルにリダイレクトして保存：

```bash
python telegram_crawler.py > output.log 2>&1
```

#### telegram_crawler_cron.py (都度実行版)
**方法1: config.iniで設定（推奨）**

`config.ini`の`[OUTPUT]`セクションで出力ファイルを指定：

```ini
[OUTPUT]
output_file=output/telegram_messages.json
```

実行すると、処理したメッセージが自動的にJSONファイルに保存されます。ファイル名には実行時の日時（JST）が自動的に先頭に追加されます：

```bash
python telegram_crawler_cron.py
# → output/20260117_143000_telegram_messages.json に保存される
#    形式: YYYYMMDD_HHMMSS_元のファイル名
```

**ファイル名の形式：**
- 設定: `output/telegram_messages.json`
- 実際のファイル名: `output/20260117_143000_telegram_messages.json`
- 日時はJST（日本標準時）で、形式は `YYYYMMDD_HHMMSS` です

**方法2: 標準出力をリダイレクト**

```bash
python telegram_crawler_cron.py >> output.log 2>&1
```

**JSONファイルの形式**

`telegram_crawler_cron.py`は、すべてのメッセージを配列形式でJSONファイルに保存します：

```json
[
  {
    "channel_id": {
      "channel_name": "...",
      "message_id": 123,
      "message": "...",
      ...
    }
  },
  {
    "channel_id": {
      ...
    }
  }
]
```

実行のたびに、既存のファイルを読み込んで新しいメッセージを追加します。

## メディアファイルのダウンロード

取得したメッセージIDとチャンネルIDを使って、写真や動画などのメディアファイルをダウンロードできます。

### 方法1: ダウンロード用スクリプトを使用

`download_media_example.py`を使用してメディアをダウンロードします：

```python
from download_media_example import download_media_by_id
import asyncio

# JSON出力から取得した情報を使用
# 例: {"media": {"download_info": {"channel_id": 123456, "message_id": 12345}}}
asyncio.run(download_media_by_id(
    api_id="your_api_id",
    api_hash="your_api_hash",
    channel_id=-1001234567890,  # チャンネルID（-100プレフィックス付き）
    message_id=12345,  # メッセージID
    output_dir="downloads"
))
```

### 方法2: メッセージオブジェクトから直接ダウンロード

メッセージオブジェクトがある場合、直接ダウンロードできます：

```python
# メッセージオブジェクトから直接ダウンロード
file_path = await message.download_media(file="downloads/photo.jpg")
print(f"ダウンロード完了: {file_path}")
```

### メディア情報の構造

JSON出力の`media`フィールドには以下の情報が含まれます：

```json
{
  "media": {
    "type": "photo",
    "photo_id": 1234567890,
    "message_id": 12345,
    "channel_id": 123456,
    "download_info": {
      "channel_id": 123456,
      "message_id": 12345,
      "note": "Use message.download_media() with this message to download"
    }
  }
}
```

`download_info`の`channel_id`と`message_id`を使用して、メディアをダウンロードできます。

### 複数メディア（写真アルバムなど）の処理

Telegramでは、1つのメッセージに複数の写真が含まれる場合（写真アルバム）、`grouped_id`でグループ化されます。`download_media_example.py`は自動的に複数メディアを検出し、関連するすべてのメッセージをダウンロードします。

```json
{
  "media": {
    "type": "photo",
    "grouped_id": 1234567890,
    "is_grouped": true,
    "download_info": {
      "channel_id": 123456,
      "message_id": 12345,
      "grouped_id": 1234567890,
      "note": "If grouped_id exists, download all related messages."
    }
  }
}
```

### エラー処理

`download_media_example.py`には以下のエラー処理が実装されています：

1. **リトライ処理**: ネットワークエラーやタイムアウト時に最大3回まで自動リトライ（指数バックオフ）
2. **タイムアウト処理**: デフォルトで300秒（5分）のタイムアウト設定
3. **レート制限対応**: Telegramのレート制限（FloodWait）を自動検出して待機
4. **ディスク容量チェック**: ディスク容量不足のエラーを検出して報告
5. **大きなファイルの警告**: 100MB以上のファイルの場合、警告を表示
6. **個別エラー処理**: 1つのメッセージのダウンロードに失敗しても、他のメッセージの処理を継続

### 使用例（エラー処理付き）

```python
from download_media_example import download_media_by_id
import asyncio

# タイムアウトとリトライ回数を指定
asyncio.run(download_media_by_id(
    api_id="your_api_id",
    api_hash="your_api_hash",
    channel_id=-1001234567890,
    message_id=12345,
    output_dir="downloads",
    max_retries=5,  # 最大リトライ回数
    timeout=600     # タイムアウト（秒、10分）
))
```

## License
The source code is licensed MIT. The website content is licensed CC BY 4.0,see LICENSE.