"""
メディアファイル（写真、動画、ファイル）をダウンロードする例

取得したメッセージIDとチャンネルIDを使って、メディアをダウンロードする方法を示します。
"""

from telethon import TelegramClient
import configparser
import socks
import asyncio
import os

async def download_media_by_id(api_id, api_hash, channel_id, message_id, output_dir="downloads", max_retries=3, timeout=300):
    """
    メッセージIDとチャンネルIDからメディアをダウンロード
    
    Args:
        api_id: Telegram API ID
        api_hash: Telegram API Hash
        channel_id: チャンネルID（例: -1001234567890）
        message_id: メッセージID
        output_dir: ダウンロード先のディレクトリ
        max_retries: 最大リトライ回数（デフォルト: 3）
        timeout: タイムアウト（秒、デフォルト: 300秒=5分）
    """
    # TelegramClientを初期化
    client = TelegramClient('CAnonBot', api_id, api_hash)
    await client.start()
    
    try:
        # チャンネルエンティティを取得
        channel = await client.get_entity(channel_id)
        
        # メッセージを取得
        message = await client.get_messages(channel, ids=message_id)
        
        if not message:
            print(f"メッセージID {message_id} が見つかりません")
            return None
        
        if not message.media:
            print("メッセージにメディアが含まれていません")
            return None
        
        # ダウンロード先ディレクトリを作成
        os.makedirs(output_dir, exist_ok=True)
        
        # 複数メディア（写真アルバムなど）のチェック
        grouped_id = getattr(message, 'grouped_id', None)
        if grouped_id:
            print(f"複数メディア検出 (grouped_id: {grouped_id})。関連メッセージを取得します...")
            # 同じgrouped_idを持つメッセージを取得
            # より確実な方法：メッセージの範囲を広く取得してフィルタリング
            grouped_messages = [message]  # 最初のメッセージを含める
            
            # 前後のメッセージを取得（範囲を広めに設定）
            # まず前方向に検索（最大50件まで）
            for offset in range(1, 51):
                try:
                    prev_msg = await client.get_messages(channel, ids=message_id - offset)
                    if not prev_msg:
                        break
                    prev_grouped_id = getattr(prev_msg, 'grouped_id', None)
                    if prev_grouped_id == grouped_id:
                        grouped_messages.insert(0, prev_msg)
                    elif prev_grouped_id is not None:
                        # 別のgrouped_idが見つかった場合は終了
                        break
                except Exception as e:
                    # メッセージが存在しない場合は終了
                    break
            
            # 後ろ方向に検索（最大50件まで）
            for offset in range(1, 51):
                try:
                    next_msg = await client.get_messages(channel, ids=message_id + offset)
                    if not next_msg:
                        break
                    next_grouped_id = getattr(next_msg, 'grouped_id', None)
                    if next_grouped_id == grouped_id:
                        grouped_messages.append(next_msg)
                    elif next_grouped_id is not None:
                        # 別のgrouped_idが見つかった場合は終了
                        break
                except Exception as e:
                    # メッセージが存在しない場合は終了
                    break
            
            # メッセージIDでソート（時系列順）
            grouped_messages.sort(key=lambda m: m.id)
            
            if grouped_messages:
                print(f"{len(grouped_messages)}件のメッセージをダウンロードします")
                downloaded_files = []
                
                for idx, msg in enumerate(grouped_messages, 1):
                    if msg.media:
                        try:
                            # リトライ処理付きでダウンロード
                            file_path = await download_with_retry(
                                client, msg, output_dir, max_retries, timeout, idx, len(grouped_messages)
                            )
                            if file_path:
                                downloaded_files.append(file_path)
                        except Exception as e:
                            print(f"エラー: メッセージ {msg.id} のダウンロードに失敗しました: {e}")
                            continue
                
                print(f"ダウンロード完了: {len(downloaded_files)}/{len(grouped_messages)}件")
                return downloaded_files
            else:
                print("関連メッセージが見つかりませんでした。単一メッセージとしてダウンロードします。")
        
        # 単一メッセージのダウンロード
        file_path = await download_with_retry(
            client, message, output_dir, max_retries, timeout, 1, 1
        )
        if file_path:
            print(f"ダウンロード完了: {file_path}")
        return file_path
            
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        await client.disconnect()

async def download_with_retry(client, message, output_dir, max_retries, timeout, current=1, total=1):
    """
    リトライ処理付きでメディアをダウンロード
    
    Args:
        client: TelegramClient
        message: メッセージオブジェクト
        output_dir: ダウンロード先ディレクトリ
        max_retries: 最大リトライ回数
        timeout: タイムアウト（秒）
        current: 現在のメッセージ番号
        total: 総メッセージ数
    """
    import asyncio
    from telethon.errors import FloodWaitError, TimeoutError as TelethonTimeoutError
    
    for attempt in range(1, max_retries + 1):
        try:
            # ファイルサイズをチェック（可能な場合）
            file_size = None
            if hasattr(message, 'document') and message.document:
                file_size = getattr(message.document, 'size', None)
                if file_size:
                    size_mb = file_size / (1024 * 1024)
                    print(f"[{current}/{total}] ダウンロード中... (サイズ: {size_mb:.2f} MB)")
                    if size_mb > 100:  # 100MB以上の場合
                        print(f"警告: 大きなファイルです ({size_mb:.2f} MB)。時間がかかる場合があります。")
            
            # タイムアウト付きでダウンロード
            file_path = await asyncio.wait_for(
                message.download_media(file=output_dir),
                timeout=timeout
            )
            return file_path
            
        except FloodWaitError as e:
            wait_time = e.seconds
            print(f"レート制限: {wait_time}秒待機します...")
            await asyncio.sleep(wait_time)
            continue
            
        except TelethonTimeoutError:
            print(f"タイムアウト: {attempt}/{max_retries}回目の試行がタイムアウトしました")
            if attempt < max_retries:
                print("リトライします...")
                await asyncio.sleep(2 ** attempt)  # 指数バックオフ
                continue
            else:
                raise
                
        except asyncio.TimeoutError:
            print(f"タイムアウト: {attempt}/{max_retries}回目の試行がタイムアウトしました")
            if attempt < max_retries:
                print("リトライします...")
                await asyncio.sleep(2 ** attempt)
                continue
            else:
                raise
                
        except OSError as e:
            if "No space left" in str(e) or "ディスク容量" in str(e):
                print(f"エラー: ディスク容量が不足しています: {e}")
                raise
            else:
                print(f"OSエラー: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise
                    
        except Exception as e:
            print(f"エラー: {e}")
            if attempt < max_retries:
                print(f"リトライします... ({attempt}/{max_retries})")
                await asyncio.sleep(2 ** attempt)
                continue
            else:
                raise
    
    return None

async def download_media_from_json(json_data, api_id, api_hash, output_dir="downloads", max_retries=3, timeout=300):
    """
    JSONデータからメディア情報を抽出してダウンロード
    
    Args:
        json_data: メッセージのJSONデータ（telegram_crawler.pyの出力形式）
        api_id: Telegram API ID
        api_hash: Telegram API Hash
        output_dir: ダウンロード先のディレクトリ
        max_retries: 最大リトライ回数（デフォルト: 3）
        timeout: タイムアウト（秒、デフォルト: 300秒=5分）
    """
    import json
    
    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data
    
    client = TelegramClient('CAnonBot', api_id, api_hash)
    await client.start()
    
    downloaded_count = 0
    error_count = 0
    
    try:
        for channel_id, message_info in data.items():
            try:
                if "media" in message_info and "download_info" in message_info["media"]:
                    download_info = message_info["media"]["download_info"]
                    channel_id_int = download_info["channel_id"]
                    message_id = download_info["message_id"]
                    grouped_id = download_info.get("grouped_id")
                    
                    print(f"\nダウンロード中: チャンネルID={channel_id_int}, メッセージID={message_id}")
                    if grouped_id:
                        print(f"  複数メディア (grouped_id: {grouped_id})")
                    
                    # チャンネルIDを適切な形式に変換（-100プレフィックスを追加）
                    if channel_id_int > 0:
                        channel_entity_id = -1000000000000 - channel_id_int
                    else:
                        channel_entity_id = channel_id_int
                    
                    # チャンネルエンティティを取得
                    try:
                        channel = await client.get_entity(channel_entity_id)
                    except Exception as e:
                        print(f"  エラー: チャンネルを取得できませんでした: {e}")
                        error_count += 1
                        continue
                    
                    # メッセージを取得
                    try:
                        message = await client.get_messages(channel, ids=message_id)
                    except Exception as e:
                        print(f"  エラー: メッセージを取得できませんでした: {e}")
                        error_count += 1
                        continue
                    
                    if not message:
                        print(f"  警告: メッセージID {message_id} が見つかりません")
                        error_count += 1
                        continue
                    
                    if not message.media:
                        print(f"  警告: メッセージにメディアが含まれていません")
                        continue
                    
                    # ダウンロード先ディレクトリを作成
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # 複数メディアの処理
                    if grouped_id:
                        # 同じgrouped_idを持つメッセージを取得
                        grouped_messages = [message]  # 最初のメッセージを含める
                        
                        # 前方向に検索（最大50件まで）
                        for offset in range(1, 51):
                            try:
                                prev_msg = await client.get_messages(channel, ids=message_id - offset)
                                if not prev_msg:
                                    break
                                prev_grouped_id = getattr(prev_msg, 'grouped_id', None)
                                if prev_grouped_id == grouped_id:
                                    grouped_messages.insert(0, prev_msg)
                                elif prev_grouped_id is not None:
                                    # 別のgrouped_idが見つかった場合は終了
                                    break
                            except Exception as e:
                                # メッセージが存在しない場合は終了
                                break
                        
                        # 後ろ方向に検索（最大50件まで）
                        for offset in range(1, 51):
                            try:
                                next_msg = await client.get_messages(channel, ids=message_id + offset)
                                if not next_msg:
                                    break
                                next_grouped_id = getattr(next_msg, 'grouped_id', None)
                                if next_grouped_id == grouped_id:
                                    grouped_messages.append(next_msg)
                                elif next_grouped_id is not None:
                                    # 別のgrouped_idが見つかった場合は終了
                                    break
                            except Exception as e:
                                # メッセージが存在しない場合は終了
                                break
                        
                        # メッセージIDでソート（時系列順）
                        grouped_messages.sort(key=lambda m: m.id)
                        
                        if grouped_messages:
                            print(f"  {len(grouped_messages)}件のメッセージをダウンロードします")
                            for idx, msg in enumerate(grouped_messages, 1):
                                if msg.media:
                                    try:
                                        file_path = await download_with_retry(
                                            client, msg, output_dir, max_retries, timeout, idx, len(grouped_messages)
                                        )
                                        if file_path:
                                            downloaded_count += 1
                                    except Exception as e:
                                        print(f"  エラー: メッセージ {msg.id} のダウンロードに失敗: {e}")
                                        error_count += 1
                        else:
                            # グループ化されたメッセージが見つからない場合は単一として処理
                            file_path = await download_with_retry(
                                client, message, output_dir, max_retries, timeout, 1, 1
                            )
                            if file_path:
                                downloaded_count += 1
                    else:
                        # 単一メッセージのダウンロード
                        file_path = await download_with_retry(
                            client, message, output_dir, max_retries, timeout, 1, 1
                        )
                        if file_path:
                            downloaded_count += 1
                            
            except Exception as e:
                print(f"エラー: チャンネルID {channel_id} の処理中にエラーが発生しました: {e}")
                import traceback
                traceback.print_exc()
                error_count += 1
                continue
        
        print(f"\nダウンロード完了: 成功 {downloaded_count}件, エラー {error_count}件")
                    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    # 設定ファイルから読み込み
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_id = config.get('TELEGRAM', 'api_id')
    api_hash = config.get('TELEGRAM', 'api_hash')
    
    # 使用例1: メッセージIDとチャンネルIDを直接指定
    # asyncio.run(download_media_by_id(
    #     api_id=api_id,
    #     api_hash=api_hash,
    #     channel_id=-1001234567890,  # チャンネルID
    #     message_id=12345,  # メッセージID
    #     output_dir="downloads"
    # ))
    
    # 使用例2: JSONデータからダウンロード
    # json_data = '{"123456": {"media": {"download_info": {"channel_id": 123456, "message_id": 12345}}}}'
    # asyncio.run(download_media_from_json(
    #     json_data=json_data,
    #     api_id=api_id,
    #     api_hash=api_hash,
    #     output_dir="downloads"
    # ))
    
    print("使用例をコメントアウトして実行してください")
