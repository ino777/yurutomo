from django.urls import path

from . import views

app_name= 'chatrooms'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('room-match', views.RoomMatchView.as_view(), name='room_match'),
    path('room/<uuid:pk>', views.RoomView.as_view(), name='room'),
    path('skyway', views.skyway, name='skyway'),
    path('rooms', views.RoomListView.as_view(), name='room_list'),

    path('api/registermatching', views.register_matching, name='register_matching'),
    path('api/unregistermatching', views.unregister_matching, name='unregister_matching'),
    path('api/getmatchroom', views.get_match_room, name='get_match_room'),
    path('api/confirmmatching', views.confirm_matching, name='confirm_matching'),
    path('api.cancel_confirm', views.cancel_confirm, name='cancel_confirm'),
    path('api/getmatchcompleted', views.get_match_completed, name='get_match_completed'),
]