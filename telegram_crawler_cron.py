from telethon import TelegramClient
from telethon.tl import types
from telethon.tl.custom import Message
import configparser
import datetime
import socks
import json
import pprint
import traceback
import os
import asyncio

class TelegramCrawlerCron:
    def __init__(self):
        try:
            config = configparser.ConfigParser()
            if not config.read('config.ini'):
                raise FileNotFoundError("config.ini が見つかりません")
            api_id      = config.get('TELEGRAM', 'api_id')
            api_hash    = config.get('TELEGRAM', 'api_hash')
            proxy       = self.set_proxy(config)
            self.exception_list = config.get('EXCEPT CHANNEL', 'channel')
            self.exception_list = self.exception_list.replace(" ","").split(',')
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            print(f"エラー: config.iniの設定が不正です: {e}")
            raise
        except Exception as e:
            print(f"エラー: 初期化中にエラーが発生しました: {e}")
            raise

        # start telegram client
        self.telegram_client = TelegramClient('CAnonBot', api_id, api_hash, proxy=proxy)
        self.last_run_file = '.last_run'
        self.channel_list = {}
        # JSON出力ファイルの設定（config.iniから読み込み、なければデフォルト値）
        try:
            base_output_file = config.get('OUTPUT', 'output_file')
        except (configparser.NoSectionError, configparser.NoOptionError):
            base_output_file = 'telegram_messages.json'  # デフォルト値
        
        # ファイル名に日時を追加
        self.output_file = self._add_timestamp_to_filename(base_output_file)
        self.all_messages = []  # すべてのメッセージを保存するリスト

    def set_proxy(self, config):
        proxy_type  = config.get('PROXY', 'type')
        proxy_addr  = config.get('PROXY', 'addr')
        proxy_port  = config.get('PROXY', 'port')
        proxy_username = config.get('PROXY', 'username')
        proxy_password = config.get('PROXY', 'password')
        
        # proxy setting & checking
        if proxy_type == "HTTP": proxy_type = socks.HTTP
        elif proxy_type == "SOCKS4": proxy_type = socks.SOCKS4
        elif proxy_type == "SOCKS5": proxy_type = socks.SOCKS5
        else: proxy_type = None

        proxy_addr = proxy_addr if proxy_addr != "" else None
        proxy_port = int(proxy_port) if proxy_port.isdigit() else None
        proxy_username = proxy_username if proxy_username != "" else None
        proxy_password = proxy_password if proxy_password != "" else None

        if proxy_type != None and proxy_addr != None and proxy_port != None \
            and proxy_username != None and proxy_password != None:
            proxy = (proxy_type, proxy_addr, proxy_port, False, proxy_username, proxy_password)
        else: proxy = None

        return proxy

    async def set_own_channel_list(self):
        self.channel_list = {}
        async for dialog in self.telegram_client.iter_dialogs(ignore_pinned=True):
            self.channel_list[str(dialog.id)] = {"channel_name": dialog.name}
            if dialog.entity.username != None: 
                self.channel_list[str(dialog.id)].update({"channel_url": "t.me/" + dialog.entity.username})

    def get_last_run_time(self):
        """前回実行時刻を取得。ファイルが存在しない場合は24時間前を返す"""
        if os.path.exists(self.last_run_file):
            try:
                with open(self.last_run_file, 'r') as f:
                    timestamp_str = f.read().strip()
                    return datetime.datetime.fromisoformat(timestamp_str)
            except:
                # ファイルが壊れている場合は24時間前を返す
                return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
        else:
            # 初回実行時は24時間前を返す
            return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)

    def _add_timestamp_to_filename(self, filepath):
        """ファイル名の先頭に日時を追加"""
        # ディレクトリとファイル名を分離
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        
        # 現在時刻を取得（JST）
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        
        # ファイル名と拡張子を分離
        name, ext = os.path.splitext(filename)
        
        # 日時を先頭に追加したファイル名を作成
        new_filename = f"{timestamp}_{name}{ext}"
        
        # ディレクトリがある場合は結合
        if directory:
            return os.path.join(directory, new_filename)
        else:
            return new_filename
    
    def save_last_run_time(self):
        """現在時刻を前回実行時刻として保存"""
        current_time = datetime.datetime.now(datetime.timezone.utc)
        with open(self.last_run_file, 'w') as f:
            f.write(current_time.isoformat())
    
    def save_messages_to_file(self):
        """すべてのメッセージをJSONファイルに保存"""
        try:
            # ディレクトリが存在しない場合は作成
            output_dir = os.path.dirname(self.output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                print(f"ディレクトリを作成しました: {output_dir}")
            
            # 既存のファイルがある場合は読み込む
            all_data = []
            if os.path.exists(self.output_file):
                try:
                    with open(self.output_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        if isinstance(existing_data, list):
                            all_data = existing_data
                        else:
                            all_data = [existing_data]
                    print(f"既存のファイルを読み込みました: {len(all_data)}件のメッセージ")
                except Exception as e:
                    # ファイルが壊れている場合は空のリストから開始
                    print(f"警告: 既存ファイルの読み込みに失敗しました（新規作成します）: {e}")
                    all_data = []
            
            # 新しいメッセージを追加
            all_data.extend(self.all_messages)
            
            # ファイルに保存（追記ではなく上書き）
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)
            
            print(f"JSONファイルに保存しました: {self.output_file} ({len(self.all_messages)}件のメッセージ、合計: {len(all_data)}件)")
        except Exception as e:
            print(f"エラー: JSONファイルの保存に失敗しました: {e}")
            traceback.print_exc()

    async def process_message(self, message: Message, channel_id: int):
        """メッセージを処理してJSON形式で出力"""
        try:
            message_logs = {}
            sender = await message.get_sender()
            
            message_logs[channel_id] = {}
            # チャンネルIDのキー形式を元のコードに合わせる（-100プレフィックス）
            channel_key = '-100' + str(channel_id) if channel_id > 0 else str(channel_id)
            if channel_key not in self.channel_list:
                # チャンネルリストにない場合はスキップ
                return
            
            channel_name = self.channel_list[channel_key]["channel_name"]
            
            # except channel
            for except_list in self.exception_list:
                if except_list in channel_name.replace(" ",""): 
                    return

            # message from user
            message_logs[channel_id]["channel_name"]       = channel_name
            message_logs[channel_id]["message_id"]         = message.id
            message_logs[channel_id]["message"]            = message.raw_text
            message_logs[channel_id]["message_from_geo"]   = message.geo
            message_logs[channel_id]["JST_send_time"]      = self.utc_to_jts(message.date)
            message_logs[channel_id]["display_of_post_author"] = message.post_author
            
            # Media information (画像、動画、ファイルなど)
            media_info = {}
            # 複数メディア（写真アルバムなど）のチェック
            grouped_id = getattr(message, 'grouped_id', None)
            if grouped_id:
                media_info["grouped_id"] = grouped_id
                media_info["is_grouped"] = True
            
            if message.photo:
                media_info["type"] = "photo"
                media_info["photo_id"] = message.photo.id if hasattr(message.photo, 'id') else None
                # 写真をダウンロードするための情報
                try:
                    media_info["message_id"] = message.id
                    media_info["channel_id"] = channel_id
                    media_info["download_info"] = {
                        "channel_id": channel_id,
                        "message_id": message.id,
                        "grouped_id": grouped_id
                    }
                except Exception as e:
                    media_info["download_error"] = str(e)
                    traceback.print_exc()
            elif message.video:
                media_info["type"] = "video"
                media_info["video_id"] = message.video.id if hasattr(message.video, 'id') else None
                media_info["duration"] = getattr(message.video, 'duration', None)
                try:
                    media_info["message_id"] = message.id
                    media_info["channel_id"] = channel_id
                    media_info["download_info"] = {
                        "channel_id": channel_id,
                        "message_id": message.id,
                        "grouped_id": grouped_id
                    }
                except Exception as e:
                    media_info["download_error"] = str(e)
                    traceback.print_exc()
            elif message.document:
                media_info["type"] = "document"
                media_info["document_id"] = message.document.id if hasattr(message.document, 'id') else None
                media_info["mime_type"] = getattr(message.document, 'mime_type', None)
                media_info["file_name"] = getattr(message.document, 'file_name', None)
                media_info["file_size"] = getattr(message.document, 'size', None)
                try:
                    media_info["message_id"] = message.id
                    media_info["channel_id"] = channel_id
                    media_info["download_info"] = {
                        "channel_id": channel_id,
                        "message_id": message.id,
                        "grouped_id": grouped_id
                    }
                except Exception as e:
                    media_info["download_error"] = str(e)
                    traceback.print_exc()
            elif message.media:
                media_info["type"] = str(type(message.media).__name__)
                try:
                    media_info["message_id"] = message.id
                    media_info["channel_id"] = channel_id
                    media_info["download_info"] = {
                        "channel_id": channel_id,
                        "message_id": message.id,
                        "grouped_id": grouped_id
                    }
                except Exception as e:
                    media_info["download_error"] = str(e)
                    traceback.print_exc()
            if media_info:
                message_logs[channel_id]["media"] = media_info
            
            # Links and entities (リンク、メンションなど)
            if message.entities:
                entities_info = []
                for entity in message.entities:
                    entity_type = type(entity).__name__
                    # 装飾情報（Bold、Emoji）は除外
                    if entity_type in ["MessageEntityBold", "MessageEntityCustomEmoji"]:
                        continue
                    entity_data = {
                        "type": entity_type
                    }
                    # URL情報の取得
                    if hasattr(entity, 'url'):
                        entity_data["url"] = entity.url
                    # テキスト内の位置情報
                    if hasattr(entity, 'offset') and hasattr(entity, 'length'):
                        entity_data["offset"] = entity.offset
                        entity_data["length"] = entity.length
                        # テキストからURLを抽出（MessageEntityUrlの場合）
                        if entity_data["type"] == "MessageEntityUrl":
                            try:
                                url_text = message.raw_text[entity.offset:entity.offset + entity.length]
                                entity_data["url"] = url_text
                            except:
                                pass
                    # ユーザーID（メンションの場合）
                    if hasattr(entity, 'user_id'):
                        entity_data["user_id"] = entity.user_id
                    entities_info.append(entity_data)
                if entities_info:
                    message_logs[channel_id]["entities"] = entities_info

            # four type of message
            if hasattr(message.from_id, "user_id") == True: 
                message_logs[channel_id]["from_id"] = {"peerUser": message.from_id.user_id}

            elif hasattr(message.from_id, "chat_id") == True:
                message_logs[channel_id]["from_id"] = {"peerChat": message.from_id.chat_id}

            elif hasattr(message.from_id, "channel_id") == True:
                message_logs[channel_id]["from_id"] = {"peerChannel": message.from_id.channel_id}

            else: 
                message_logs[channel_id]["from_id"] = {"anonymous": None}

            # if it wasn't a bot, get user data
            if sender is None:
                # senderがNoneの場合、メッセージ情報から判断
                if hasattr(message, 'via_bot_id') and message.via_bot_id is not None:
                    sender_is_bot = True  # ボット経由のメッセージ
                elif hasattr(message, 'post') and message.post:
                    sender_is_bot = False  # チャンネル投稿（通常はボットではない）
                elif hasattr(message.from_id, "user_id"):
                    # from_idにuser_idがある場合は、そのユーザー情報を取得して確認
                    try:
                        # ユーザーIDからユーザーエンティティ（ユーザー情報）を取得
                        user_entity = await self.telegram_client.get_entity(message.from_id.user_id)
                        sender_is_bot = getattr(user_entity, "bot", False)
                        # ユーザーエンティティが存在する場合は、ユーザー情報を取得
                        if not sender_is_bot and isinstance(user_entity, types.User):
                            message_logs[channel_id]["sender_user"] = {
                                "user_id": user_entity.id,
                                "username": user_entity.username,
                                "phone": getattr(user_entity, "phone", None),
                                "Firstname": user_entity.first_name,
                                "Lastname": user_entity.last_name,
                            }
                    except:
                        sender_is_bot = False  # 取得できない場合はFalseとする
                else:
                    sender_is_bot = False  # 判断できない場合はFalseとする
            else:
                sender_is_bot = getattr(sender, "bot", False)
                if not sender_is_bot and isinstance(sender, types.User):
                    message_logs[channel_id]["sender_user"] = {
                        "user_id": sender.id, 
                        "username": sender.username,  
                        "phone": getattr(sender, "phone", None), 
                        "Firstname": sender.first_name, 
                        "Lastname": sender.last_name
                    }
            message_logs[channel_id]["bot"] = sender_is_bot  # True if sender is bot

            # output:JSON
            json_telegram_message_data = json.dumps(message_logs, indent=2, ensure_ascii=False)
            # pprint.pprint(json_telegram_message_data)  # ファイルに保存するため、コンソール出力は不要
            
            # メッセージをリストに追加（後でファイルに保存）
            self.all_messages.append(message_logs)
        except Exception as e:
            print(f"エラー: メッセージ処理中にエラーが発生しました (message_id: {message.id if hasattr(message, 'id') else 'unknown'}): {e}")
            traceback.print_exc()
            return
    
    def utc_to_jts(self, date_time):
        try:
            date_time = date_time.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
            date_time = date_time.strftime("%Y/%m/%d %H:%M:%S")
            return date_time
        except:
            traceback.print_exc()
            return None

    async def run(self):
        """都度実行：前回実行時刻以降のメッセージを取得して処理"""
        await self.telegram_client.start()
        
        # チャンネルリストを取得
        print("チャンネルリストを取得中...")
        await self.set_own_channel_list()
        print(f"チャンネル数: {len(self.channel_list)}件")
        
        last_run_time = self.get_last_run_time()
        print(f"前回実行時刻: {last_run_time}")
        
        # 全ダイアログから新しいメッセージを取得
        processed_count = 0
        channel_count = 0
        skipped_count = 0
        dialog_count = 0
        # 全ダイアログから新しいメッセージを取得
        async for dialog in self.telegram_client.iter_dialogs(ignore_pinned=True):
            dialog_count += 1
            if dialog_count % 10 == 0:
                print(f"処理中... ダイアログ {dialog_count}件目を確認中")
            try:
                # チャンネルIDを取得（元のコードの形式に合わせる）
                # InputChannelを取得してchannel_idを抽出
                try:
                    input_chat = await self.telegram_client.get_input_entity(dialog.entity)
                    if hasattr(input_chat, 'channel_id'):
                        channel_id = input_chat.channel_id
                    else:
                        # チャンネルでない場合はスキップ
                        continue
                except:
                    # チャンネルでない場合はスキップ
                    continue
                
                channel_count += 1
                print(f"チャンネル処理中: {dialog.name} ({channel_count}件目)")
                message_count_in_channel = 0
                checked_messages = 0
                # 前回実行時刻以降のメッセージを取得
                # offset_dateは「この日時以降」のメッセージを取得するが、reverse=Falseの場合は古い順
                # そのため、最新のメッセージから取得するためにreverse=Trueを使用
                async for message in self.telegram_client.iter_messages(
                    dialog.entity, 
                    offset_date=last_run_time,
                    reverse=True,  # 新しい順に取得（最新のメッセージから）
                    limit=100  # 1チャンネルあたり最大100件まで取得（パフォーマンス向上）
                ):
                    checked_messages += 1
                    # メッセージが前回実行時刻より後であることを確認
                    # タイムゾーンを統一して比較
                    message_date_utc = message.date
                    if message_date_utc.tzinfo is None:
                        message_date_utc = message_date_utc.replace(tzinfo=datetime.timezone.utc)
                    
                    if message_date_utc > last_run_time:
                        await self.process_message(message, channel_id)
                        processed_count += 1
                        message_count_in_channel += 1
                    else:
                        # 前回実行時刻以前のメッセージに到達したら終了（新しい順に取得しているので）
                        break
                
                if checked_messages > 0 and message_count_in_channel == 0:
                    # デバッグ情報を追加
                    print(f"  → メッセージを{checked_messages}件確認しましたが、すべて前回実行時刻（{last_run_time}）以前でした")
                    # 最新のメッセージの日時を表示（デバッグ用）
                    try:
                        latest_msg = await self.telegram_client.get_messages(dialog.entity, limit=1)
                        if latest_msg and len(latest_msg) > 0:
                            latest_date = latest_msg[0].date
                            if latest_date.tzinfo is None:
                                latest_date = latest_date.replace(tzinfo=datetime.timezone.utc)
                            print(f"  → 最新メッセージの日時: {latest_date} (前回実行時刻: {last_run_time})")
                    except:
                        pass
                
                if message_count_in_channel == 0:
                    skipped_count += 1
                else:
                    print(f"  → {message_count_in_channel}件のメッセージを処理しました")
            except Exception as e:
                print(f"エラー: チャンネル {dialog.name} の処理中にエラーが発生しました: {e}")
                traceback.print_exc()
                continue
        
        print(f"\n処理完了: {processed_count}件のメッセージを処理しました")
        print(f"  総ダイアログ数: {dialog_count}件")
        print(f"  チャンネル数: {channel_count}件, 新規メッセージなし: {skipped_count}件")
        print(f"  保存待ちメッセージ数: {len(self.all_messages)}件")
        
        # JSONファイルに保存
        if self.all_messages:
            print(f"\nJSONファイルに保存中: {self.output_file}")
            self.save_messages_to_file()
        else:
            print(f"\n保存するメッセージがありません（output_file: {self.output_file}）")
        
        # 実行時刻を保存
        self.save_last_run_time()
        
        # クライアントを切断
        await self.telegram_client.disconnect()
    
    # reset telegram client session
    def logout_from_telegram_session(self):
        asyncio.run(self.telegram_client.log_out())

if __name__ == "__main__":
    crawler = TelegramCrawlerCron()
    asyncio.run(crawler.run())
