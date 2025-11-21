from django.urls import path
from . import views
from django.contrib.auth import views as auth_views # auth_views'i import edin

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('server/join/', views.join_server, name='join_server'),
    path('server/<slug:slug>/', views.server_view, name='server_view'),
    path('server/<slug:server_slug>/create-text-channel/', views.create_text_channel, name='create_text_channel'),
    path('server/<slug:server_slug>/create-voice-channel/', views.create_voice_channel, name='create_voice_channel'),
    path('server/<slug:server_slug>/channel/<slug:channel_slug>/', views.channel_view, name='channel_view'),
    path('oda/<slug:slug>/', views.voice_channel_view, name='odasayfasi'),  # Legacy support
    path('api/chat/<slug:slug>/messages/', views.chat_messages_api, name='chat_messages_api'),
    path('settings/', views.settings_view, name='settings'),

    path('game-lobby/', views.all_games_lobby, name='all_games_lobby'),


    path('<slug:game_slug>/lobby/', views.game_specific_lobby, name='game_specific_lobby'),

    # 3. ODA YÖNETİM URL'LERİ (Değişiklik yok)
    path('<slug:game_slug>/create/', views.create_game, name='create_game'),
    path('game/join/<uuid:game_id>/', views.join_game, name='join_game'),
    path('game/play/<uuid:game_id>/', views.game_room, name='game_room'),
    path('game/rematch/<uuid:game_id>/', views.rematch_request, name='rematch_request'),
    path('game/delete/<uuid:game_id>/', views.delete_game, name='delete_game'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('<slug:game_slug>/leaderboard/', views.game_leaderboard, name='game_leaderboard'),
]