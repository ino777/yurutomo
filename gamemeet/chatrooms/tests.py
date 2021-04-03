import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client

from .models import Room, MatchingRecord

User = get_user_model()


# マッチング登録のテスト
class MatchingRegisterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'testuser', 'test@gmail.com', 'password')

    # ログインしていない場合
    def test_not_logged_in(self):
        post_data = {
            'condition': {
                'game_name': 'Test game',
                'number': 3
            }
        }
        response = self.client.post(reverse(
            'chatrooms:register_matching'), data=post_data, content_type='application/json')
        self.assertRedirects(
            response,
            reverse('login') + '?next=' +
            reverse('chatrooms:register_matching')
        )

    # condition が空の場合
    def test_no_condition(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('chatrooms:register_matching'), data=json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    # 既に登録済みの場合
    def test_already_registered(self):
        game_name = 'Test game'
        number = 3
        record = MatchingRecord.objects.create(user=self.user, game_name=game_name, number=number, is_active=True)
        record.save()

        self.client.force_login(self.user)
        post_data = {
            'condition': {
                'game_name': game_name,
                'number': number
            }
        }
        response = self.client.post(reverse('chatrooms:register_matching'), data=json.dumps(post_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_registered'])

    # 正常に登録できる場合
    def test_logged_in(self):
        self.client.force_login(self.user)

        post_data = {
            'condition': {
                'game_name': 'Test game',
                'number': 3
            }
        }
        response = self.client.post(reverse('chatrooms:register_matching'), data=json.dumps(post_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_registered'])

        # 適切にレコードが更新されているか検証
        records = MatchingRecord.objects.filter(user=self.user.pk)
        self.assertEqual(len(records), 1)
        record = records.first()
        self.assertTrue(record.is_active)
        self.assertFalse(record.is_pending)
        self.assertFalse(record.is_confirmed)

# マッチング登録解除のテスト
class MatchingUnregisterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'testuser', 'test@gmail.com', 'password')

    # ログインしていない場合
    def test_not_logged_in(self):
        response = self.client.post(reverse('chatrooms:unregister_matching'))
        self.assertRedirects(
            response,
            reverse('login') + '?next=' + reverse('chatrooms:unregister_matching')
        )

    # マッチング登録をしていない場合
    def test_not_registered(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('chatrooms:unregister_matching'), data=json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_unregistered'])
    
    # マッチング登録をしている場合
    def test_registered(self):
        game_name = 'Test game'
        number = 3
        record = MatchingRecord.objects.create(user=self.user, game_name=game_name, number=number, is_active=True)

        self.client.force_login(self.user)
        response = self.client.post(reverse('chatrooms:unregister_matching'), data=json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_unregistered'])

        # 適切にレコードが更新されているか検証
        records = MatchingRecord.objects.filter(user=self.user.pk)
        self.assertEqual(len(records), 1)
        record = records.first()
        self.assertFalse(record.is_active)
        self.assertFalse(record.is_pending)
        self.assertFalse(record.is_confirmed)

# マッチング待ちのテスト
class GetMatchRoomTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'testuser', 'test@gmail.com', 'password')
    
    # ログインしていない場合
    def test_not_logged_in(self):
        response = self.client.get(reverse('chatrooms:get_match_room'))
        self.assertRedirects(
            response,
            reverse('login') + '?next=' + reverse('chatrooms:get_match_room')
        )
    
    # マッチング前にRoomがあった場合
    def test_room_exists_before_match(self):
        # マッチング登録前ににRoomが作られる
        room = Room.objects.create(is_active=True)
        room.users.add(self.user)
        room.save()

        self.client.force_login(self.user)
        post_data = {
            'condition': {
                'game_name': 'Test game',
                'number': 1
            }
        }
        self.client.post(reverse('chatrooms:register_matching'), data=json.dumps(post_data), content_type='application/json')
        response = self.client.get(reverse('chatrooms:get_match_room'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_matched'])
        self.assertNotEqual(response.json()['room_id'], str(room.pk))

    # マッチング待ち中にRoomが作成された場合
    def test_room_created_while_matching(self):
        self.client.force_login(self.user)
        post_data = {
            'condition': {
                'game_name': 'Test game',
                'number': 1
            }
        }
        self.client.post(reverse('chatrooms:register_matching'), data=json.dumps(post_data), content_type='application/json')
        # マッチング登録後にRoomが作られる
        room = Room.objects.create(is_active=True)
        room.users.add(self.user)
        room.save()
        response = self.client.get(reverse('chatrooms:get_match_room'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_matched'])
        self.assertEqual(response.json()['room_id'], str(room.pk))
    
    # マッチングしない場合
    def test_not_matched(self):
        self.client.force_login(self.user)
        post_data = {
            'condition': {
                'game_name': 'Test game',
                'number': 2
            }
        }
        self.client.post(reverse('chatrooms:register_matching'), data=json.dumps(post_data), content_type='application/json')
        response = self.client.get(reverse('chatrooms:get_match_room'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_matched'])

    
    # 2人のユーザーでマッチングした場合
    def test_two_users(self):
        c1 = Client()
        c1.force_login(self.user)
        c2 = Client()
        c2.force_login(User.objects.create_user('testuser2', 'test2@gmail.com', 'password2'))

        post_data = {
            'condition': {
                'game_name': 'Test game',
                'number': 2
            }
        }
        c1.post(reverse('chatrooms:register_matching'), data=json.dumps(post_data), content_type='application/json')
        c2.post(reverse('chatrooms:register_matching'), data=json.dumps(post_data), content_type='application/json')
        response1 = c1.get(reverse('chatrooms:get_match_room'))
        response2 = c2.get(reverse('chatrooms:get_match_room'))

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertTrue(response1.json()['is_matched'])
        self.assertTrue(response2.json()['is_matched'])
        self.assertEqual(response1.json()['room_id'], response2.json()['room_id'])
    
    # 3人以上でマッチングした場合
    def test_many_users(self):
        user_counts = 5
        clients = []
        for i in range(user_counts):
            c = Client()
            c.force_login(User.objects.create_user(f'testuser{i}', f'test{i}@gmail.com', f'password{i}'))
            clients.append(c)
        
        post_data = {
            'condition': {
                'game_name': 'Test game',
                'number': user_counts
            }
        }
        responses = []
        for c in clients:
            c.post(reverse('chatrooms:register_matching'), data=json.dumps(post_data), content_type='application/json')
        for c in clients:
            response = c.get(reverse('chatrooms:get_match_room'))
            responses.append(response)
        
        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['is_matched'])
            self.assertEqual(response.json()['room_id'], responses[0].json()['room_id'])

# マッチング承認のテスト
class MatchingConfirmTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'testuser', 'test@gmail.com', 'password')
    
    # ログインしていない場合
    def test_not_logged_in(self):
        response = self.client.post(reverse('chatrooms:confirm_matching'), data=json.dumps({}), content_type='application/json')
        self.assertRedirects(
            response,
            reverse('login') + '?next=' + reverse('chatrooms:confirm_matching')
        )

    # 有効なレコードがなかった場合
    def test_invalid_record(self):
        self.client.force_login(self.user)
        MatchingRecord.objects.create(
            user=self.user,
            game_name='Test game',
            number=3,
            is_active=True,
            is_pending=False)
        response = self.client.post(reverse('chatrooms:confirm_matching'), data=json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_confirmed'])

    # 有効なレコードがあった場合
    def test_valid_record(self):
        self.client.force_login(self.user)
        MatchingRecord.objects.create(
            user=self.user,
            game_name='Test game',
            number=3,
            is_active=True,
            is_pending=True)
        response = self.client.post(reverse('chatrooms:confirm_matching'), data=json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_confirmed'])

        # 適切にレコードが更新されているか検証
        records = MatchingRecord.objects.filter(user=self.user.pk)
        self.assertEqual(len(records), 1)
        record = records.first()
        self.assertTrue(record.is_active)
        self.assertFalse(record.is_pending)
        self.assertTrue(record.is_confirmed)

# マッチング承認キャンセルのテスト
class CancelConfirmTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'testuser', 'test@gmail.com', 'password')
    
    # ログインしていない場合
    def test_not_logged_in(self):
        response = self.client.post(reverse('chatrooms:cancel_confirm'), data=json.dumps({}), content_type='application/json')
        self.assertRedirects(
            response,
            reverse('login') + '?next=' + reverse('chatrooms:cancel_confirm')
        )
    
    # 承認されていない場合
    def test_not_confirmed(self):
        self.client.force_login(self.user)
        MatchingRecord.objects.create(
            user=self.user,
            game_name='Test game',
            number=3,
            is_active=True,
            is_confirmed=False)
        response = self.client.post(reverse('chatrooms:cancel_confirm'), data=json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_cancelled'])
    
    # 承認されている場合
    def test_confirmed(self):
        self.client.force_login(self.user)
        MatchingRecord.objects.create(
            user=self.user,
            game_name='Test game',
            number=3,
            is_active=True,
            is_pending=False,
            is_confirmed=True)
        response = self.client.post(reverse('chatrooms:cancel_confirm'), data=json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_cancelled'])

        # 適切にレコードが更新されているか検証
        records = MatchingRecord.objects.filter(user=self.user.pk)
        self.assertEqual(len(records), 1)
        record = records.first()
        self.assertTrue(record.is_active)
        self.assertFalse(record.is_pending)
        self.assertFalse(record.is_confirmed)

# マッチング完了のテスト
class MatchingCompleteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'testuser', 'test@gmail.com', 'password')
    
    # ログインしていない場合
    def test_not_logged_in(self):
        response = self.client.get(reverse('chatrooms:get_match_completed'), data={})
        self.assertRedirects(
            response,
            reverse('login') + '?next=' + reverse('chatrooms:get_match_completed')
        )
    
    # GETでパラメータを与えなかった場合
    def test_not_params(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('chatrooms:get_match_completed'), data={})
        self.assertEqual(response.status_code, 400)
    
    # Room IDでRoomが見つからない場合
    def test_not_room(self):
        room = Room.objects.create(is_active=True)
        room.users.add(self.user)
        room_id = room.pk
        room.delete()

        self.client.force_login(self.user)
        response = self.client.get(reverse('chatrooms:get_match_completed'), data={'room_id': room_id})
        self.assertEqual(response.status_code, 400)
    
    # レコードがなかった場合
    def test_no_record(self):
        room = Room.objects.create(is_active=True)
        room.users.add(self.user)

        self.client.force_login(self.user)
        response = self.client.get(reverse('chatrooms:get_match_completed'), data={'room_id': room.pk})

        self.assertEqual(response.status_code, 404)

    # 2人でマッチングした場合
    def test_two_users(self):
        c1 = Client()
        c1.force_login(self.user)
        c2 = Client()
        c2.force_login(User.objects.create_user('testuser2', 'test2@gmail.com', 'password2'))

        post_data = {
            'condition': {
                'game_name': 'Test game',
                'number': 2
            }
        }
        # マッチング登録
        c1.post(reverse('chatrooms:register_matching'), data=json.dumps(post_data), content_type='application/json')
        c2.post(reverse('chatrooms:register_matching'), data=json.dumps(post_data), content_type='application/json')
        # マッチング待ち
        match_response1 = c1.get(reverse('chatrooms:get_match_room'))
        match_response2 = c2.get(reverse('chatrooms:get_match_room'))
        # マッチング承認
        c1.post(reverse('chatrooms:confirm_matching'), data=json.dumps({}), content_type='application/json')
        c2.post(reverse('chatrooms:confirm_matching'), data=json.dumps({}), content_type='application/json')
        # マッチング完了待ち
        compl_response1 = c1.get(reverse('chatrooms:get_match_completed'), data={'room_id': match_response1.json()['room_id']})
        compl_response2 = c2.get(reverse('chatrooms:get_match_completed'), data={'room_id': match_response2.json()['room_id']})

        self.assertEqual(compl_response1.status_code, 200)
        self.assertEqual(compl_response2.status_code, 200)
        self.assertTrue(compl_response1.json()['is_completed'])
        self.assertTrue(compl_response2.json()['is_completed'])
    
    # 3人以上でマッチングした場合
    def test_many_users(self):
        user_counts = 5
        clients = []
        for i in range(user_counts):
            c = Client()
            c.force_login(User.objects.create_user(f'testuser{i}', f'test{i}@gmail.com', f'password{i}'))
            clients.append(c)
        
        post_data = {
            'condition': {
                'game_name': 'Test game',
                'number': user_counts
            }
        }
        match_responses = []
        compl_responses = []
        # マッチング登録
        for c in clients:
            c.post(reverse('chatrooms:register_matching'), data=json.dumps(post_data), content_type='application/json')
        # マッチング待ち
        for c in clients:
            response = c.get(reverse('chatrooms:get_match_room'))
            match_responses.append(response)
        # マッチング承認
        for c in clients:
            c.post(reverse('chatrooms:confirm_matching'), data=json.dumps({}), content_type='application/json')
        # マッチング完了待ち
        for c, match_response in zip(clients, match_responses):
            response = c.get(reverse('chatrooms:get_match_completed'), data={'room_id': match_response.json()['room_id']})
            compl_responses.append(response)
        
        for response in compl_responses:
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['is_completed'])

