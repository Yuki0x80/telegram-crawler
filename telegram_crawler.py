from telethon import TelegramClient, events
from telethon.tl import types
from telethon.tl.custom import Message
import configparser
import datetime
import socks
import json
import pprint
import traceback
import asyncio

class TelegramCrawler:
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
        self.telegram_client.add_event_handler(self.new_message_handler, events.NewMessage(incoming=None))

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

    # Waiting new message
    async def new_message_handler(self, event: events.NewMessage.Event):
        try:
            message_logs = {}
            message: Message    = event.message
            sender              = await event.get_sender()
            chennel_info        = await event.get_input_chat()

            # チャンネルかどうかをチェック
            if not hasattr(chennel_info, 'channel_id'):
                # チャンネルでない場合（ユーザーからのメッセージなど）はスキップ
                return

            chennel_id                  = chennel_info.channel_id
            message_logs[chennel_id]    = {}
            
            # チャンネルリストに存在するかチェック
            channel_key = '-100' + str(chennel_id)
            if channel_key not in self.channel_list:
                # チャンネルリストにない場合はスキップ
                return
            
            channel_name                = self.channel_list[channel_key]["channel_name"]
            
            # excpet channel
            for except_list in self.exception_list:
                if except_list in channel_name.replace(" ",""): return

            # message from user
            message_logs[chennel_id]["channel_name"]       =  channel_name  # Channel title
            message_logs[chennel_id]["message_id"]         =  message.id  # Message ID in channel
            message_logs[chennel_id]["message"]            =  message.raw_text  # Plain text content
            message_logs[chennel_id]["message_from_geo"]   =  message.geo  # Geo tag if present
            message_logs[chennel_id]["JST_send_time"]      =  self.utc_to_jts(message.date)  # Timestamp in JST
            message_logs[chennel_id]["display_of_post_author"] =  message.post_author  # Author name shown on post
            
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
                    media_info["channel_id"] = chennel_id
                    media_info["download_info"] = {
                        "channel_id": chennel_id,
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
                    media_info["channel_id"] = chennel_id
                    media_info["download_info"] = {
                        "channel_id": chennel_id,
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
                    media_info["channel_id"] = chennel_id
                    media_info["download_info"] = {
                        "channel_id": chennel_id,
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
                    media_info["channel_id"] = chennel_id
                    media_info["download_info"] = {
                        "channel_id": chennel_id,
                        "message_id": message.id,
                        "grouped_id": grouped_id
                    }
                except Exception as e:
                    media_info["download_error"] = str(e)
                    traceback.print_exc()
            if media_info:
                message_logs[chennel_id]["media"] = media_info
            
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
                    message_logs[chennel_id]["entities"] = entities_info

            # four type of message
            if hasattr(message.from_id, "user_id") == True: 
                message_logs[chennel_id]["from_id"] = {"peerUser": message.from_id.user_id}  # Sender user id

            elif hasattr(message.from_id, "chat_id") == True:
                message_logs[chennel_id]["from_id"] = {"peerChat": message.from_id.chat_id}  # Sender chat id

            elif hasattr(message.from_id, "channel_id") == True:
                message_logs[chennel_id]["from_id"] = {"peerChannel": message.from_id.channel_id}  # Sender channel id

            else: 
                message_logs[chennel_id]["from_id"] = {"anonymous": None}  # Unknown sender type

            # if it wasn't a bot, get user data (sender can be Channel/Chat without bot attr)
            if sender is None:
                # senderがNoneの場合、メッセージ情報から判断
                if hasattr(message, 'via_bot_id') and message.via_bot_id is not None:
                    sender_is_bot = True  # ボット経由のメッセージ
                elif hasattr(message, 'post') and message.post:
                    sender_is_bot = False  # チャンネル投稿（通常はボットではない）
                elif hasattr(message.from_id, "user_id"):
                    # from_idにuser_idがある場合は、そのユーザー情報を取得して確認
                    try:
                        user_entity = await self.telegram_client.get_entity(message.from_id.user_id)
                        sender_is_bot = getattr(user_entity, "bot", False)
                        if not sender_is_bot and isinstance(user_entity, types.User):
                            message_logs[chennel_id]["sender_user"] = {
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
                    message_logs[chennel_id]["sender_user"] = {
                        "user_id": sender.id,  # Sender user id
                        "username": sender.username,  # Sender username
                        "phone": getattr(sender, "phone", None),  # Sender phone number
                        "Firstname": sender.first_name,  # Sender first name
                        "Lastname": sender.last_name,  # Sender last name
                    }
            message_logs[chennel_id]["bot"] = sender_is_bot  # True if sender is bot

            # output:JSON
            self.json_telegram_message_data = json.dumps(message_logs, indent=2, ensure_ascii=False)
            pprint.pprint(self.json_telegram_message_data)
        except Exception as e:
            print(f"エラー: メッセージ処理中にエラーが発生しました: {e}")
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
    
    # reset telegram client session
    async def logout_from_telegram_session(self):
        await self.telegram_client.log_out()

    async def initialize(self):
        """非同期初期化メソッド"""
        await self.telegram_client.start()
        await self.set_own_channel_list()

if __name__ == "__main__":
    async def main():
        abc = TelegramCrawler()
        await abc.initialize()
        await abc.telegram_client.run_until_disconnected()
    
    asyncio.run(main())
