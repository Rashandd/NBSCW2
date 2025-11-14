from django.urls import path
from . import views
from django.contrib.auth import views as auth_views # auth_views'i import edin

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('oda/<slug:slug>/', views.voice_channel_view, name='odasayfasi'),
    path('settings/', views.settings_view, name='settings'),

    path('game-lobby/', views.all_games_lobby, name='all_games_lobby'),

    # 2. ÖZEL LOBİ (Bu, minigames.html'in yönlendirdiği yerdir)
    # Örn: /dice-wars/lobby/
    # -> views.game_specific_lobby
    path('<slug:game_slug>/lobby/', views.game_specific_lobby, name='game_specific_lobby'),

    # 3. ODA YÖNETİM URL'LERİ (Değişiklik yok)
    path('<slug:game_slug>/create/', views.create_game, name='create_game'),
    path('game/join/<uuid:game_id>/', views.join_game, name='join_game'),
    path('game/play/<uuid:game_id>/', views.game_room, name='game_room'),
    path('game/delete/<uuid:game_id>/', views.delete_game, name='delete_game'),
]