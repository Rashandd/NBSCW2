import json
import logging

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
    Tüm patlamalar bittikten sonra, rakibin taşı kalmış mı diye kontrol eder.
    """
    # Rakibi belirle
    opponent = game.player2 if current_player_user == game.player1 else game.player1

    # Eğer rakip henüz yoksa (lobi) veya bir şekilde None ise kontrol etme
    if not opponent:
        return

    opponent_username = opponent.username
    opponent_pieces = 0

    # Tahtayı tara
    for r in range(5):
        for c in range(5):
            cell = game.board_state[r][c]
            # Rakibe ait bir hücre bulunduysa...
            if cell and cell.get('owner') == opponent_username:
                opponent_pieces += 1
                break  # Arama yapmayı bırak, rakibin taşı var.
        if opponent_pieces > 0:
            break  # Dış döngüden de çık

    # Döngüler bittiğinde rakibin hiç taşı bulunamadıysa...
    if opponent_pieces == 0:
        game.status = 'finished'
        game.winner = current_player_user
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


class GameConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # 1. URL'den game_id'yi al
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f"game_{self.game_id}"
        self.user = self.scope['user']

        # 2. Giriş yapmamış kullanıcıları reddet
        if not self.user.is_authenticated:
            await self.close()
            return

        # 3. Oyunu veritabanından al ve kullanıcıyı gruba ekle
        try:
            self.game = await self.get_game_session()
            await self.channel_layer.group_add(
                self.game_group_name,
                self.channel_name
            )
            await self.accept()

            # 4. Bağlanan kullanıcıya güncel oyun durumunu gönder
            await self.send_game_state(self)

        except GameSession.DoesNotExist:
            await self.close()
        except Exception as e:
            print(f"HATA (connect): {e}")  # Sunucu loglarını kontrol et
            await self.close()

    async def disconnect(self, close_code):
        # Grubu terk et
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )
        # ... (Oyunculardan biri çıkınca ne yapılacağına dair mantık buraya eklenebilir) ...

    async def receive(self, text_data):
        data = json.loads(text_data)

        # Sadece 'make_move' (hamle yap) mesajlarını işle
        if data.get('type') == 'make_move':
            await self.handle_make_move(data)

    # --- HAMLE ALMA VE OYUN MANTIĞI ---

    @database_sync_to_async
    def handle_make_move(self, data):
        # 1. Veritabanından en güncel hali al (transaction kilidiyle)
        with transaction.atomic():
            game = GameSession.objects.select_for_update().get(game_id=self.game_id)

            # 2. Gerekli kontroller
            if game.status != 'in_progress':
                return self.send_error_to_user("Oyun henüz başlamadı veya bitti.")
            if game.current_turn != self.user:
                return self.send_error_to_user("Sıra sizde değil.")

            # 3. OYUN MANTIĞINI ÇAĞIR (Bu sizin DiceWars mantığınız olmalı)
            # --------------------------------------------------
            # ÖRNEK MANTIK (Kendi mantığınızla değiştirin):
            try:
                row = int(data.get('row'))
                col = int(data.get('col'))

                # 'game_logic.py' dosyanız olduğunu varsayalım
                # game_logic = DiceWarsGame(game.board_state)
                # result = game_logic.make_move(self.user.username, row, col)

                # Şimdilik basit bir örnek:
                board_state = game.board_state or {}
                if not board_state.get(str(row)):
                    board_state[str(row)] = {}

                board_state[str(row)][str(col)] = {
                    'owner': self.user.username,
                    'count': 1
                }
                game.board_state = board_state

                # Sırayı diğer oyuncuya geçir (N-kişilik)
                players_list = list(game.players.all())
                current_turn_index = players_list.index(self.user)
                next_turn_index = (current_turn_index + 1) % len(players_list)
                game.current_turn = players_list[next_turn_index]

                game.save()

                # Başarılı hamle sonrası herkese yeni durumu gönder
                return self.send_game_state_to_group(game)

            except Exception as e:
                print(f"HATA (handle_make_move): {e}")
                return self.send_error_to_user("Geçersiz hamle.")
            # --------------------------------------------------

    # --- VERİ GÖNDERME FONKSİYONLARI ---

    @database_sync_to_async
    def get_game_state_data(self, game_obj):
        """Veritabanı nesnesini JSON'a hazır dict'e çevirir."""
        # N-Kişilik modele göre 'players' listesi oluştur
        player_usernames = [p.username for p in game_obj.players.all()]

        return {
            'type': 'game_state',  # 'game_message' yerine 'game_state'
            'state': game_obj.board_state,
            'turn': game_obj.current_turn.username if game_obj.current_turn else None,
            'players': player_usernames,  # 'p1'/'p2' yerine bu
            'status': game_obj.status,
            'winner': game_obj.winner.username if game_obj.winner else None,
            'message': '',  # Hamle mesajları için
            'exploded_cells': [],  # Patlama animasyonu için
        }

    def send_game_state_to_group(self, game_obj):
        """
        Oyun durumunu gruptaki HERKESE gönderir.
        (Bu 'async' olmalı çünkü channel_layer'a erişiyor)
        """
        state_data = self.get_game_state_data(game_obj)

        # 'database_sync_to_async' içindeyken 'await' kullanamayız,
        # bu yüzden 'async_to_sync' ile sarmalarız.
        async_to_sync(self.channel_layer.group_send)(
            self.game_group_name,
            state_data  # 'type' anahtarı zaten state_data içinde ('game_state')
        )

    async def send_game_state(self, event):
        """
        Gruptan gelen 'game_state' mesajını WebSocket'e gönderir.
        """
        await self.send(text_data=json.dumps({
            'type': event.get('type', 'game_state'),
            'state': event.get('state'),
            'turn': event.get('turn'),
            'players': event.get('players'),  # N-kişilik
            'status': event.get('status'),
            'winner': event.get('winner'),
            'message': event.get('message'),
            'special_event': event.get('special_event'),
            'exploded_cells': event.get('exploded_cells'),
        }))

    def send_error_to_user(self, message):
        """Sadece bu kullanıcıya (hamleyi yapan) hata mesajı gönderir."""
        async_to_sync(self.send)(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    # --- GEREKLİ VERİTABANI ERİŞİMİ ---

    @database_sync_to_async
    def get_game_session(self):
        """
        WebSocket bağlanırken oyunu çeker.
        (N-kişilik model için güncellendi)
        """
        game = GameSession.objects.select_related(
            'game_type', 'host', 'current_turn', 'winner'
        ).prefetch_related('players').get(game_id=self.game_id)

        # Oyuncu veya izleyici mi? (İzin kontrolü)
        is_player = game.players.filter(id=self.user.id).exists()
        is_spectator = not is_player

        # Eğer izleyiciyse ve oda bekliyorsa ve dolu değilse...
        # Normalde bu 'join_game' view'i tarafından engellenir,
        # ama WebSocket'e direkt gelenler için ekstra güvenlik.
        if is_spectator and game.status == 'waiting' and not game.is_full:
            # İzleyiciyi oyuncu listesine ekle
            game.players.add(self.user)
            # (Burada 'join_game' view'indeki gibi
            # oyun başlatma mantığı da eklenebilir)

        return game