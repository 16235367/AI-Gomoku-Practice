from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List
import math
import copy
import random
import json


# ==========================================
# 核心游戏引擎与 AI 算法 (保持极速与高智商)
# ==========================================
class Board2D:
    def __init__(self, size=15):
        self.size = size
        self.grid = [[[0] * size for _ in range(size)] for _ in range(1)]
        self.history, self.scores = [], {1: 0, -1: 0}

    def place_piece(self, x, y, z, player):
        if self.grid[0][y][x] == 0:
            self.history.append((copy.deepcopy(self.grid), self.scores.copy(), {"x": x, "y": y, "z": 0}))
            self.grid[0][y][x] = player
            return True
        return False

    def undo(self):
        if self.history:
            self.grid, self.scores, _ = self.history.pop()
            return True
        return False

    def check_win(self, player):
        dirs = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for y in range(self.size):
            for x in range(self.size):
                if self.grid[0][y][x] == player:
                    for dx, dy in dirs:
                        count, nx, ny = 1, x + dx, y + dy
                        while 0 <= nx < self.size and 0 <= ny < self.size and self.grid[0][ny][nx] == player:
                            count += 1;
                            nx += dx;
                            ny += dy
                        if count >= 5: return True
        return False

    def get_candidate_moves(self):
        moves = []
        for y in range(self.size):
            for x in range(self.size):
                if self.grid[0][y][x] != 0:
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < self.size and 0 <= ny < self.size and self.grid[0][ny][nx] == 0:
                                if (nx, ny, 0) not in moves: moves.append((nx, ny, 0))
        return moves


class Board3DNormal(Board2D):
    def __init__(self, size=10):
        self.size = size
        self.grid = [[[0] * size for _ in range(size)] for _ in range(size)]
        self.history, self.scores = [], {1: 0, -1: 0}

    def place_piece(self, x, y, z, player):
        if self.grid[z][y][x] == 0:
            self.history.append((copy.deepcopy(self.grid), self.scores.copy(), {"x": x, "y": y, "z": z}))
            self.grid[z][y][x] = player
            return True
        return False

    def check_win(self, player):
        dirs = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (0, 1, 1), (0, 1, -1),
                (1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1)]
        for z in range(self.size):
            for y in range(self.size):
                for x in range(self.size):
                    if self.grid[z][y][x] == player:
                        for dx, dy, dz in dirs:
                            count, nx, ny, nz = 1, x + dx, y + dy, z + dz
                            while 0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size and \
                                    self.grid[nz][ny][nx] == player:
                                count += 1;
                                nx += dx;
                                ny += dy;
                                nz += dz
                            if count >= 5: return True
        return False

    def get_candidate_moves(self):
        moves = []
        for z in range(self.size):
            for y in range(self.size):
                for x in range(self.size):
                    if self.grid[z][y][x] != 0:
                        for dz in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                for dx in [-1, 0, 1]:
                                    nx, ny, nz = x + dx, y + dy, z + dz
                                    if 0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size and \
                                            self.grid[nz][ny][nx] == 0:
                                        if (nx, ny, nz) not in moves: moves.append((nx, ny, nz))
        return moves


class Board3DMelt(Board3DNormal):
    def __init__(self, size=15):
        super().__init__(size)

    def place_piece(self, x, y, z, player):
        if self.grid[z][y][x] == 0:
            self.history.append((copy.deepcopy(self.grid), self.scores.copy(), {"x": x, "y": y, "z": z}))
            self.grid[z][y][x] = player
            self._process_chains()
            return True
        return False

    def _process_chains(self):
        dirs = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (0, 1, 1), (0, 1, -1),
                (1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1)]
        changes_to_rock, changes_to_empty = set(), set()
        for z in range(self.size):
            for y in range(self.size):
                for x in range(self.size):
                    for dx, dy, dz in dirs:
                        chain, valid = [], True
                        for i in range(5):
                            nx, ny, nz = x + dx * i, y + dy * i, z + dz * i
                            if 0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size:
                                st = self.grid[nz][ny][nx]
                                if st in [1, -1]:
                                    chain.append((nx, ny, nz, st))
                                else:
                                    valid = False; break
                            else:
                                valid = False; break
                        if valid and len(chain) == 5:
                            c_b = sum(1 for c in chain if c[3] == 1)
                            c_w = 5 - c_b
                            if c_b == 5 or c_w == 5:
                                for c in chain: changes_to_rock.add((c[0], c[1], c[2]))
                            else:
                                self.scores[1 if c_b > c_w else -1] += 1
                                for c in chain: changes_to_empty.add((c[0], c[1], c[2]))
        for cx, cy, cz in changes_to_rock: self.grid[cz][cy][cx] = 2
        for cx, cy, cz in changes_to_empty: self.grid[cz][cy][cx] = 0

    def check_win(self, player):
        return self.scores[player] >= 5


class AI:
    def __init__(self, mode, size):
        self.mode = mode;
        self.size = size

    def _evaluate_point_normal(self, board, x, y, z, player):
        score = 0
        dirs = [(1, 0, 0), (0, 1, 0), (1, 1, 0), (1, -1, 0)] if self.mode == '2D' else [(1, 0, 0), (0, 1, 0), (0, 0, 1),
                                                                                        (1, 1, 0), (1, -1, 0),
                                                                                        (1, 0, 1), (1, 0, -1),
                                                                                        (0, 1, 1), (0, 1, -1),
                                                                                        (1, 1, 1), (1, 1, -1),
                                                                                        (1, -1, 1), (-1, 1, 1)]
        for dx, dy, dz in dirs:
            f_count, f_blocked = 0, False
            nx, ny, nz = x + dx, y + dy, z + dz
            while 0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size:
                if board.grid[nz][ny][nx] == player:
                    f_count += 1; nx += dx; ny += dy; nz += dz
                elif board.grid[nz][ny][nx] == 0:
                    break
                else:
                    f_blocked = True; break
            if not (0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size): f_blocked = True
            b_count, b_blocked = 0, False
            nx, ny, nz = x - dx, y - dy, z - dz
            while 0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size:
                if board.grid[nz][ny][nx] == player:
                    b_count += 1; nx -= dx; ny -= dy; nz -= dz
                elif board.grid[nz][ny][nx] == 0:
                    break
                else:
                    b_blocked = True; break
            if not (0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size): b_blocked = True
            total, blocks = 1 + f_count + b_count, (1 if f_blocked else 0) + (1 if b_blocked else 0)
            if total >= 5:
                score += 100000
            elif total == 4:
                score += 10000 if blocks == 0 else 2000
            elif total == 3:
                score += 2000 if blocks == 0 else 200
            elif total == 2:
                score += 200 if blocks == 0 else 10
            elif total == 1:
                score += 10 if blocks == 0 else 0
        return score

    def _evaluate_point_melt(self, board, x, y, z, player):
        hu_player, score = -player, 0
        dirs = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (0, 1, 1), (0, 1, -1),
                (1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1)]
        for dx, dy, dz in dirs:
            for offset in range(-4, 1):
                window, valid = [], True
                for i in range(5):
                    nx, ny, nz = x + dx * (offset + i), y + dy * (offset + i), z + dz * (offset + i)
                    if 0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size:
                        st = player if i == -offset else board.grid[nz][ny][nx]
                        if st in [1, -1, 0]:
                            window.append(st)
                        else:
                            valid = False; break
                    else:
                        valid = False; break
                if valid and len(window) == 5:
                    c_ai, c_hu = window.count(player), window.count(hu_player)
                    if c_ai == 3 and c_hu == 1:
                        score += 500
                    elif c_ai == 2 and c_hu == 1:
                        score += 100
                    elif c_ai == 1 and c_hu == 1:
                        score += 10
                    elif c_ai == 2 and c_hu == 2:
                        score -= 1000
                    elif c_ai == 1 and c_hu == 3:
                        score -= 1000
                    elif c_hu == 4 and c_ai == 1:
                        score += 200
        return score

    def get_best_move(self, board, player):
        moves = board.get_candidate_moves()
        if not moves: return {"x": self.size // 2, "y": self.size // 2, "z": 0 if self.mode == '2D' else self.size // 2}
        best_move, max_score, hu_player = None, -math.inf, -player
        for x, y, z in moves:
            if self.mode in ['2D', '3D_NORMAL']:
                ai_score = self._evaluate_point_normal(board, x, y, z, player)
                hu_score = self._evaluate_point_normal(board, x, y, z, hu_player)
                if ai_score >= 100000: return {"x": x, "y": y, "z": z}
                if hu_score >= 100000:
                    total_score = 90000 + ai_score
                else:
                    total_score = ai_score + hu_score * 1.2
                total_score += -((x - self.size // 2) ** 2 + (y - self.size // 2) ** 2 + (
                            z - (0 if self.mode == '2D' else self.size // 2)) ** 2) * 0.1 + random.uniform(0, 2)
                if total_score > max_score: max_score, best_move = total_score, (x, y, z)
            elif self.mode == '3D_MELT':
                orig_grid, orig_scores = copy.deepcopy(board.grid), board.scores.copy()
                board.grid[z][y][x] = player
                board._process_chains()
                if board.scores[player] > orig_scores[player]:
                    board.grid, board.scores = orig_grid, orig_scores;
                    return {"x": x, "y": y, "z": z}
                board.grid, board.scores = copy.deepcopy(orig_grid), orig_scores.copy()
                board.grid[z][y][x] = hu_player
                board._process_chains()
                hu_scored = board.scores[hu_player] > orig_scores[hu_player]
                board.grid, board.scores = orig_grid, orig_scores
                if hu_scored:
                    total_score = 50000
                else:
                    total_score = self._evaluate_point_melt(board, x, y, z, player) + self._evaluate_point_melt(board,
                                                                                                                x, y, z,
                                                                                                                hu_player) * 1.1
                    total_score += -((x - 7) ** 2 + (y - 7) ** 2 + (z - 7) ** 2) * 0.1 + random.uniform(0, 2)
                if total_score > max_score: max_score, best_move = total_score, (x, y, z)
        m = best_move or moves[0]
        return {"x": m[0], "y": m[1], "z": m[2]}


# ==========================================
# FastAPI 后端与 WebSocket 联机对战大厅
# ==========================================
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# HTTP 模式状态 (AI 对战)
game_session = {"board": None, "ai": None, "mode": "2D"}


class InitRequest(BaseModel): mode: str


class PlayRequest(BaseModel): x: int; y: int; z: int; player: int


class AIRequest(BaseModel): player: int


@app.get("/")
def serve_frontend(): return FileResponse("static/index.html")


@app.post("/api/init")
def init_game(req: InitRequest):
    game_session["mode"] = req.mode
    if req.mode == '2D':
        game_session["board"] = Board2D(15); game_session["ai"] = AI(req.mode, 15)
    elif req.mode == '3D_NORMAL':
        game_session["board"] = Board3DNormal(10); game_session["ai"] = AI(req.mode, 10)
    elif req.mode == '3D_MELT':
        game_session["board"] = Board3DMelt(15); game_session["ai"] = AI(req.mode, 15)
    return {"success": True}


@app.post("/api/play")
def play_piece(req: PlayRequest):
    b = game_session["board"]
    success = b.place_piece(req.x, req.y, req.z, req.player)
    return {"success": success, "isWin": b.check_win(req.player) if success else False, "state": b.grid,
            "scores": b.scores, "lastMove": b.history[-1][2] if b.history else None}


@app.post("/api/ai_play")
def ai_play(req: AIRequest):
    b, ai = game_session["board"], game_session["ai"]
    move = ai.get_best_move(b, req.player)
    success = b.place_piece(move["x"], move["y"], move["z"], req.player)
    return {"success": success, "isWin": b.check_win(req.player) if success else False, "state": b.grid,
            "scores": b.scores, "move": move, "lastMove": b.history[-1][2] if b.history else None}


@app.post("/api/undo")
def undo_move():
    b = game_session["board"]
    success = b.undo()
    return {"success": success, "state": b.grid if success else [], "scores": b.scores if success else {},
            "lastMove": b.history[-1][2] if b.history else None}


# --- WebSocket 联机大厅管理 ---
class ConnectionManager:
    def __init__(self):
        # rooms 结构: { room_id: { "mode": "2D", "board": Board, "players": { websocket1: 1, websocket2: -1 }, "turn": 1 } }
        self.rooms = {}

    def get_or_create_room(self, room_id: str, mode: str):
        if room_id not in self.rooms:
            if mode == '2D':
                board = Board2D(15)
            elif mode == '3D_NORMAL':
                board = Board3DNormal(10)
            else:
                board = Board3DMelt(15)
            self.rooms[room_id] = {"mode": mode, "board": board, "players": {}, "turn": 1}
        return self.rooms[room_id]


manager = ConnectionManager()


@app.websocket("/ws/pvp/{room_id}/{mode}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, mode: str):
    await websocket.accept()
    room = manager.get_or_create_room(room_id, mode)

    if len(room["players"]) >= 2:
        await websocket.send_text(json.dumps({"type": "error", "msg": "房间已满"}))
        await websocket.close()
        return

    # 分配阵营：第一个进房间的执黑(1)，第二个执白(-1)
    assigned_color = 1 if len(room["players"]) == 0 else -1
    room["players"][websocket] = assigned_color

    await websocket.send_text(json.dumps({"type": "connected", "color": assigned_color,
                                          "msg": f"成功加入房间 {room_id}，您是{'黑棋(先手)' if assigned_color == 1 else '白棋(后手)'}"}))

    # 如果满两人，通知双方游戏开始
    if len(room["players"]) == 2:
        for ws in room["players"]:
            await ws.send_text(json.dumps({
                "type": "start",
                "msg": "对手已连接，游戏开始！",
                "state": room["board"].grid,
                "turn": room["turn"]
            }))

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            if payload["action"] == "play":
                if len(room["players"]) < 2:
                    await websocket.send_text(json.dumps({"type": "info", "msg": "请等待对手加入..."}))
                    continue
                if room["turn"] != assigned_color:
                    continue  # 不是你的回合

                x, y, z = payload["x"], payload["y"], payload["z"]
                b = room["board"]

                if b.place_piece(x, y, z, assigned_color):
                    is_win = b.check_win(assigned_color)
                    if not is_win:
                        room["turn"] = -assigned_color  # 切换回合

                    # 广播更新给房间内所有玩家
                    for ws in room["players"]:
                        await ws.send_text(json.dumps({
                            "type": "update",
                            "state": b.grid,
                            "scores": b.scores,
                            "lastMove": {"x": x, "y": y, "z": z},
                            "turn": room["turn"],
                            "isWin": is_win,
                            "winner": assigned_color if is_win else 0
                        }))

    except WebSocketDisconnect:
        if websocket in room["players"]:
            del room["players"][websocket]
        for ws in room["players"]:
            await ws.send_text(json.dumps({"type": "opponent_left", "msg": "对手已断开连接！"}))
        if len(room["players"]) == 0:
            del manager.rooms[room_id]  # 房间空了就销毁