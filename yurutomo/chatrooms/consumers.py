import json
import uuid
import copy
import datetime
import asyncio
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


from .models import Room, MatchingRecord

# from asgiref.sync import async_to_sync  # async_to_sync() : 非同期関数を同期的に実行する際に使用する


User = get_user_model()

USERNAME_SYSTEM = '*system*'

class UserConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = ''
        self.group_id = ''

    
    async def connect(self):
        self.user_id = self.scope['user'].pk
        await self.accept()
    
    async def disconnect(self, code):
        pass

    # グループに参加
    async def join_group(self, group_id):
        self.group_id = group_id

        await self.channel_layer.group_add(self.group_id, self.channel_name)

    # グループを離脱
    async def leave_group(self):
        await self.channel_layer.group_discard(self.group_id, self.channel_name)
        self.group_id = ''
    
    # タイムスタンプ付きメッセージ送信
    async def send_info(self, message, **kwargs):
        data = {
            'message': message,
            'datetime': '{:%d-%m-%Y:%H:%M:%S}.{:06d}'.format(timezone.localtime(timezone.now()), timezone.now().microsecond),
        }

        for k, v in kwargs.items():
            kwargs[k] = str(v)
        data.update(kwargs)
        await self.send(text_data=json.dumps(data))

    # メッセージ送信
    async def send_message(self, data):
        data_json = {
            'message': data['message'],
            'datetime': '{:%d-%m-%Y:%H:%M:%S}.{:06d}'.format(timezone.localtime(timezone.now()), timezone.now().microsecond),
        }
        await self.send(text_data=json.dumps(data_json))

    
class MatchingConsumer(UserConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # WebSocket接続時
    async def connect(self):
        await super().connect()
        await self.join_group(self.user_id)

    # WebSocket切断時
    async def disconnect(self, close_code):
        print('DISCONNECT', close_code)

    # WebSocketからデータ受信時
    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        method = text_data_json.get('method')

        if method == 'start_wait':
            print(f'Got data from {self.user_id}. method: "start_wait"')
            
            condition = text_data_json.get('condition')
            submission_time = timezone.now()

            # マッチング登録
            is_registered = await self.register_matching(condition, submission_time)
            if not is_registered:
                await self.send_info('fail to register')
                return
            
            await self.send_info('registered!')


        elif method == 'quit_wait':
            print(f'Got data from {self.user_id}. method: "quit_wait"')

            # マッチングの登録解除
            is_unregistered = await self.unregister_matching()
            if not is_registered:
                await self.send_info('fail to unregister.')
                return
            
            await self.send_info('unregistered!')
        
        elif method == 'get_room':
            print(f'Got data from {self.user_id}. method: "get_room"')

            try:
                room_id = await self.get_match_room()
            except ObjectDoesNotExist as e:
                print(e)
                await self.send_info('error', error=e)
                return
            
            print(room_id)
            if room_id is None:
                await self.send_info('now waiting...')
                return
            
            # 保留状態にする
            await self.pending()
            
            await self.join_group(str(room_id))
            data = {
                'room_id': str(room_id),
                'message': 'got matched!'
            }
            await self.send(text_data=json.dumps(data))

        elif method == 'status':
            print(f'Got data from {self.user_id}. method: "status"')

            data = {
                'message': 'status',
            }
            await self.send(text_data=json.dumps(data))
        
        elif method == 'confirm_matching':
            print(f'Got data from {self.user_id}. method: "confirm_matching"')

            room_id = text_data_json.get('room_id')

            # room_id のバリデーション
            if not await self.room_exists(room_id):
                await self.send_info('invalid room id')
                return
            
            # マッチングを承認する
            await self.confirm()

            # マッチングしたユーザーらが承認したか
            ok = await self.check_other_confirmations(room_id)
            if not ok:
                await self.send_info('waiting for other confirmations...')
                return
            
            # グループの全員にマッチングが完了したことを伝える
            await self.channel_layer.group_send(self.group_id, {
                'type': 'send.message',
                'message': 'matching complete'
            })
        
    

    # マッチングに登録
    @database_sync_to_async
    def register_matching(self, condition, submission_time):
        defaults = dict(
            user=User.objects.get(pk=self.user_id),
            game_name=condition['game_name'],
            number=condition['number'],
            submission_time=submission_time,
            is_active=True,
            is_pending=False,
            is_confirmed=False
        )

        record, created = MatchingRecord.objects.update_or_create(
            user=User.objects.get(pk=self.user_id),
            defaults=defaults,
        )
        record.save()

        return True

    # マッチングを登録解除
    @database_sync_to_async
    def unregister_matching(self):
        
        record = MatchingRecord.objects.filter(user=self.user_id, is_active=True).first()
        if record is None:
            return False
        # is_active is_confirmedを False にする
        record.is_active = False
        record.is_pending = False
        record.is_confirmed = False
        record.save()
        return True
    
    # マッチングを保留状態にする（承認待ち状態）
    @database_sync_to_async
    def pending(self):
        record = MatchingRecord.objects.filter(user=self.user_id, is_active=True).first()
        if record is None:
            return False
        
        record.is_pending = True
        record.save()
        return True

    # マッチング処理
    @database_sync_to_async
    def get_match_room(self):
        myrecord = MatchingRecord.objects.filter(
            user=self.user_id,
            is_active=True,
            is_pending=False,
            is_confirmed=False).first()
        if myrecord is None:
            raise ObjectDoesNotExist('Not registered.')

        # 入れるルームが既にあればそれを返す
        room = Room.objects.filter(
            users=self.user_id,
            is_active=True,
            created_date__gte=myrecord.submission_time).order_by('-created_date').first()
        if room is not None:
            return room.pk

        '''
        マッチングできるかチェック
        '''
        # マッチングするものがあるか検索
        match_records = MatchingRecord.objects.filter(
            game_name=myrecord.game_name,
            number=myrecord.number,
            is_active=True,
            is_pending=False,
            is_confirmed=False).order_by('submission_time')

        # クエリセットが条件の数より少ない場合は不適
        if match_records.count() < myrecord.number:
            return

        # クエリセットを条件の数に制限
        match_records = match_records[:myrecord.number]

        # クエリセットと関連した User を取得し、idをリスト match_users_id に格納
        match_users_id = [record.user.pk for record in match_records]

        # 自分が入っていない場合は不適
        if not self.user_id in match_users_id:
            return
        
        print(match_users_id)

        print('matching ok', self.user_id)


        '''
        ルームを作成
        '''
        # 既に作られているか
        room = Room.objects.filter(
            users=self.user_id,
            is_active=True,
            created_date__gte=myrecord.submission_time).order_by('-created_date').first()
        if room is None:
            # ない場合はルーム作成
            print(self.user_id, 'create room')
            room = Room.objects.create(is_active=True)
            for user_id in match_users_id:
                room.users.add(User.objects.get(pk=user_id))
        
        return room.pk
    
    # ルームが存在するか
    @database_sync_to_async
    def room_exists(self, room_id):
        if not room_id:
            return False
        
        room = Room.objects.filter(pk=room_id, users=self.user_id).first()
        
        return room is not None

    # マッチング承認
    @database_sync_to_async
    def confirm(self):
        record = MatchingRecord.objects.filter(user=self.user_id).first()
        if record is None:
            return False
        
        record.is_confirmed = True
        record.is_pending = False
        record.save()
        return True

    # 他のユーザーが全員承認しているか
    @database_sync_to_async
    def check_other_confirmations(self, room_id):
        room = Room.objects.get(pk=room_id)
        users = room.users.all()

        for user in users:
            try:
                record = MatchingRecord.objects.filter(user=user.pk).first()
            except User.matchingrecord.RelatedObjectDoesNotExist:
                print('User.matchingrecord.RelatedObjectDoesNotExist')
                return False
            except Exception:
                return False
            if not record.is_confirmed:
                return False
        
        return True

