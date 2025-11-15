import asyncio
import json
import logging
import random

from asgiref.sync import sync_to_async, async_to_sync
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext as _

from .models import GameSession
from django.utils import timezone

User = get_user_model()

from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer


def update_player_rankings(game, winner):
    """
    Oyun bittiğinde oyuncuların istatistiklerini günceller (sync).
    """
    with transaction.atomic():
        # Game'i yeniden yükle (fresh from DB)
        game = GameSession.objects.get(game_id=game.game_id)
        all_players = list(game.players.all())

        # Bu oyunun slug'ı (oyun bazlı istatistikler için key)
        game_slug = game.game_type.slug if game.game_type else "unknown"

        for player in all_players:
            # --- Global istatistikler ---
            player.total_games += 1
            if player == winner:
                player.total_wins += 1
                # Kazanan için global rank point (oyuncu sayısına göre)
                global_points = len(all_players) * 10
                player.rank_point += global_points
            else:
                player.total_losses += 1
                # Kaybeden için küçük bir bonus (oyuna katıldığı için)
                player.rank_point += 5

            # --- Oyun bazlı istatistikler (per_game_stats JSONField) ---
            stats = player.per_game_stats or {}
            game_stats = stats.get(game_slug, {
                "rank_point": 0,
                "wins": 0,
                "losses": 0,
                "games": 0,
            })

            game_stats["games"] += 1
            if player == winner:
                game_stats["wins"] += 1
                # Oyun bazlı rank point
                game_points = len(all_players) * 10
                game_stats["rank_point"] += game_points
            else:
                game_stats["losses"] += 1
                game_stats["rank_point"] += 5

            stats[game_slug] = game_stats
            player.per_game_stats = stats

            player.save()
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
                # Oyun bittiğinde sıralamayı güncelle
                game.finished_at = timezone.now()
                game.save()
                # Sıralama güncellemesini yap
                if winner_user:
                    update_player_rankings(game, winner_user)
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
        İlk tur tamamlanmadan elenme kontrolü yapmaz.
        Returns: list of usernames who have no pieces left
        """
        eliminated = []
        board_state = game.board_state
        if not board_state:
            return eliminated
        
        # İlk tur tamamlanmadan elenme kontrolü yapma
        # Her oyuncunun en az bir hamle yapması gerekir
        player_count = game.players.count()
        if game.move_count < player_count:
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
            "message": _("{username} joined the room.").format(username=event['username'])
        })

    # Üye ayrılışını bildir
    async def member_left(self, event):
        await self.send_json({
            "type": "system_notification",
            "event": "member_left",
            "sender_id": event["sender_id"],
            "username": event["username"],
            "message": _("{username} left the room.").format(username=event['username'])
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
                    message=_("{username} joined the game.").format(username=self.user.username)
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
            await self.send_error(_("You must be logged in."))
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
            move_row = content.get('row')
            move_col = content.get('col')
            await self.broadcast_game_state(
                game, 
                message=_("{username} made a move.").format(username=player_username),
                move_cell=[move_row, move_col] if move_row is not None and move_col is not None else None
            )
            await asyncio.sleep(0.1)

            reaction_happened = False
            while True:
                cells_to_explode = await self.find_critical_cells_async(game.board_state)
                if not cells_to_explode:
                    break
                reaction_happened = True
                
                # IMPORTANT: Broadcast current state with cells that WILL explode
                # This allows all players (including the one who started the reaction) to see explosions
                # on the current board BEFORE it's updated
                await self.broadcast_game_state(
                    game,
                    exploded_cells=cells_to_explode,  # Cells that WILL explode (for animation)
                    move_cell=None
                )
                await asyncio.sleep(0.25)  # Delay for explosion animation to show
                
                # Then apply the explosions and broadcast updated state
                game, exploded_cells_list = await self.apply_explosions(
                    game.game_id, cells_to_explode, player_username
                )
                # Broadcast updated board state (cells are now cleared)
                await self.broadcast_game_state(
                    game, 
                    exploded_cells=None,  # No explosions in this broadcast (already shown)
                    move_cell=None
                )
                await asyncio.sleep(0.1)  # Small delay between explosion rounds

            final_game = None
            eliminated_players = []
            if reaction_happened:
                final_game, eliminated_players = await self.check_winner_and_change_turn(game.game_id, self.user)
            else:
                # Patlama olmadıysa, kazananı kontrol etme (Oyun bitmez)
                final_game, eliminated_players = await self.just_change_turn(game.game_id, self.user)

            await asyncio.sleep(0.3)  # Faster turn change delay
            
            # Only show elimination message if there are NEW eliminations (not already shown)
            # Get previously eliminated players from the game state
            previous_eliminated = set(final_game.eliminated_players) if final_game.eliminated_players else set()
            new_eliminated = [p for p in eliminated_players if p not in previous_eliminated]
            
            elimination_message = None
            if new_eliminated:  # Only show message for NEW eliminations
                if len(new_eliminated) == 1:
                    elimination_message = _("❌ {player} eliminated! They will no longer take turns.").format(player=new_eliminated[0])
                else:
                    elimination_message = _("❌ {players} eliminated! They will no longer take turns.").format(players=', '.join(new_eliminated))
            
            if final_game.status == 'finished':
                await self.broadcast_game_state(
                    final_game, 
                    message=_("Game Over!"),
                    eliminated_players=eliminated_players,
                    move_cell=None
                )
            else:
                turn_message = _("Turn: {username}").format(username=final_game.current_turn.username)
                if elimination_message:
                    turn_message = f"{elimination_message} {turn_message}"
                await self.broadcast_game_state(
                    final_game,
                    message=turn_message,
                    eliminated_players=eliminated_players,
                    move_cell=None  # No move cell for turn change
                )
        except Exception as e:
            print(f"HATA (handle_make_move ASYNC): {e}")
            await self.send_error(_("Move could not be made: {error}").format(error=str(e)))

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
        """
        Hamle yapma fonksiyonu.
        İlk turda: Boş hücrelere yerleştirme yapılabilir
        Sonraki turlarda: Sadece kendi hücrelerini yükseltme yapılabilir
        """
        with transaction.atomic():
            game = GameSession.objects.select_for_update().get(game_id=self.game_id)
            if game.status != 'in_progress':
                return game, False, _("Game has not started or has ended.")
            if game.current_turn != self.user:
                return game, False, _("It is not your turn.")

            row, col = content.get('row'), content.get('col')
            r_str, c_str = str(row), str(col)
            if r_str not in game.board_state:
                game.board_state[r_str] = {}
            cell = game.board_state[r_str].get(c_str)
            
            player_count = game.players.count()
            is_first_round = game.move_count < player_count
            
            if cell is None:
                # Boş hücreye tıklama
                if is_first_round:
                    # İlk turda: Boş hücrelere yerleştirme yapılabilir
                    game.board_state[r_str][c_str] = {
                        'owner': self.user.username,
                        'count': 3
                    }
                else:
                    # Sonraki turlarda: Boş hücrelere yerleştirme yapılamaz
                    return game, False, _("After the first round, you can only upgrade your own cells.")
            else:
                # Dolu hücreye tıklama
                if cell.get('owner') != self.user.username:
                    return game, False, _("This cell belongs to your opponent.")
                # Kendi hücresini yükselt
                cell['count'] += 1
            
            # Hamle sayısını artır
            game.move_count += 1
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
            return None, _("Only the host can start the game.")
        if game.status != 'waiting':
            return None, _("Game has already started.")
        if game.players.count() < game.game_type.min_players:
            return None, _("At least {min_players} players are required to start the game.").format(min_players=game.game_type.min_players)

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

        # Hamle sayacını sıfırla (ilk tur için)
        game.move_count = 0
        game.save()
        return game, _("Game started! {username} begins.").format(username=starter.username)

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
            return None, _("Only the host can kick players.")
        if game.status != 'waiting':
            return None, _("You cannot kick anyone after the game has started.")
        if self.user.username == username_to_kick:
            return None, _("You cannot kick yourself.")

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
                # Elenmiş oyuncuları JSON field'a ekle (players listesinden çıkarma)
                current_eliminated = list(game.eliminated_players) if game.eliminated_players else []
                for username in eliminated_usernames:
                    if username not in current_eliminated:
                        current_eliminated.append(username)
                        try:
                            eliminated_user = User.objects.get(username=username)
                            eliminated_players.append(eliminated_user)
                        except User.DoesNotExist:
                            pass
                game.eliminated_players = current_eliminated

            # --- KAZANAN KONTROLÜ ---
            try:
                dw.check_for_winner(game, user)
            except TypeError:
                dw.check_for_winner(game, user)

            # --- SIRAYI DEĞİŞTİR (Elenmiş oyuncuları atla) ---
            if game.status != 'finished':
                # Tüm oyuncuları al, ama elenmiş olanları filtrele
                all_players = list(game.players.all())
                eliminated_set = set(game.eliminated_players) if game.eliminated_players else set()
                active_players = [p for p in all_players if p.username not in eliminated_set]
                
                if active_players:  # Hala aktif oyuncu varsa
                    try:
                        current_turn_index = active_players.index(user)
                        # Sonraki aktif oyuncuyu bul
                        next_turn_index = (current_turn_index + 1) % len(active_players)
                        game.current_turn = active_players[next_turn_index]
                    except ValueError:
                        # Eğer mevcut oyuncu listede yoksa, ilk aktif oyuncuyu al
                        if active_players:
                            game.current_turn = active_players[0]
                else:
                    # Hiç aktif oyuncu kalmadıysa oyunu bitir
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
                # Elenmiş oyuncuları JSON field'a ekle (players listesinden çıkarma)
                current_eliminated = list(game.eliminated_players) if game.eliminated_players else []
                for username in eliminated_usernames:
                    if username not in current_eliminated:
                        current_eliminated.append(username)
                        try:
                            eliminated_user = User.objects.get(username=username)
                            eliminated_players.append(eliminated_user)
                        except User.DoesNotExist:
                            pass
                game.eliminated_players = current_eliminated

            if game.status == 'in_progress':  # Sadece oyun sürüyorsa
                # Tüm oyuncuları al, ama elenmiş olanları filtrele
                all_players = list(game.players.all())
                eliminated_set = set(game.eliminated_players) if game.eliminated_players else set()
                active_players = [p for p in all_players if p.username not in eliminated_set]
                
                if active_players:  # Hala aktif oyuncu varsa
                    if user in active_players:
                        current_turn_index = active_players.index(user)
                        next_turn_index = (current_turn_index + 1) % len(active_players)
                        game.current_turn = active_players[next_turn_index]
                    else:
                        # Eğer mevcut oyuncu listede yoksa, ilk aktif oyuncuyu al
                        if active_players:
                            game.current_turn = active_players[0]
                else:
                    # Hiç aktif oyuncu kalmadıysa oyunu bitir
                    game.status = 'finished'

            game.save()
            return game, eliminated_usernames

    async def broadcast_game_state(self, game, message=None, exploded_cells=None, special_event=None, eliminated_players=None, move_cell=None):
        state_data = await self.get_game_state_data_async(game)
        state_data['message'] = message
        state_data['exploded_cells'] = exploded_cells if exploded_cells else []
        state_data['special_event'] = special_event # 'start_game' için eklendi
        state_data['eliminated_players'] = eliminated_players if eliminated_players else []
        state_data['move_cell'] = move_cell  # [row, col] of the cell that was moved
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

    async def rematch_invite(self, event):
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
        eliminated_players = game_obj.eliminated_players if game_obj.eliminated_players else []
        return {
            'type': 'game_state',
            'state': game_obj.board_state,
            'turn': game_obj.current_turn.username if game_obj.current_turn else None,
            'players': player_usernames,
            'status': game_obj.status,
            'winner': game_obj.winner.username if game_obj.winner else None,
            'board_size': game_obj.board_size,
            'eliminated_players': eliminated_players,
        }

    async def send_game_state_to_user(self, game_obj):
        # ... (Değişiklik yok) ...
        state_data = await self.get_game_state_data_async(game_obj)
        await self.send_json(state_data)