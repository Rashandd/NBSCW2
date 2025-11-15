import asyncio
import json
import logging
import random

from asgiref.sync import sync_to_async, async_to_sync
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import GameSession

User = get_user_model()

from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from .models import VoiceChannel
logger = logging.getLogger('main') # İstediğiniz bir isim verin


class DiceWars:
    def get_valid_neighbors(self,row, col, board_size):
        """
        Belirtilen boyuttaki (board_size x board_size) bir tahta için
        geçerli komşuları döndürür.
        """
        potential_moves = [
            (row - 1, col),  # Yukarı
            (row + 1, col),  # Aşağı
            (row, col - 1),  # Sol
            (row, col + 1)  # Sağ
        ]
        valid_neighbors = []

        for r, c in potential_moves:
            # --- DEĞİŞTİ: 5 yerine board_size ---
            if 0 <= r < board_size and 0 <= c < board_size:
                valid_neighbors.append((r, c))
            # else:
            # print(f"-> Geçersiz komşu atlandı: ({r}, {c})")

        return valid_neighbors
    def find_critical_cells(self,board_state):
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
    def bum(self,game, row, col, username):
        """
        SÖZLÜK (dict) tabanlı tahtada bir hücreyi patlatır.
        'game' objesinden dinamik 'board_size' alır.
        """
        r_str, c_str = str(row), str(col)
        try:
            current_count = game.board_state[r_str][c_str].get('count', 0)
        except KeyError:
            return

        new_count = current_count - 4
        if new_count <= 0:
            game.board_state[r_str][c_str] = None
        else:
            game.board_state[r_str][c_str]['count'] = new_count

        # --- DEĞİŞTİ: game.board_size parametresi eklendi ---
        valids = self.get_valid_neighbors(row, col, game.board_size)
        # ---------------------------------------------------

        for r_int, c_int in valids:
            r_neighbor_str, c_neighbor_str = str(r_int), str(c_int)
            if r_neighbor_str not in game.board_state:
                game.board_state[r_neighbor_str] = {}

            current_cell = game.board_state[r_neighbor_str].get(c_neighbor_str)
            if current_cell is None:
                game.board_state[r_neighbor_str][c_neighbor_str] = {
                    'owner': username, 'count': 1
                }
            else:
                current_cell['count'] += 1
                current_cell['owner'] = username
    def check_for_winner(self,game, current_player_user):
        owners_left = set()
        board_state = game.board_state
        if not board_state: return
        for r_key, row in board_state.items():
            for c_key, cell in row.items():
                if cell and cell.get('owner'):
                    owners_left.add(cell.get('owner'))

        # --- DÜZELTME: Oyunun başlamış olması ve 1'den fazla oyuncu olması lazım ---
        # Bu kontrol, tek başına oynayan host'un anında kazanmasını engeller
        if game.status == 'in_progress' and game.players.count() > 1:
            if len(owners_left) <= 1:
                winner_user = None
                if len(owners_left) == 1:
                    winner_username = owners_left.pop()
                    try:
                        winner_user = User.objects.get(username=winner_username)
                    except User.DoesNotExist:
                        winner_user = current_player_user
                else:  # Hiç taş kalmadı (örn. 2 kişi aynı anda patladı)
                    winner_user = current_player_user  # Veya None/Berabere

                game.status = 'finished'
                game.winner = winner_user
        return
    def _count_player_pieces(self,board_state, player_username):
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
    
    def check_and_get_eliminated_players(self, game):
        """
        Tahtada hiç taşı kalmayan oyuncuları bulur ve döndürür.
        Returns: list of usernames who have no pieces left
        """
        eliminated = []
        board_state = game.board_state
        if not board_state:
            return eliminated
        
        # Tüm aktif oyuncuları al
        active_players = set(p.username for p in game.players.all())
        
        # Tahtada hala taşı olan oyuncuları bul
        players_with_pieces = set()
        for r_key, row in board_state.items():
            for c_key, cell in row.items():
                if cell and cell.get('owner'):
                    players_with_pieces.add(cell.get('owner'))
        
        # Tahtada taşı olmayan ama hala oyunda olan oyuncuları bul
        eliminated = list(active_players - players_with_pieces)
        
        return eliminated

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


dw = DiceWars()
class GameConsumer_DiceWars(AsyncJsonWebsocketConsumer):

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

            is_player = await self.is_user_in_game(self.game)

            # --- OTOMATİK KATILMA (DEĞİŞTİ) ---
            # 'add_player_and_start_game' artık oyunu BAŞLATMAYACAK, sadece ekleyecek.
            if self.game.status == 'waiting' and not self.game.is_full and not is_player:
                self.game = await self.add_player_to_game(self.game, self.user)
                # Odaya yeni katılanı duyur
                await self.broadcast_game_state(
                    self.game,
                    message=f"{self.user.username} oyuna katıldı."
                )
            else:
                # Odaya zaten katılmış olanlara mevcut durumu gönder
                await self.send_game_state_to_user(self.game)
        except Exception as e:
            print(f"HATA (connect): {e}")
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

        command_type = content.get('type')

        if command_type == 'make_move':
            await self.handle_make_move(content)

        elif command_type == 'start_game':
            await self.handle_start_game()

        elif command_type == 'kick_player':
            await self.handle_kick_player(content)

    # --- DEĞİŞEN FONKSİYON ---
    async def handle_make_move(self, content):
        try:
            game, is_valid_move, error_msg = await self.perform_initial_click(content)
            if not is_valid_move:
                await self.send_error(error_msg)
                return
            player_username = self.user.username
            await self.broadcast_game_state(game, message=f"{player_username} tıkladı.")
            await asyncio.sleep(0.1)

            reaction_happened = False
            while True:
                cells_to_explode = await self.find_critical_cells_async(game.board_state)
                if not cells_to_explode:
                    break
                reaction_happened = True
                await asyncio.sleep(0.6)
                game, exploded_cells_list = await self.apply_explosions(
                    game.game_id, cells_to_explode, player_username
                )
                await self.broadcast_game_state(game, exploded_cells=exploded_cells_list)

            final_game = None
            eliminated_players = []
            if reaction_happened:
                final_game, eliminated_players = await self.check_winner_and_change_turn(game.game_id, self.user)
            else:
                # Patlama olmadıysa, kazananı kontrol etme (Oyun bitmez)
                final_game, eliminated_players = await self.just_change_turn(game.game_id, self.user)

            await asyncio.sleep(0.6)
            
            # Elenmiş oyuncular varsa mesaj ekle
            elimination_message = None
            if eliminated_players:
                if len(eliminated_players) == 1:
                    elimination_message = f"❌ {eliminated_players[0]} elendi! Artık sıra almayacak."
                else:
                    elimination_message = f"❌ {', '.join(eliminated_players)} elendi! Artık sıra almayacaklar."
            
            if final_game.status == 'finished':
                await self.broadcast_game_state(
                    final_game, 
                    message="Oyun Bitti!",
                    eliminated_players=eliminated_players
                )
            else:
                turn_message = f"Sıra {final_game.current_turn.username} kullanıcısında."
                if elimination_message:
                    turn_message = f"{elimination_message} {turn_message}"
                await self.broadcast_game_state(
                    final_game,
                    message=turn_message,
                    eliminated_players=eliminated_players
                )
        except Exception as e:
            print(f"HATA (handle_make_move ASYNC): {e}")
            await self.send_error(f"Hamle yapılamadı: {e}")

    async def handle_start_game(self):
        game, message = await self._start_game_db()
        if not game:
            await self.send_error(message)
            return

        await self.broadcast_game_state(
            game,
            message=message,
            special_event='game_start_roll'  # Çark animasyonunu tetikle
        )
    async def handle_kick_player(self, content):
        username_to_kick = content.get('username_to_kick')
        if not username_to_kick:
            await self.send_error("Kullanıcı adı belirtilmedi.")
            return

        game, message = await self._kick_player_db(username_to_kick)

        if not game:
            await self.send_error(message)
            return

        # Herkese güncel oyuncu listesini gönder
        await self.broadcast_game_state(game, message=message)
    # --- Grup Yayını Metodları ---
    @database_sync_to_async
    def perform_initial_click(self, content):
        # ... (Bu fonksiyonunuz zaten doğru, değişiklik yok) ...
        with transaction.atomic():
            game = GameSession.objects.select_for_update().get(game_id=self.game_id)
            if game.status != 'in_progress':
                return game, False, "Oyun başlamadı veya bitti."
            if game.current_turn != self.user:
                return game, False, "Sıra sizde değil."

            row, col = content.get('row'), content.get('col')
            r_str, c_str = str(row), str(col)
            if r_str not in game.board_state:
                game.board_state[r_str] = {}
            cell = game.board_state[r_str].get(c_str)
            if cell is None:
                game.board_state[r_str][c_str] = {
                    'owner': self.user.username,
                    'count': 3
                }
            else:
                if cell.get('owner') != self.user.username:
                    return game, False, "Bu hücre rakibinize ait."
                cell['count'] += 1
            game.save()
            return game, True, ""

    @database_sync_to_async
    def just_change_turn(self, game_id, user):
        with transaction.atomic():
            game = GameSession.objects.get(game_id=game_id)
            if game.status == 'in_progress':
                players_list = list(game.players.all())
                if user in players_list:
                    current_turn_index = players_list.index(user)
                    next_turn_index = (current_turn_index + 1) % len(players_list)
                    game.current_turn = players_list[next_turn_index]
            game.save()
            return game

    @database_sync_to_async
    def find_critical_cells_async(self, board_state):
        return dw.find_critical_cells(board_state)

    @database_sync_to_async
    def _start_game_db(self):
        game = GameSession.objects.select_related('game_type').get(game_id=self.game_id)

        if self.user != game.host:
            return None, "Oyunu sadece kurucu başlatabilir."
        if game.status != 'waiting':
            return None, "Oyun zaten başladı."
        if game.players.count() < game.game_type.min_players:
            return None, f"Oyunu başlatmak için en az {game.game_type.min_players} oyuncu gerekiyor."

        # --- Başlatma Mantığı ---
        game.status = 'in_progress'
        players_list = list(game.players.all())
        starter = random.choice(players_list)
        game.current_turn = starter

        # Tahta boyutunu gerçek oyuncu sayısına göre ayarla
        player_count = game.players.count()
        if player_count <= 2:
            game.board_size = 5
        elif player_count == 3:
            game.board_size = 6
        else:  # 4+
            game.board_size = 7

        game.save()
        return game, f"Oyun başladı! {starter.username} başlıyor."

    @database_sync_to_async
    def apply_explosions(self, game_id, cells_to_explode, player_username):
        # ... (Değişiklik yok) ...
        with transaction.atomic():
            game = GameSession.objects.get(game_id=game_id)
            for r, c in cells_to_explode:
                dw.bum(game, r, c, player_username)
            game.save()
            return game, cells_to_explode

    @database_sync_to_async
    def _kick_player_db(self, username_to_kick):
        game = GameSession.objects.get(game_id=self.game_id)
        if self.user != game.host:
            return None, "Sadece kurucu oyuncu atabilir."
        if game.status != 'waiting':
            return None, "Oyun başladıktan sonra kimseyi atamazsınız."
        if self.user.username == username_to_kick:
            return None, "Kendinizi atamazsınız."

        try:
            user_to_kick = User.objects.get(username=username_to_kick)
            game.players.remove(user_to_kick)
            game.save()
            return game, f"{username_to_kick} oyundan atıldı."
        except User.DoesNotExist:
            return None, "Kullanıcı bulunamadı."
        except Exception as e:
            return None, f"Hata: {e}"

    @database_sync_to_async
    def check_winner_and_change_turn(self, game_id, user):
        """
        Kazananı KONTROL EDER, elenmiş oyuncuları kontrol eder ve sırayı değiştirir.
        Returns: (game, eliminated_players_list)
        """
        with transaction.atomic():
            game = GameSession.objects.get(game_id=game_id)

            # --- ELENMİŞ OYUNCULARI KONTROL ET ---
            eliminated_usernames = dw.check_and_get_eliminated_players(game)
            eliminated_players = []
            
            if eliminated_usernames:
                # Elenmiş oyuncuları User objelerine çevir
                for username in eliminated_usernames:
                    try:
                        eliminated_user = User.objects.get(username=username)
                        eliminated_players.append(eliminated_user)
                        # Oyuncuyu players listesinden çıkar (artık sıra almayacak)
                        game.players.remove(eliminated_user)
                    except User.DoesNotExist:
                        pass

            # --- KAZANAN KONTROLÜ ---
            try:
                dw.check_for_winner(game, user)
            except TypeError:
                dw.check_for_winner(game, user)

            # --- SIRAYI DEĞİŞTİR (Elenmiş oyuncuları atla) ---
            if game.status != 'finished':
                players_list = list(game.players.all())
                if players_list:  # Hala oyuncu varsa
                    try:
                        current_turn_index = players_list.index(user)
                        # Sonraki oyuncuyu bul (elenmiş oyuncuları atla)
                        next_turn_index = (current_turn_index + 1) % len(players_list)
                        game.current_turn = players_list[next_turn_index]
                    except ValueError:
                        # Eğer mevcut oyuncu listede yoksa (elenmiş olabilir), ilk oyuncuyu al
                        if players_list:
                            game.current_turn = players_list[0]
                else:
                    # Hiç oyuncu kalmadıysa oyunu bitir
                    game.status = 'finished'

            game.save()
            return game, eliminated_usernames

    # --- YENİ YARDIMCI FONKSİYON ---
    @database_sync_to_async
    def just_change_turn(self, game_id, user):
        """
        Kazananı KONTROL ETMEDEN sadece sırayı değiştirir.
        Elenmiş oyuncuları kontrol eder ve atlar.
        Returns: (game, eliminated_players_list)
        """
        with transaction.atomic():
            game = GameSession.objects.get(game_id=game_id)

            # --- ELENMİŞ OYUNCULARI KONTROL ET ---
            eliminated_usernames = dw.check_and_get_eliminated_players(game)
            eliminated_players = []
            
            if eliminated_usernames:
                # Elenmiş oyuncuları User objelerine çevir
                for username in eliminated_usernames:
                    try:
                        eliminated_user = User.objects.get(username=username)
                        eliminated_players.append(eliminated_user)
                        # Oyuncuyu players listesinden çıkar (artık sıra almayacak)
                        game.players.remove(eliminated_user)
                    except User.DoesNotExist:
                        pass

            if game.status == 'in_progress':  # Sadece oyun sürüyorsa
                players_list = list(game.players.all())
                if players_list:  # Hala oyuncu varsa
                    if user in players_list:
                        current_turn_index = players_list.index(user)
                        next_turn_index = (current_turn_index + 1) % len(players_list)
                        game.current_turn = players_list[next_turn_index]
                    else:
                        # Eğer mevcut oyuncu listede yoksa (elenmiş olabilir), ilk oyuncuyu al
                        game.current_turn = players_list[0]
                else:
                    # Hiç oyuncu kalmadıysa oyunu bitir
                    game.status = 'finished'

            game.save()
            return game, eliminated_usernames

    async def broadcast_game_state(self, game, message=None, exploded_cells=None, special_event=None, eliminated_players=None):
        state_data = await self.get_game_state_data_async(game)
        state_data['message'] = message
        state_data['exploded_cells'] = exploded_cells if exploded_cells else []
        state_data['special_event'] = special_event # 'start_game' için eklendi
        state_data['eliminated_players'] = eliminated_players if eliminated_players else []
        await self.channel_layer.group_send(self.game_group_name, state_data)

    def broadcast_game_state_sync(self, game, message=None, exploded_cells=None):
        # ... (Değişiklik yok) ...
        state_data = self.get_game_state_data_sync(game)
        state_data['message'] = message
        state_data['exploded_cells'] = exploded_cells if exploded_cells else []
        async_to_sync(self.channel_layer.group_send)(self.game_group_name, state_data)

    async def game_state(self, event):
        # ... (Değişiklik yok) ...
        await self.send_json(event)

    async def send_error(self, message):
        # ... (Değişiklik yok) ...
        await self.send_json({'type': 'error', 'message': message})

    def send_error_to_user(self, message):
        # ... (Değişiklik yok) ...
        async_to_sync(self.send_json)({'type': 'error', 'message': message})

    # --- Veritabanı (Sync/Async) Metodları ---
    @database_sync_to_async
    def get_game(self, game_id):
        # ... (Değişiklik yok) ...
        try:
            return GameSession.objects.select_related(
                'game_type', 'host', 'current_turn', 'winner'
            ).prefetch_related('players').get(game_id=self.game_id)
        except GameSession.DoesNotExist:
            return None

    @database_sync_to_async
    def is_user_in_game(self, game):
        # ... (Değişiklik yok) ...
        return game.players.filter(id=self.user.id).exists()

    @database_sync_to_async
    def add_player_to_game(self, game, user):
        """
        Sadece oyuncuyu ekler, oyunu BAŞLATMAZ.
        """
        with transaction.atomic():
            game_with_lock = GameSession.objects.select_for_update().get(game_id=game.id)
            if game_with_lock.is_full or game_with_lock.status != 'waiting':
                return game_with_lock

            game_with_lock.players.add(user)
            game_with_lock.save()
            return game_with_lock

    @database_sync_to_async
    def get_game_state_data_async(self, game_obj):
        # ... (Değişiklik yok) ...
        return self.get_game_state_data_sync(game_obj)

    def get_game_state_data_sync(self, game_obj):
        # ... (Bu fonksiyonunuz zaten doğru, değişiklik yok) ...
        players_list = list(game_obj.players.all())
        player_usernames = [p.username for p in players_list]
        return {
            'type': 'game_state',
            'state': game_obj.board_state,
            'turn': game_obj.current_turn.username if game_obj.current_turn else None,
            'players': player_usernames,
            'status': game_obj.status,
            'winner': game_obj.winner.username if game_obj.winner else None,
            'board_size': game_obj.board_size,
        }

    async def send_game_state_to_user(self, game_obj):
        # ... (Değişiklik yok) ...
        state_data = await self.get_game_state_data_async(game_obj)
        await self.send_json(state_data)