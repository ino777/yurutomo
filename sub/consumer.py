# ChatConsumerクラス: WebSocketからの受け取ったものを処理するクラス
class ChatConsumer(AsyncWebsocketConsumer):

    rooms = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if ChatConsumer.rooms is None:
            ChatConsumer.rooms = {}
        self.group_name = ''
        self.user_name = ''

    # WebSocket接続時
    async def connect(self):
        # WebSocket接続を受け入れる
        await self.accept()

    # WebSocket切断時
    async def disconnect(self, close_code):
        # チャットグループから抜ける
        await self.leave_chat()

    # WebSocketからデータ受信時
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)

        if text_data_json.get('data_type') == 'join':
            self.user_name = text_data_json['username']
            room_name = text_data_json['room']
            await self.join_chat(room_name)

        elif text_data_json.get('data_type') == 'leave':
            await self.leave_chat()

        else:
            message = text_data_json['message']

            # グループ内の全コンシューマーにメッセージを拡散送信
            # 受信関数を'type'で指定
            data = {
                'type': 'chat_message',
                'message': message,
                'username': self.user_name,
                'datetime': datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
            }
            await self.channel_layer.group_send(self.group_name, data)

    # 拡散メッセージ受信時
    async def chat_message(self, data):
        data_json = {
            'message': data['message'],
            'username': data['username'],
            'datetime': data['datetime'],
        }

        await self.send(text_data=json.dumps(data_json))

    # チャットグループに参加
    async def join_chat(self, room_name):
        self.group_name = 'chat_' + room_name

        # グループに参加
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        # 参加者数の更新
        room = ChatConsumer.rooms.get(self.group_name)
        if room is None:
            ChatConsumer.rooms[self.group_name] = {'participants_count': 1}
        else:
            room['participants_count'] += 1

        # グループにシステムメッセージ送信
        system_message = f'{self.user_name} joind. ({ChatConsumer.rooms[self.group_name]["participants_count"]} participants)'
        data = {
            'type': 'chat_message',
            'message': system_message,
            'username': USERNAME_SYSTEM,
            'datetime': datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        }
        await self.channel_layer.group_send(self.group_name, data)

    # チャットグループから退出
    async def leave_chat(self):
        if not self.group_name:
            return

        # グループを離脱
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

        # 参加者数の更新
        ChatConsumer.rooms[self.group_name]['participants_count'] -= 1

        # グループにシステムメッセージ送信
        system_message = f'{self.user_name} left. ({ChatConsumer.rooms[self.group_name]["participants_count"]} participants)'
        data = {
            'type': 'chat_message',
            'message': system_message,
            'username': USERNAME_SYSTEM,
            'datetime': datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        }
        await self.channel_layer.group_send(self.group_name, data)

        # 参加者がゼロのときはルーム削除
        if not ChatConsumer.rooms[self.group_name]['participants_count']:
            del ChatConsumer.rooms[self.group_name]

        self.group_name = ''
