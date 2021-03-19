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


from .models import Room, MatchingCondition

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

        # マッチングタスク
        self.task = None

        # マッチングしたユーザーを格納
        self.match_user_id_list = []

    # WebSocket接続時
    async def connect(self):
        await super().connect()

    # WebSocket切断時
    async def disconnect(self, close_code):
        print('DISCONNECT', close_code)
        if self.task is not None and not self.task.cancelled():
            self.task.cancel()
        await self.matching_unregister()

    # WebSocketからデータ受信時
    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        method = text_data_json.get('method')

        if method == 'start_wait':
            print(f'Got data from {self.user_id}. method: "start_wait"')

            # 既に待ち状態の場合はメッセージを返して終了
            if self.task is not None and not self.task.done():
                await self.send(text_data=json.dumps({'message': 'now waiting...'}))
                return
            
            condition = text_data_json.get('condition')
            submission_time = timezone.now()

            # イベントループでマッチングタスク処理
            loop = asyncio.get_event_loop()
            self.task = loop.create_task(self.matching_task(condition, submission_time))


        elif method == 'quit_wait':
            print(f'Got data from {self.user_id}. method: "quit_wait"')

            # 待ち状態でない場合はメッセージを返して終了
            if self.task is None or self.task.done():
                await self.send(text_data=json.dumps({'message': 'not waiting.'}))
                return

            # タスクキャンセル
            if self.task is not None and not self.task.cancelled():
                self.task.cancel()
                await self.send_info('cancel matching')

            # マッチングの登録解除
            is_registered = await self.matching_unregister()
            if not is_registered:
                await self.send_info('fail to unregister.')
                return
            
            await self.send_info('unregistered!')
        
        elif method == 'force-unregister':
            # マッチングの登録解除
            is_registered = await self.matching_unregister()
            if not is_registered:
                await self.send_info('fail to unregister.')
                return
            
            await self.send_info('unregistered!')

        elif method == 'status':
            print(f'Got data from {self.user_id}. method: "status"')

            data = {
                'message': 'status',
                'task_running': self.task is not None and not self.task.done()
            }
            await self.send(text_data=json.dumps(data))
        
        elif method == 'confirm_matching':
            print(f'Got data from {self.user_id}. method: "confirm_matching"')

            room_id = text_data_json.get('room_id')
            
            if not room_id or not self.group_id == room_id:
                await self.send_info('invalid room id', room_id=room_id)
                return
            
            # マッチングを承認する
            await self.confirm()

            # マッチングしたユーザーらが承認したか
            ok = await self.check_other_confirmations(self.match_user_id_list)
            if not ok:
                await self.send_info('waiting for other confirmations...')
                return
            
            await self.channel_layer.group_send(self.group_id, {
                'type': 'matching.unregister',
            })
            
            # グループの全員にマッチングが完了したことを伝える
            await self.channel_layer.group_send(self.group_id, {
                'type': 'send.message',
                'message': 'matching complete!!'
            })
        
    
    # マッチングタスク
    async def matching_task(self, condition, submission_time):

        # 既にマッチングしているか

        # マッチングに登録
        is_registered = await self.matching_register(condition, submission_time)

        if not is_registered:
            await self.send_info('fail to register.')
            return
        
        await self.send_info('registered!')

        # マッチング待ち
        try:
            room_id = await self.wait_matching_until_complete(condition, submission_time)
        except ObjectDoesNotExist as ex:

            # マッチング解除
            await self.matching_unregister()
            await self.send_info('a error happens while waiting for matching.', error=ex)
            return
        
        # Conditionを保留状態に
        await self.pending()

        # グループに参加
        await self.join_group(str(room_id))

        # roomIDを送信
        await self.send_info('got matched!', room_id=room_id)

    # マッチングに登録
    @database_sync_to_async
    def matching_register(self, condition, submission_time):
        defaults = dict(
            user=User.objects.get(pk=self.user_id),
            game_name=condition['game_name'],
            number=condition['number'],
            submission_time=submission_time,
            is_active=True,
            is_pending=False,
            is_confirmed=False
        )

        condition, created = MatchingCondition.objects.update_or_create(
            user=User.objects.get(pk=self.user_id),
            defaults=defaults,
        )
        condition.save()

        return True

    # マッチングを登録解除
    @database_sync_to_async
    def matching_unregister(self):
        
        condition = MatchingCondition.objects.filter(user=self.user_id, is_active=True).first()
        if condition is None:
            return False
        # is_active is_confirmedを False にする
        condition.is_active = False
        condition.is_pending = False
        condition.is_confirmed = False
        condition.save()
        return True
    
    # マッチングを保留状態にする（承認待ち状態）
    @database_sync_to_async
    def pending(self):
        condition = MatchingCondition.objects.filter(user=self.user_id, is_active=True).first()
        if condition is None:
            return False
        
        condition.is_pending = True
        condition.save()
        return True

    # 終わるまでマッチングを待つ
    async def wait_matching_until_complete(self, condition, submission_time):
        room_id = None

        # マッチングが完了するまでループ
        while True:
            try:
                room_id = await self.matching(condition, submission_time)
            except ObjectDoesNotExist:
                raise
            if room_id:
                break
            await asyncio.sleep(1)

        return room_id

    # マッチング処理
    @database_sync_to_async
    def matching(self, condition, submission_time):
        # 入れるルームが既にあればそれを返す
        room = Room.objects.filter(users=self.user_id, is_active=True, created_date__gte=submission_time).order_by('-created_date').first()

        if room is not None:
            print('room found!')
            self.match_user_id_list = copy.deepcopy([user.pk for user in list(room.users.all())])
            return room.pk

        '''
        マッチングできるかチェック
        '''
        my_room_condition = MatchingCondition.objects.filter(
            user=self.user_id,
            is_active=True,
            is_pending=False,
            is_confirmed=False,
            submission_time=submission_time).first()
        # 有効な自分の RoomCondition がなければエラー
        if my_room_condition is None:
            raise ObjectDoesNotExist('Valid room condition does not exist.')

        # condition に合致する RoomCondition のクエリセットを取得
        match_room_conditions = MatchingCondition.objects.filter(
            game_name=condition['game_name'],
            number=condition['number'],
            is_active=True,
            is_pending=False,
            is_confirmed=False).order_by('submission_time')

        # クエリセットが条件の数より少ない場合は不適
        if match_room_conditions.count() < condition['number']:
            return

        # クエリセットを条件の数に制限
        match_room_conditions = match_room_conditions[:condition['number']]

        # クエリセットと関連した User を取得し、idをリスト match_users_id に格納
        match_users_id = [room_condition.user.pk for room_condition in match_room_conditions]

        # 自分が入っていない場合は不適
        if not self.user_id in match_users_id:
            return
        
        print(match_users_id)

        print('matching ok', self.user_id)


        '''
        ルームを作成
        '''
        # 既に作られているか
        room = Room.objects.filter(users=self.user_id, is_active=True, created_date__gte=submission_time).order_by('-created_date').first()
        if room is None:
            # ない場合はルーム作成
            print(self.user_id, 'create room')
            room = Room.objects.create(is_active=True)
            for user_id in match_users_id:
                room.users.add(User.objects.get(pk=user_id))
        
        self.match_user_id_list = copy.deepcopy(match_users_id)
        
        return room.pk

    # マッチング承認
    @database_sync_to_async
    def confirm(self):
        condition = MatchingCondition.objects.filter(user=self.user_id).first()
        if condition is None:
            return False
        
        condition.is_confirmed = True
        condition.is_pending = False
        condition.save()
        return True

    @database_sync_to_async
    def check_other_confirmations(self, id_list):
        if not id_list:
            return False

        for user_id in id_list:
            try:
                condition = MatchingCondition.objects.filter(user=user_id).first()
            except User.matchingcondition.RelatedObjectDoesNotExist:
                print('User.matchingcondition.RelatedObjectDoesNotExist')
                return False
            except Exception:
                return False
            if not condition.is_confirmed:
                return False
        
        return True

