import json
import requests
from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import QueryDict
from django.http.response import JsonResponse, HttpResponse
from django.views import generic
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy

from .models import Room, MatchingRecord, Topic

User = get_user_model()


class IndexView(generic.TemplateView):
    template_name = 'chatrooms/index.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class RoomMatchView(LoginRequiredMixin, generic.TemplateView):
    login_url = reverse_lazy('accounts:login')
    template_name = 'chatrooms/room_match.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class RoomView(LoginRequiredMixin, UserPassesTestMixin, generic.TemplateView):
    login_url = reverse_lazy('accounts:login')
    template_name = 'chatrooms/room.html'

    # Room に紐づいたユーザーのみアクセス可能にする
    def test_func(self):
        user = self.request.user
        room = get_object_or_404(Room, pk=self.kwargs['pk'])
        return any([user.pk == member.pk for member in room.users.all()])

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        room = get_object_or_404(Room, pk=self.kwargs['pk'])
        context['room'] = room

        members = room.users.all()

        member_names = {str(member.uuid): member.username for member in members}
        context['member_names'] = json.dumps(member_names)

        member_icons = {str(member.uuid): member.icon_image.url for member in members}
        context['member_icons'] = json.dumps(member_icons)

        return context

class RoomListView(generic.ListView):
    model = Room
    template_name = 'chatrooms/room_list.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hoge'] = 'hoge'
        return context


# Skyway Test Page
def skyway(request):
    return render(request, 'chatrooms/skyway.html')


"""
検索API
"""
def popular_topics(request):
    params = request.GET

    # TODO
    # Topicにpopularityカラムを追加
    result = Topic.objects.all()
    return JsonResponse({"topics": [topic.data() for topic in result]}, status=200)


def search_topics(request):
    params = request.GET

    search_text = params.get('search_text')
    if search_text is None or not search_text:
        return JsonResponse({}, status=400)
    
    if search_text == '/all':
        # allコマンド = 全データ
        query = Q()
    else:
        keywords = search_text.split()

        query = Q()
        for keyword in keywords:
            query &= (
                Q(name__icontains=keyword)
                | Q(name__istartswith=keyword)
                | Q(name__iendswith=keyword)
                | Q(tags__name__icontains=keyword)
                | Q(tags__name__istartswith=keyword)
                | Q(tags__name__iendswith=keyword)
            )

    result = Topic.objects.filter(query)
    return JsonResponse({"topics": [topic.data() for topic in result]}, status=200)


"""
トピック追加API
"""
def create_topic(request):
    json_data = json.loads(request.body)

    name = json_data.get('name')
    topic, created = Topic.objects.update_or_create(
        name=name
    )
    if not created:
        return JsonResponse({'is_created': False, 'message': 'A topic with the same name already exists.'})
    topic.save()
    return JsonResponse({'is_created': True}, status=200)


"""
マッチング処理の WebAPI
Ajax で Json の送受信をすることを前提に書いている
"""

# マッチングに登録
@login_required
def register_matching(request):
    json_data = json.loads(request.body)
    user_id = request.user.pk


    condition = json_data.get('condition')
    if condition is None:
        return JsonResponse({}, status=400)
    
    # 条件のバリデーション
    topic = Topic.objects.get(name=condition['topic'])
    if topic is None:
        return JsonResponse({}, status=400)

    # 既に待ち状態であれば登録しない
    record = MatchingRecord.objects.filter(user=user_id, is_active=True).first()
    if record is not None:
        return JsonResponse({'is_registered': False}, status=200)
    
    submission_time = timezone.now()
    defaults = {
        'user': User.objects.get(pk=user_id),
        'topic': topic,
        'number': condition['number'],
        'submission_time': submission_time,
        'is_active': True,
        'is_pending': False,
        'is_confirmed': False
    }

    record, created = MatchingRecord.objects.update_or_create(
        user=User.objects.get(pk=user_id),
        defaults=defaults,
    )
    record.save()
    return JsonResponse({'is_registered': True}, status=200)


# マッチングを登録解除
@login_required
def unregister_matching(request):
    json_data = json.loads(request.body)
    user_id = request.user.pk

    # 解除するレコードがなければ処理しない
    record = MatchingRecord.objects.filter(user=user_id, is_active=True).first()
    if record is None:
        return JsonResponse({'is_unregistered': False}, status=200)

    record.is_active = False
    record.is_pending = False
    record.is_confirmed = False
    record.save()
    return JsonResponse({'is_unregistered': True}, status=200)



# マッチングしたルームIDを返す
@login_required
def get_match_room(request):
    user_id = request.user.pk

    myrecord = MatchingRecord.objects.filter(
        user=user_id,
        is_active=True,
        is_pending=False,
        is_confirmed=False).first()
    if myrecord is None:
        return JsonResponse({'message': 'valid record is not found.'}, status=404)

    # 入れるルームが既にあればそれを返す
    room = Room.objects.filter(
        users=user_id,
        is_active=True,
        created_date__gte=myrecord.submission_time).order_by('-created_date').first()
    if room is not None:
        # 保留状態にする
        myrecord.is_pending = True
        myrecord.save()
        return JsonResponse({
            'is_matched': True,
            'room_id': str(room.pk),
            'room_url': reverse_lazy('chatrooms:room', kwargs={'pk': room.pk})
            },
            status=200)

    """
    マッチングできるかチェック
    """
    # マッチングするものがあるか検索
    match_records = MatchingRecord.objects.filter(
        topic=myrecord.topic,
        number=myrecord.number,
        is_active=True,
        is_pending=False,
        is_confirmed=False).order_by('submission_time')

    # クエリセットが条件の数より少ない場合は不適
    if match_records.count() < myrecord.number:
        return JsonResponse({
            'is_matched': False,
            'message': 'not matched.'
            }, status=200)

    # クエリセットを条件の数に制限
    match_records = match_records[:myrecord.number]

    # クエリセットと関連した User を取得し、idをリスト match_users_id に格納
    match_users_id = [record.user.pk for record in match_records]

    # 自分が入っていない場合は不適
    if not user_id in match_users_id:
        return JsonResponse({
            'is_matched': False,
            'message': 'not matched.'
            }, status=200)


    """
    ルームを作成
    """
    # 既に作られているか
    room = Room.objects.filter(
        users=user_id,
        is_active=True,
        created_date__gte=myrecord.submission_time).order_by('-created_date').first()
    if room is None:
        # ない場合はルーム作成
        room = Room.objects.create(is_active=True)
        for user_id in match_users_id:
            room.users.add(User.objects.get(pk=user_id))
    
    
    # 保留状態にする
    myrecord.is_pending = True
    myrecord.save()
    
    return JsonResponse({
        'is_matched': True,
        'room_id': str(room.pk),
        'room_url': reverse_lazy('chatrooms:room', kwargs={'pk': room.pk})
        },
        status=200)


# マッチングを承認する
@login_required
def confirm_matching(request):
    json_data = json.loads(request.body)
    user_id = request.user.pk

    record = MatchingRecord.objects.filter(user=user_id, is_active=True, is_pending=True, is_confirmed=False).first()
    if record is None:
        return JsonResponse({'is_confirmed': False}, status=200)
    
    record.is_confirmed = True
    record.is_pending = False
    record.save()
    return JsonResponse({'is_confirmed': True}, status=200)

# マッチング承認をキャンセルして再び待ち状態へ
@login_required
def cancel_confirm(request):
    json_data = json.loads(request.body)
    user_id = request.user.pk

    record = MatchingRecord.objects.filter(user=user_id, is_active=True, is_pending=False, is_confirmed=True).first()
    if record is None:
        return JsonResponse({'is_cancelled': False}, status=200)
    
    record.is_pending = False
    record.is_confirmed = False
    record.save()
    return JsonResponse({'is_cancelled': True}, status=200)

# 他のユーザーがマッチングを承認したか
# 全員承認していればマッチング完了
@login_required
def get_match_completed(request):
    user_id = request.user.pk

    room_id = request.GET.get('room_id')
    if room_id is None or not room_id:
        return JsonResponse({
            'is_completed': False,
            'is_cancelled': False,
            'message': 'invalid room id.'
            }, status=400)
    
    room = Room.objects.filter(pk=room_id, users=user_id).first()
    if room is None:
        return JsonResponse({
            'is_completed': False,
            'is_cancelled': False,
            'message': 'invalid room id.'
            }, status=400)

    users = room.users.all()

    for user in users:
        try:
            record = MatchingRecord.objects.filter(user=user.pk).first()
        except User.matchingrecord.RelatedObjectDoesNotExist as ex:
            print('User.matchingrecord.RelatedObjectDoesNotExist')
            return JsonResponse({
                'is_completed': False,
                'is_cancelled': False,
                'message': 'error',
                'error': ex
                }, status=500)
        except Exception as ex:
            return JsonResponse({
                'is_completed': False,
                'is_cancelled': False,
                'message': 'error',
                'error': ex
                }, status=500)
        
        # レコードが見つからない場合
        if record is None:
            return JsonResponse({
                'is_completed': False,
                'is_cancelled': False,
                'message': 'record is not found.'
                }, status=404)
        
        # キャンセル処理
        if not record.is_active:
            room.is_active = False
            room.save()
            return JsonResponse({
                'is_completed': False,
                'is_cancelled': True,
                'message': 'matching cancelled.'
                }, status=200)

        # 未完了
        if not record.is_confirmed:
            return JsonResponse({
                'is_completed': False,
                'is_cancelled': False,
                'message': 'not confirmed.'
                }, status=200)
    
    return JsonResponse({
        'is_completed': True,
        'is_cancelled': False,
        'message': 'matching done.'
        }, status=200)
