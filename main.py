from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import math
import copy
import random
import json


# ==========================================
# 核心游戏引擎 (2D, 3D Normal, 3D Melt 保持不变)
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


# ==========================================
# ★ 支持难度分级的智能 AI 大脑 ★
# ==========================================
class AI:
    def __init__(self, mode, size, difficulty="MEDIUM"):
        self.mode = mode
        self.size = size
        self.difficulty = difficulty

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

        hu_player = -player
        scored_moves = []

        # 1. 基础评分阶段
        for x, y, z in moves:
            if self.mode in ['2D', '3D_NORMAL']:
                ai_score = self._evaluate_point_normal(board, x, y, z, player)
                hu_score = self._evaluate_point_normal(board, x, y, z, hu_player)

                if ai_score >= 100000: return {"x": x, "y": y, "z": z}  # 己方绝杀，所有难度立刻执行

                # 简单难度：有 30% 的概率瞎眼忽略对方的绝杀威胁
                if self.difficulty == 'EASY' and random.random() < 0.3: hu_score = 0

                if hu_score >= 100000:
                    total_score = 90000 + ai_score
                else:
                    total_score = ai_score + hu_score * 1.2

                total_score += -((x - self.size // 2) ** 2 + (y - self.size // 2) ** 2 + (
                            z - (0 if self.mode == '2D' else self.size // 2)) ** 2) * 0.1 + random.uniform(0, 2)
                scored_moves.append((total_score, (x, y, z)))

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

                # 简单难度：有 30% 概率忽略对方融解得分的风险
                if self.difficulty == 'EASY' and random.random() < 0.3: hu_scored = False

                if hu_scored:
                    total_score = 50000
                else:
                    total_score = self._evaluate_point_melt(board, x, y, z, player) + self._evaluate_point_melt(board,
                                                                                                                x, y, z,
                                                                                                                hu_player) * 1.1
                    total_score += -((x - 7) ** 2 + (y - 7) ** 2 + (z - 7) ** 2) * 0.1 + random.uniform(0, 2)
                scored_moves.append((total_score, (x, y, z)))

        scored_moves.sort(key=lambda item: item[0], reverse=True)

        # 2. 难度梯级反馈阶段
        if self.difficulty == 'EASY':
            # 简单：在前 30% 的可行解中随机挑一个，模拟人类的不完美决策
            pool_size = max(1, int(len(scored_moves) * 0.3))
            m = random.choice(scored_moves[:pool_size])[1]
            return {"x": m[0], "y": m[1], "z": m[2]}

        if self.difficulty == 'MEDIUM' or scored_moves[0][0] >= 50000:
            # 中等：或触发了紧急拦截/绝杀，直接走最优解
            m = scored_moves[0][1]
            return {"x": m[0], "y": m[1], "z": m[2]}

        if self.difficulty == 'HARD':
            # 困难：预判 Minimax 深度 2 搜索 (过滤前 5 个最优点，看对手是否有致命反击)
            best_hard_move = None
            max_hard_score = -math.inf

            for base_score, (x, y, z) in scored_moves[:5]:
                backup_grid, backup_scores = copy.deepcopy(board.grid), board.scores.copy()
                board.grid[z][y][x] = player
                if self.mode == '3D_MELT': board._process_chains()

                opp_moves = board.get_candidate_moves()
                opp_max_score = 0
                # 模拟对手最佳回应 (只评估对手前 15 步)
                for ox, oy, oz in opp_moves[:15]:
                    if self.mode in ['2D', '3D_NORMAL']:
                        s = self._evaluate_point_normal(board, ox, oy, oz, hu_player)
                        if s > opp_max_score: opp_max_score = s
                    elif self.mode == '3D_MELT':
                        s = self._evaluate_point_melt(board, ox, oy, oz, hu_player)
                        if s > opp_max_score: opp_max_score = s

                board.grid, board.scores = backup_grid, backup_scores

                # 当前收益减去对手可能得到的最大收益
                hard_score = base_score - opp_max_score * 0.85
                if hard_score > max_hard_score:
                    max_hard_score = hard_score
                    best_hard_move = (x, y, z)

            m = best_hard_move or scored_moves[0][1]
            return {"x": m[0], "y": m[1], "z": m[2]}


# ==========================================
# FastAPI 后端与 API
# ==========================================
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

game_session = {"board": None, "ai": None, "mode": "2D"}
snake_records = []


# ★ 更新 Request 接收难度参数
class InitRequest(BaseModel): mode: str; difficulty: str


class PlayRequest(BaseModel): x: int; y: int; z: int; player: int


class AIRequest(BaseModel): player: int


class SnakeRecord(BaseModel): speed: int; score: int


@app.get("/")
def serve_frontend(): return FileResponse("static/index.html")


@app.post("/api/init")
def init_game(req: InitRequest):
    game_session["mode"] = req.mode
    if req.mode == '2D':
        game_session["board"] = Board2D(15); game_session["ai"] = AI(req.mode, 15, req.difficulty)
    elif req.mode == '3D_NORMAL':
        game_session["board"] = Board3DNormal(10); game_session["ai"] = AI(req.mode, 10, req.difficulty)
    elif req.mode == '3D_MELT':
        game_session["board"] = Board3DMelt(15); game_session["ai"] = AI(req.mode, 15, req.difficulty)
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


# --- 贪吃蛇 API ---
@app.post("/api/snake/record")
def add_snake_record(req: SnakeRecord):
    snake_records.append({"speed": req.speed, "score": req.score})
    snake_records.sort(key=lambda x: x["score"], reverse=True)
    if len(snake_records) > 10: snake_records.pop()
    return {"success": True}


@app.get("/api/snake/history")
def get_snake_history(): return {"history": snake_records}


# --- WebSocket 联机管理与观战/聊天系统 ---
class ConnectionManager:
    def __init__(self):
        self.rooms = {}

    def get_or_create_room(self, room_id: str, mode: str):
        if room_id not in self.rooms:
            if mode == '2D':
                board = Board2D(15)
            elif mode == '3D_NORMAL':
                board = Board3DNormal(10)
            else:
                board = Board3DMelt(15)
            # 新增 spectators 集合来存放观众
            self.rooms[room_id] = {"mode": mode, "board": board, "players": {}, "spectators": set(), "turn": 1}
        return self.rooms[room_id]

    async def broadcast(self, room_id: str, message: dict):
        """核心广播函数：把消息同时发给房间里的玩家和观众"""
        if room_id not in self.rooms: return
        room = self.rooms[room_id]
        payload = json.dumps(message)

        # 广播给对局玩家
        for ws in list(room["players"].keys()):
            try:
                await ws.send_text(payload)
            except:
                pass

        # 广播给观众
        for ws in list(room["spectators"]):
            try:
                await ws.send_text(payload)
            except:
                room["spectators"].remove(ws)


manager = ConnectionManager()


@app.websocket("/ws/pvp/{room_id}/{mode}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, mode: str):
    await websocket.accept()
    room = manager.get_or_create_room(room_id, mode)

    # 身份分配逻辑：前两个进房间的是玩家 (1 和 -1)，后面的都是观众 (0)
    if len(room["players"]) == 0:
        assigned_color = 1
        room["players"][websocket] = assigned_color
        role_name = "黑方(先手)"
    elif len(room["players"]) == 1:
        assigned_color = -1
        room["players"][websocket] = assigned_color
        role_name = "白方(后手)"
    else:
        assigned_color = 0
        room["spectators"].add(websocket)
        role_name = "观战者"

    await websocket.send_text(json.dumps({
        "type": "connected",
        "color": assigned_color,
        "msg": f"成功加入房间 {room_id}，您的身份是：{role_name}"
    }))

    # 广播某人进入房间的消息
    await manager.broadcast(room_id, {
        "type": "chat_broadcast",
        "sender": "系统",
        "msg": f"[{role_name}] 进入了房间"
    })

    if len(room["players"]) == 2 and assigned_color != 0:
        await manager.broadcast(room_id, {
            "type": "start",
            "msg": "双方已就绪，比赛开始！",
            "state": room["board"].grid,
            "turn": room["turn"]
        })
    elif assigned_color == 0:
        # 观众一进来，立刻给他同步当前棋盘状态
        await websocket.send_text(json.dumps({
            "type": "update",
            "state": room["board"].grid,
            "scores": room["board"].scores,
            "lastMove": room["board"].history[-1][2] if room["board"].history else None,
            "turn": room["turn"],
            "isWin": False, "winner": 0
        }))

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            # --- 聊天广播逻辑 ---
            if payload["action"] == "chat":
                # 确定发送者的身份
                if websocket in room["players"]:
                    sender_name = "黑方" if room["players"][websocket] == 1 else "白方"
                else:
                    sender_name = f"观众_{str(id(websocket))[-4:]}"

                await manager.broadcast(room_id, {
                    "type": "chat_broadcast",
                    "sender": sender_name,
                    "msg": payload["msg"]
                })

            # --- 落子逻辑 ---
            elif payload["action"] == "play":
                if assigned_color == 0: continue  # 观众不能下棋
                if len(room["players"]) < 2:
                    await websocket.send_text(json.dumps({"type": "info", "msg": "等待对手..."}))
                    continue
                if room["turn"] != assigned_color: continue

                x, y, z = payload["x"], payload["y"], payload["z"]
                b = room["board"]
                if b.place_piece(x, y, z, assigned_color):
                    is_win = b.check_win(assigned_color)
                    if not is_win: room["turn"] = -assigned_color

                    # 状态更新广播给所有人
                    await manager.broadcast(room_id, {
                        "type": "update", "state": b.grid, "scores": b.scores,
                        "lastMove": {"x": x, "y": y, "z": z}, "turn": room["turn"],
                        "isWin": is_win, "winner": assigned_color if is_win else 0
                    })

    except WebSocketDisconnect:
        # 离开房间的清理逻辑
        if websocket in room["players"]:
            del room["players"][websocket]
            left_role = "黑方" if assigned_color == 1 else "白方"
            await manager.broadcast(room_id, {"type": "opponent_left", "msg": f"{left_role} 逃跑了！对局强行终止。"})
        elif websocket in room["spectators"]:
            room["spectators"].remove(websocket)
            await manager.broadcast(room_id,
                                    {"type": "chat_broadcast", "sender": "系统", "msg": f"一位观战者离开了房间"})

        if len(room["players"]) == 0 and len(room["spectators"]) == 0:
            if room_id in manager.rooms: del manager.rooms[room_id]