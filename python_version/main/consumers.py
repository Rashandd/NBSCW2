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
    Verilen 5x5'lik board_state'i tarar.
    'count' değeri 4 olan hücrelerin (satır, sütun) koordinatlarını
    bir liste içinde döndürür.

    Args:
        board_state (list[list[dict|None]]): Oyun tahtasının mevcut durumu.

    Returns:
        list[tuple(int, int)]: 'count' == 4 olan hücrelerin (row, col) listesi.
    """

    # 5x5'lik bir tahta olduğunu varsayıyoruz
    ROWS = 5
    COLS = 5

    # 'count' değeri 4 olan hücrelerin koordinatlarını (r, c)
    # depolayacağımız liste.
    critical_cells = []

    for row in range(ROWS):
        for col in range(COLS):
            # O anki hücreyi al
            cell = board_state[row][col]

            # 1. Hücre dolu mu? (None değil mi?): 'if cell:'
            # 2. Doluysa 'count' değeri 4 mü?: 'cell['count'] == 4'
            if cell and cell.get('count') == 4:
                # Eğer iki koşul da doğruysa, koordinatları listeye ekle
                critical_cells.append((row, col))

    # Listeyi döndür
    return critical_cells
def bum(game, row, col, username):
    """
    (row, col) koordinatındaki hücreyi patlatır.
    1. Patlayan hücrenin sayısını 0 yapar.
    2. Komşu hücreleri bulur.
    3. Komşu hücrelerin sayısını 1 artırır (eğer boşsa 1 yapar).
    """

    # 1. Patlayan hücrenin kendisini sıfırla
    # (Bu hücrenin 'None' olmadığını ve 'count' == 4 olduğunu varsayıyoruz,
    # çünkü bu fonksiyonu 'while' döngüsü çağırdı)
    exploding_cell = game.board_state[row][col]
    exploding_cell['count'] = 0
    # Opsiyonel: Patlayan hücre sahipsiz kalabilir
    # exploding_cell['owner'] = None

    # 2. Geçerli komşuları al
    # (get_valid_neighbors fonksiyonunun tanımlı olduğunu varsayıyoruz)
    valids = get_valid_neighbors(row, col)

    # 3. Komşuları güncelle
    for r, c in valids:
        # Komşu hücrenin mevcut durumunu al
        current_cell = game.board_state[r][c]

        # --- ÖNCEKİ SORUNUN ÇÖZÜMÜ (None KONTROLÜ) ---
        if current_cell is None:
            # Hücre boşsa (NoneType), yeni hücre oluştur ve 1 yap
            game.board_state[r][c] = {
                'owner': username,
                'count': 1
            }
        else:
            # Hücre doluysa, 'count'u 1 artır ve sahibini güncelle
            current_cell['count'] += 1
            current_cell['owner'] = username

    # Bu fonksiyon 'game' objesini doğrudan değiştirdi,
    # bir şey döndürmesine gerek yok.


def check_for_winner(game, current_player_user):
    """
    Tüm patlamalar bittikten sonra, tahtada 1'den fazla oyuncunun
    taşı kalıp kalmadığını kontrol eder.
    N-Kişilik (2-4) oyunlar için güncellendi.
    """

    # Tahtadaki tüm mevcut oyuncuların (sahiplerin)
    # benzersiz bir listesini (set) tut
    owners_left = set()

    board_state = game.board_state
    if not board_state:  # Tahta boşsa (olmamalı ama)
        return

    # Tahtayı tara
    for r_key, row in board_state.items():
        for c_key, cell in row.items():
            # Eğer hücre doluysa ve bir sahibi varsa
            if cell and cell.get('owner'):
                owners_left.add(cell.get('owner'))

    # --- Kazanan Kontrolü ---

    # 1. Sadece bir oyuncunun taşı kaldıysa (veya hiç kalmadıysa)
    if len(owners_left) <= 1:

        winner_user = None

        if len(owners_left) == 1:
            # Tahtada kalan tek kişinin adını al
            winner_username = owners_left.pop()
            try:
                # O kişinin User objesini bul
                winner_user = User.objects.get(username=winner_username)
            except User.DoesNotExist:
                # Bu olmamalı, ama olursa kazanan hamleyi yapandır
                winner_user = current_player_user
        else:
            # Hiç taş kalmadıysa (rakibin son taşını patlattı)
            # Kazanan, hamleyi yapan 'current_player_user'dır
            winner_user = current_player_user

        # Oyunu bitir ve kazananı ata
        game.status = 'finished'
        game.winner = winner_user

    # 2. Birden fazla oyuncunun (len(owners_left) > 1) taşı varsa
    # Oyun devam eder, hiçbir şey yapma.
    return
def _count_player_pieces(board_state, username):
        """Tahtadaki belirli bir oyuncuya ait taş sayısını döner."""
        count = 0
        for r in range(5):
            for c in range(5):
                cell = board_state[r][c]
                if cell and cell.get('owner') == username:
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
        if not self.user.is_authenticated:
            await self.send_error("Giriş yapmalısınız.")
            return

        if content.get('type') == 'make_move':
            await self.handle_make_move(content)

    @database_sync_to_async
    def handle_make_move(self, content):
        try:
            with transaction.atomic():
                game = GameSession.objects.select_for_update().get(game_id=self.game_id)
                player_username = self.user.username

                if game.status != 'in_progress':
                    return self.send_error_to_user("Oyun başlamadı veya bitti.")
                if game.current_turn != self.user:
                    return self.send_error_to_user("Sıra sizde değil.")

                row = content.get('row')
                col = content.get('col')
                piece_count = _count_player_pieces(game.board_state, player_username)

                # 'str' anahtarları kullandığımız için 'str' ile erişmeliyiz
                cell = game.board_state.get(str(row), {}).get(str(col))

                exploded_cells_list = []

                if piece_count == 0:  # İlk Hamle
                    if cell is not None:
                        return self.send_error_to_user("İlk hamleniz boş bir hücreye olmalı.")
                    if not game.board_state.get(str(row)):
                        game.board_state[str(row)] = {}
                    game.board_state[str(row)][str(col)] = {'owner': player_username, 'count': 1}
                else:  # Normal Hamle
                    if not cell:
                        return self.send_error_to_user("Boş bir hücreye oynayamazsınız.")
                    if cell.get('owner') != player_username:
                        return self.send_error_to_user("Bu hücre rakibinize ait.")

                    cell['count'] += 1
                    cell['owner'] = player_username
                    cells_to_explode = find_critical_cells(game.board_state)
                    while cells_to_explode:
                        r, c = cells_to_explode.pop(0)
                        if (r, c) not in exploded_cells_list:
                            exploded_cells_list.append((r, c))
                        bum(game, r, c, player_username)
                        cells_to_explode = find_critical_cells(game.board_state)
                    check_for_winner(game, self.user)

                if game.status != 'finished':
                    players_list = list(game.players.all())
                    current_turn_index = players_list.index(self.user)
                    next_turn_index = (current_turn_index + 1) % len(players_list)
                    game.current_turn = players_list[next_turn_index]

                game.save()

                self.broadcast_game_state_sync(
                    game,
                    message=f"{player_username} hamle yaptı.",
                    exploded_cells=exploded_cells_list
                )
        except Exception as e:
            print(f"HATA (handle_make_move): {e}")
            self.send_error_to_user(f"Hamle yapılamadı: {e}")

    # --- Grup Yayını Metodları ---
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