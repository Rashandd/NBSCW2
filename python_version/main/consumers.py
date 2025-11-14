import asyncio
import json
import logging
import random

from asgiref.sync import sync_to_async, async_to_sync
from django.contrib.auth import get_user_model
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import GameSession

User = get_user_model()

from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import VoiceChannel
logger = logging.getLogger('main') # İstediğiniz bir isim verin

def get_valid_neighbors(row, col):
    # Olası komşu hamleleri (Yukarı, Aşağı, Sol, Sağ)
    # (n_row2, n_row, n_col2, n_col mantığınız)
    potential_moves = [
        (row - 1, col),  # Yukarı
        (row + 1, col),  # Aşağı
        (row, col - 1),  # Sol
        (row, col + 1)  # Sağ
    ]

    valid_neighbors = []

    for r, c in potential_moves:
        # Ana kontrolümüz:
        if 0 <= r < 5 and 0 <= c < 5:
            # Sınırların içindeyse listeye ekle
            valid_neighbors.append((r, c))
        else:
            # Sınır dışındaysa uyarı ver (isteğe bağlı)
            print(f"-> Geçersiz komşu atlandı: ({r}, {c})")

    return valid_neighbors


def find_critical_cells(board_state):
    """
    SÖZLÜK (dict) tabanlı tahtada patlamaya hazır hücreleri bulur.
    YENİ KURAL: Bir hücre 4 veya daha fazla olduğunda patlar.
    """
    critical_cells = []
    if not board_state: return critical_cells

    for r_str, row in board_state.items():
        for c_str, cell in row.items():
            if not cell:
                continue

            # KURAL: Basitçe 4'ü kontrol et
            if cell.get('count', 0) >= 4:
                critical_cells.append((int(r_str), int(c_str)))
    return critical_cells


def bum(game, row, col, username):
    """
    SÖZLÜK (dict) tabanlı tahtada bir hücreyi patlatır.
    KURAL: Hücre 4 kaybeder, etrafa 1'er tane dağıtır.
    """
    r_str, c_str = str(row), str(col)

    # Patlayan hücredeki zar sayısını al (4, 5, 6... olabilir)
    try:
        current_count = game.board_state[r_str][c_str].get('count', 0)
    except KeyError:
        return  # Patlayacak hücre yoksa çık

    # KURAL: Patlayan hücre 4 zar kaybeder
    new_count = current_count - 4

    if new_count <= 0:
        game.board_state[r_str][c_str] = None  # Hücre boşalır
    else:
        # Kalan zarlar hücrede kalır
        game.board_state[r_str][c_str]['count'] = new_count
        # Sahibi değişmez (çünkü içinde hâlâ zar var)

    # 4 zarı etrafa dağıt
    valids = get_valid_neighbors(row, col)

    for r_int, c_int in valids:
        r_neighbor_str, c_neighbor_str = str(r_int), str(c_int)

        if r_neighbor_str not in game.board_state:
            game.board_state[r_neighbor_str] = {}

        current_cell = game.board_state[r_neighbor_str].get(c_neighbor_str)

        if current_cell is None:
            # Hücre boşsa, 1 zar ile yeni hücre oluştur
            game.board_state[r_neighbor_str][c_neighbor_str] = {
                'owner': username, 'count': 1
            }
        else:
            # Hücre doluysa, 1 zar ekle ve sahibini güncelle
            current_cell['count'] += 1
            current_cell['owner'] = username


def check_for_winner(game, current_player_user):
    """
    N-Kişilik kazanan kontrolü (Bunu zaten yapmıştık).
    """
    owners_left = set()
    board_state = game.board_state
    if not board_state: return

    for r_key, row in board_state.items():
        for c_key, cell in row.items():
            if cell and cell.get('owner'):
                owners_left.add(cell.get('owner'))

    if len(owners_left) <= 1:
        winner_user = None
        if len(owners_left) == 1:
            winner_username = owners_left.pop()
            try:
                winner_user = User.objects.get(username=winner_username)
            except User.DoesNotExist:
                winner_user = current_player_user
        else: # Hiç taş kalmadı
            winner_user = current_player_user

        game.status = 'finished'
        game.winner = winner_user
    return
def _count_player_pieces(board_state, player_username):
    """
    SÖZLÜK (dict) tabanlı tahtada bir oyuncunun kaç taşı olduğunu sayar.
    """
    count = 0
    if not board_state: return 0
    # board_state artık {'0': {'0': ...}, '1': ...}
    for r_key, row in board_state.items():
        for c_key, cell in row.items():
            if cell and cell.get('owner') == player_username:
                count += 1
    return count

class VoiceChatConsumer(AsyncJsonWebsocketConsumer):

    # DB'den VoiceChannel objesini çeker
    @database_sync_to_async
    def get_channel_by_slug(self, slug):
        try:
            return VoiceChannel.objects.get(slug=slug)
        except VoiceChannel.DoesNotExist:
            return None

    async def connect(self):
        logger.info(f"Yeni bağlantı denemesi. Kullanıcı Anonim mi? {self.scope['user'].is_anonymous}")

        if self.scope["user"].is_anonymous:
            logger.warning("Kimlik doğrulanmamış kullanıcı reddedildi.")
            await self.close()
            return

        # 2. Oda adını/slug'ını al
        query_params = parse_qs(self.scope['query_string'].decode('utf-8'))
        channel_slug = query_params.get('channel_slug', [None])[0]

        self.channel_slug = channel_slug

        if not self.channel_slug:
            await self.close()
            return

        # 3. Oda Var mı Kontrolü
        self.channel_object = await self.get_channel_by_slug(self.channel_slug)
        if not self.channel_object:
            await self.close()
            return

        self.channel_group_name = f'voice_{self.channel_slug}'
        self.user_id = str(self.scope["user"].id)

        # 4. Gruba (Odaya) katıl
        await self.channel_layer.group_add(
            self.channel_group_name,
            self.channel_name
        )

        await self.accept()

        # 5. Odaya katıldığını tüm gruba bildir
        await self.channel_layer.group_send(
            self.channel_group_name,
            {
                "type": "member.joined",
                "sender_id": self.user_id,
                "username": self.scope["user"].username,
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'channel_group_name') and self.channel_group_name and not self.scope["user"].is_anonymous:
            # 1. Gruptan (Oda) ayrıl
            await self.channel_layer.group_discard(
                self.channel_group_name,
                self.channel_name
            )
            # 2. Ayrıldığını gruba bildir
            await self.channel_layer.group_send(
                self.channel_group_name,
                {
                    "type": "member.left",
                    "sender_id": self.user_id,
                    "username": self.scope["user"].username,
                }
            )

        await super().disconnect(close_code)

    # --- Sinyalleşme ve Sohbet Mesajlarını İşleme ---

    async def receive_json(self, content, **kwargs):
        signal_type = content.get("signal_type")
        recipient_id = content.get("recipient_id")
        data = content.get("data")

        # 1. WebRTC Sinyalleşmesi (Offer/Answer/ICE)
        if signal_type in ['offer', 'answer', 'ice_candidate']:
            # Sinyali sadece ilgili alıcıya değil, gruba gönderiyoruz.
            # İstemci (JS) bu sinyalin kendisi için olup olmadığını kontrol edecek.
            await self.channel_layer.group_send(
                self.channel_group_name,
                {
                    "type": "webrtc.signal",
                    "sender_id": self.user_id,
                    "recipient_id": recipient_id,  # Kimin alması gerektiğini belirt
                    "signal_type": signal_type,
                    "data": data,
                }
            )

        # 2. Normal Sohbet Mesajı
        elif signal_type == 'chat_message':
            await self.channel_layer.group_send(
                self.channel_group_name,
                {
                    "type": "chat.message",
                    "sender_id": self.user_id,
                    "username": self.scope["user"].username,
                    "message": data,
                }
            )

        # 3. Durum Güncellemesi (Mute/Deafen)
        elif signal_type == 'status_update':
            await self.channel_layer.group_send(
                self.channel_group_name,
                {
                    "type": "member.status.update",
                    "sender_id": self.user_id,
                    "username": self.scope["user"].username,
                    "status": data  # {'muted': true, 'deafened': false}
                }
            )

    # --- Channel Layer'dan Gelen Olay İşleyicileri ---

    # Normal sohbet mesajlarını istemciye ilet
    async def chat_message(self, event):
        await self.send_json({
            "type": "chat_message",
            "sender_id": event["sender_id"],
            "username": event["username"],
            "message": event["message"],
        })

    # Yeni üye katılımını bildir
    async def member_joined(self, event):
        await self.send_json({
            "type": "system_notification",
            "event": "member_joined",
            "sender_id": event["sender_id"],
            "username": event["username"],
            "message": f"{event['username']} odaya katıldı."
        })

    # Üye ayrılışını bildir
    async def member_left(self, event):
        await self.send_json({
            "type": "system_notification",
            "event": "member_left",
            "sender_id": event["sender_id"],
            "username": event["username"],
            "message": f"{event['username']} odadan ayrıldı."
        })

    # WebRTC sinyallerini istemciye ilet
    async def webrtc_signal(self, event):
        await self.send_json({
            "type": "webrtc_signal",
            "sender_id": event["sender_id"],
            "recipient_id": event.get("recipient_id"),
            "signal_type": event["signal_type"],
            "data": event["data"],
        })

    # Durum güncellemesini gruba yayınla
    async def member_status_update(self, event):
        await self.send_json({
            "type": "member_status_update",
            "sender_id": event["sender_id"],
            "username": event["username"],
            "status": event["status"],
        })


# main/consumers.py


class GameConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'game_{self.game_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        try:
            self.game = await self.get_game(self.game_id)
            if not self.game:
                await self.close()
                return

            await self.channel_layer.group_add(
                self.game_group_name,
                self.channel_name
            )
            await self.accept()

            # --- N-Kişilik Otomatik Katılma Mantığı ---
            is_player = await self.is_user_in_game(self.game)

            if self.game.status == 'waiting' and not self.game.is_full and not is_player:
                self.game = await self.add_player_and_start_game(self.game, self.user)
                await self.broadcast_game_state(
                    self.game,
                    message=f"{self.user.username} oyuna katıldı."
                )
            else:
                await self.send_game_state_to_user(self.game)

        except Exception as e:
            print(f"HATA (connect): {e}")  # Sunucu loglarını kontrol et
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )

    async def receive_json(self, content, **kwargs):
        """
        Gelen hamleyi alır ve ASENKRON hamle işleyiciye yönlendirir.
        """
        if not self.user.is_authenticated:
            await self.send_error("Giriş yapmalısınız.")
            return
        if content.get('type') == 'make_move':
            # Eski '@database_sync_to_async' 'handle_make_move' yerine
            # 'async def handle_make_move' fonksiyonunu çağırıyoruz.
            await self.handle_make_move(content)

    async def handle_make_move(self, content):
        """
        YENİ ASENKRON HAMLE İŞLEYİCİ.
        Tüm zincirleme reaksiyonu adım adım yönetir.
        """
        try:
            # --- 1. TIKLAMA (İLK HAMLE) ---
            # Oyuncunun tıkladığı ilk hamleyi (örn: 3'ü 4 yapma)
            # veritabanına işler ve geçerli olup olmadığını kontrol eder.
            game, is_valid_move, error_msg = await self.perform_initial_click(content)

            if not is_valid_move:
                await self.send_error(error_msg)
                return

            player_username = self.user.username

            # --- 2. TIKLAMAYI YAYINLA ---
            # Tıkladığı hücrenin (örn: 4) görünmesi için
            # ilk durumu, patlama olmadan yayınla.
            await self.broadcast_game_state(game, message=f"{player_username} tıkladı.")

            # JS'in bu ilk tıklamayı çizmesi için kısa bir ara ver
            await asyncio.sleep(0.1)

            # --- 3. ZİNCİRLEME REAKSİYON DÖNGÜSÜ ---
            # Tahtada patlayacak hücre (sayısı >= 4 olan) kaldığı sürece
            # bu döngü devam eder.
            while True:
                # Patlayacak hücreleri bul
                cells_to_explode = await self.find_critical_cells_async(game.board_state)
                if not cells_to_explode:
                    break  # Patlayacak hücre kalmadı, döngü bitti.

                # --- ANLAŞILABİLİR ANİMASYON İÇİN BEKLE ---
                # Patlama dalgaları arasında BEKLE (örn: 600ms)
                await asyncio.sleep(0.6)

                # Patlamaları uygula (bum) ve DB'yi güncelle
                game, exploded_cells_list = await self.apply_explosions(
                    game.game_id, cells_to_explode, player_username
                )

                # Herkese "ARA DURUMU" ve patlayan hücre listesini gönder
                await self.broadcast_game_state(game, exploded_cells=exploded_cells_list)

            # --- 4. OYUN BİTTİ, SIRAYI DEĞİŞTİR ---
            # Döngü bittiğinde kazananı kontrol et ve sırayı değiştir
            final_game = await self.check_winner_and_change_turn(game.game_id, self.user)

            # Son bir bekleme ve "SON DURUMU" (yeni sıra ile) yayınla
            await asyncio.sleep(0.6)

            if final_game.status == 'finished':
                await self.broadcast_game_state(final_game, message="Oyun Bitti!")
            else:
                await self.broadcast_game_state(
                    final_game,
                    message=f"Sıra {final_game.current_turn.username} kullanıcısında."
                )

        except Exception as e:
            print(f"HATA (handle_make_move ASYNC): {e}")
            await self.send_error(f"Hamle yapılamadı: {e}")

    # --- Grup Yayını Metodları ---
    @database_sync_to_async
    def perform_initial_click(self, content):
        """
        Sadece ilk tıklamayı yapar. (Hata kontrolü)
        (Eski 'handle_make_move' kodunuzun sadeleştirilmiş hali)
        """
        with transaction.atomic():
            game = GameSession.objects.select_for_update().get(game_id=self.game_id)

            if game.status != 'in_progress':
                return game, False, "Oyun başlamadı veya bitti."
            if game.current_turn != self.user:
                return game, False, "Sıra sizde değil."

            row, col = content.get('row'), content.get('col')
            r_str, c_str = str(row), str(col)
            piece_count = _count_player_pieces(game.board_state, self.user.username)
            cell = game.board_state.get(r_str, {}).get(c_str)

            if piece_count == 0:  # İlk hamle
                if cell is not None:
                    return game, False, "İlk hamleniz boş bir hücreye olmalı."
                if r_str not in game.board_state: game.board_state[r_str] = {}
                game.board_state[r_str][c_str] = {'owner': self.user.username, 'count': 1}
            else:  # Normal hamle
                if not cell:
                    return game, False, "Boş bir hücreye oynayamazsınız."
                if cell.get('owner') != self.user.username:
                    return game, False, "Bu hücre rakibinize ait."
                cell['count'] += 1
                cell['owner'] = self.user.username

            game.save()
            return game, True, ""

    @database_sync_to_async
    def find_critical_cells_async(self, board_state):
        # find_critical_cells (CPU-yoğun)
        return find_critical_cells(board_state)

    @database_sync_to_async
    def apply_explosions(self, game_id, cells_to_explode, player_username):
        """
        Bir patlama dalgasını (o an kritik olan tüm hücreler)
        veritabanına işler.
        """
        with transaction.atomic():
            game = GameSession.objects.get(game_id=game_id)
            for r, c in cells_to_explode:
                # 'bum' fonksiyonu game.board_state'i GÜNCELLER
                bum(game, r, c, player_username)
            game.save()
            return game, cells_to_explode

    @database_sync_to_async
    def check_winner_and_change_turn(self, game_id, user):
        """
        Kazananı kontrol eder ve sırayı değiştirir.
        """
        with transaction.atomic():
            game = GameSession.objects.get(game_id=game_id)
            check_for_winner(game, user)  # Kazananı belirler

            if game.status != 'finished':
                players_list = list(game.players.all())
                current_turn_index = players_list.index(user)
                next_turn_index = (current_turn_index + 1) % len(players_list)
                game.current_turn = players_list[next_turn_index]

            game.save()
            return game
    async def broadcast_game_state(self, game, message=None, exploded_cells=None):
        state_data = await self.get_game_state_data_async(game)
        state_data['message'] = message
        state_data['exploded_cells'] = exploded_cells if exploded_cells else []
        await self.channel_layer.group_send(self.game_group_name, state_data)

    def broadcast_game_state_sync(self, game, message=None, exploded_cells=None):
        state_data = self.get_game_state_data_sync(game)
        state_data['message'] = message
        state_data['exploded_cells'] = exploded_cells if exploded_cells else []
        async_to_sync(self.channel_layer.group_send)(self.game_group_name, state_data)

    async def game_state(self, event):
        await self.send_json(event)

    async def send_error(self, message):
        await self.send_json({'type': 'error', 'message': message})

    def send_error_to_user(self, message):
        async_to_sync(self.send_json)({'type': 'error', 'message': message})

    # --- Veritabanı (Sync/Async) Metodları ---
    @database_sync_to_async
    def get_game(self, game_id):
        try:
            return GameSession.objects.select_related(
                'game_type', 'host', 'current_turn', 'winner'
            ).prefetch_related('players').get(game_id=self.game_id)
        except GameSession.DoesNotExist:
            return None

    @database_sync_to_async
    def is_user_in_game(self, game):
        return game.players.filter(id=self.user.id).exists()

    @database_sync_to_async
    def add_player_and_start_game(self, game, user):
        with transaction.atomic():
            game_with_lock = GameSession.objects.select_for_update().get(game_id=game.id)
            if game_with_lock.is_full or game_with_lock.status != 'waiting':
                return game_with_lock

            game_with_lock.players.add(user)

            if game_with_lock.players.count() >= game_with_lock.game_type.max_players:
                game_with_lock.status = 'in_progress'
                players_list = list(game_with_lock.players.all())
                starter = random.choice(players_list)
                game_with_lock.current_turn = starter

            game_with_lock.save()
            return game_with_lock

    @database_sync_to_async
    def get_game_state_data_async(self, game_obj):
        return self.get_game_state_data_sync(game_obj)

    def get_game_state_data_sync(self, game_obj):
        players_list = list(game_obj.players.all())
        player_usernames = [p.username for p in players_list]
        return {
            'type': 'game_state',
            'state': game_obj.board_state,
            'turn': game_obj.current_turn.username if game_obj.current_turn else None,
            'players': player_usernames,
            'status': game_obj.status,
            'winner': game_obj.winner.username if game_obj.winner else None,
        }

    async def send_game_state_to_user(self, game_obj):
        state_data = await self.get_game_state_data_async(game_obj)
        await self.send_json(state_data)