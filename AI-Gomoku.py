import tkinter as tk
from tkinter import messagebox
import math
import random
import threading
import asyncio
import os
import edge_tts
import pygame


# ==========================================
# 模块1：核心逻辑模块
# ==========================================
class GomokuBoard:
    def __init__(self, size=15):
        self.size = size
        self.grid = [[0] * size for _ in range(size)]
        self.history = []

    def place_piece(self, r, c, player):
        if self.grid[r][c] == 0:
            self.grid[r][c] = player
            self.history.append((r, c))
            return True
        return False

    def undo_move(self):
        if self.history:
            r, c = self.history.pop()
            self.grid[r][c] = 0
            return True
        return False

    def check_win(self, r, c, player):
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            nr, nc = r + dr, c + dc
            while 0 <= nr < self.size and 0 <= nc < self.size and self.grid[nr][nc] == player:
                count += 1
                nr, nc = nr + dr, nc + dc
            nr, nc = r - dr, c - dc
            while 0 <= nr < self.size and 0 <= nc < self.size and self.grid[nr][nc] == player:
                count += 1
                nr, nc = nr - dr, nc - dc
            if count >= 5: return True
        return False

    def get_candidate_moves(self):
        moves = set()
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] != 0:
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < self.size and 0 <= nc < self.size and self.grid[nr][nc] == 0:
                                moves.add((nr, nc))
        return list(moves)


# ==========================================
# 模块2：AI语音情绪引擎 (升级为微软真神级 Neural TTS)
# ==========================================
class AIVoiceEngine:
    def __init__(self):
        self.is_speaking = False
        pygame.mixer.init()  # 初始化音频混音器

        # 语音角色设置：
        # "zh-CN-YunxiNeural" 是阳光青年男声（很有感情）
        # "zh-CN-XiaoxiaoNeural" 是知性女声
        self.voice_model = "zh-CN-YunxiNeural"
        self.temp_file = "ai_voice_temp.mp3"

        self.lines = {
            "random": [
                "这局棋有点意思。",
                "我的后台博弈树正在疯狂生长。",
                "看你犹豫的样子，是找不到破绽了吗？",
                "需要我让你的大脑休息一下吗？",
                "这步棋下得毫无波澜，你确定吗？"
            ],
            "ai_winning": [
                "在我的评估函数里，你的胜率已经跌破百分之一了。",
                "放弃吧，我的剪枝算法已经看到了结局。",
                "你的算力似乎跟不上我的节奏了。"
            ],
            "ai_losing": [
                "等等，刚才那步棋...我的算力好像低估了你！",
                "竟然绕过了我的启发式搜索，有点东西！",
                "我的防守权重没设置对吗？局势居然有点失控。",
                "不要高兴得太早，我的底层逻辑还能反杀。"
            ],
            "ai_win_game": [
                "这就是人工智能的纯粹算力，承让了！",
                "你的逻辑很强，但我的算法更胜一筹。"
            ],
            "human_win_game": [
                "我的处理器要烧了...恭喜你，人类赢了这次计算。",
                "算力竟然输给了直觉，这次算你厉害。"
            ]
        }

    def speak(self, text):
        if self.is_speaking:
            return
        threading.Thread(target=self._speak_thread, args=(text,), daemon=True).start()

    def _speak_thread(self, text):
        self.is_speaking = True
        try:
            # 1. 使用 asyncio 运行 edge-tts 生成音频文件
            async def generate_audio():
                # rate="+10%" 可以让语速稍微快一点，显得更聪明
                communicate = edge_tts.Communicate(text, self.voice_model, rate="+10%")
                await communicate.save(self.temp_file)

            asyncio.run(generate_audio())

            # 2. 使用 pygame 在后台静默播放，绝对不会卡死 Tkinter 界面
            pygame.mixer.music.load(self.temp_file)
            pygame.mixer.music.play()

            # 等待播放完成
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            # 3. 释放文件句柄
            pygame.mixer.music.unload()

        except Exception as e:
            print(f"语音引擎调用失败 (请检查网络): {e}")
        finally:
            self.is_speaking = False
            # 尝试删除临时文件
            if os.path.exists(self.temp_file):
                try:
                    os.remove(self.temp_file)
                except:
                    pass

    def trigger_context_voice(self, ai_score, is_game_over=False, winner=None):
        if is_game_over:
            if winner == "AI":
                self.speak(random.choice(self.lines["ai_win_game"]))
            elif winner == "Human":
                self.speak(random.choice(self.lines["human_win_game"]))
            return

        if random.random() > 0.3: return  # 30% 概率触发说话

        if ai_score > 3000:
            self.speak(random.choice(self.lines["ai_winning"]))
        elif ai_score < -2000:
            self.speak(random.choice(self.lines["ai_losing"]))
        else:
            self.speak(random.choice(self.lines["random"]))


# ==========================================
# 模块3：AI算法模块
# ==========================================
class GomokuAI:
    def __init__(self, board_size=15, depth=2):
        self.size = board_size
        self.depth = depth

    def evaluate_board(self, board, ai_player):
        score = 0
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for r in range(self.size):
            for c in range(self.size):
                if board[r][c] == 0: continue
                player = board[r][c]

                for dr, dc in directions:
                    prev_r, prev_c = r - dr, c - dc
                    if 0 <= prev_r < self.size and 0 <= prev_c < self.size and board[prev_r][prev_c] == player:
                        continue

                    count = 1
                    nr, nc = r + dr, c + dc
                    while 0 <= nr < self.size and 0 <= nc < self.size and board[nr][nc] == player:
                        count += 1
                        nr += dr
                        nc += dc

                    blocks = 0
                    if not (0 <= prev_r < self.size and 0 <= prev_c < self.size) or board[prev_r][prev_c] != 0:
                        blocks += 1
                    if not (0 <= nr < self.size and 0 <= nc < self.size) or board[nr][nc] != 0:
                        blocks += 1

                    pts = 0
                    if count >= 5:
                        pts = 100000
                    elif count == 4:
                        pts = 10000 if blocks == 0 else 1000
                    elif count == 3:
                        pts = 1000 if blocks == 0 else 100
                    elif count == 2:
                        pts = 100 if blocks == 0 else 10
                    elif count == 1:
                        pts = 10 if blocks == 0 else 0

                    if player == ai_player:
                        score += pts
                    else:
                        score -= pts * 2
        return score

    def minimax(self, board_obj, depth, alpha, beta, is_maximizing, ai_player):
        if depth == 0: return self.evaluate_board(board_obj.grid, ai_player)
        moves = board_obj.get_candidate_moves()
        if not moves: return 0
        human_player = -ai_player

        if is_maximizing:
            max_eval = -math.inf
            for r, c in moves:
                board_obj.grid[r][c] = ai_player
                if board_obj.check_win(r, c, ai_player):
                    board_obj.grid[r][c] = 0
                    return 100000 + depth

                eval = self.minimax(board_obj, depth - 1, alpha, beta, False, ai_player)
                board_obj.grid[r][c] = 0
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha: break
            return max_eval
        else:
            min_eval = math.inf
            for r, c in moves:
                board_obj.grid[r][c] = human_player
                if board_obj.check_win(r, c, human_player):
                    board_obj.grid[r][c] = 0
                    return -100000 - depth

                eval = self.minimax(board_obj, depth - 1, alpha, beta, True, ai_player)
                board_obj.grid[r][c] = 0
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha: break
            return min_eval

    def get_best_move(self, board_obj, ai_player):
        best_val = -math.inf
        best_move = None
        moves = board_obj.get_candidate_moves()
        if not moves: return (self.size // 2, self.size // 2)

        for r, c in moves:
            board_obj.grid[r][c] = ai_player
            if board_obj.check_win(r, c, ai_player):
                board_obj.grid[r][c] = 0
                return (r, c)
            move_val = self.minimax(board_obj, self.depth - 1, -math.inf, math.inf, False, ai_player)
            board_obj.grid[r][c] = 0
            if move_val > best_val:
                best_move = (r, c)
                best_val = move_val

        return best_move if best_move else moves[0]


# ==========================================
# 模块3：界面交互模块
# ==========================================
class GomokuGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI五子棋 - 软件综合实践")
        self.board_size = 15
        self.cell_size = 40
        self.margin = 30

        self.ai = GomokuAI(self.board_size, depth=2)
        self.voice = AIVoiceEngine()

        self.human_color = -1
        self.setup_ui()
        self.reset_game()

    def setup_ui(self):
        control_frame = tk.Frame(self.root)
        control_frame.pack(side=tk.TOP, pady=10)

        tk.Button(control_frame, text="重新开始(交替颜色)", command=self.reset_game).pack(side=tk.LEFT, padx=10)
        tk.Button(control_frame, text="悔棋", command=self.undo).pack(side=tk.LEFT, padx=10)

        self.status_var = tk.StringVar()
        tk.Label(control_frame, textvariable=self.status_var, font=("Arial", 12)).pack(side=tk.LEFT, padx=20)

        canvas_width = self.cell_size * (self.board_size - 1) + self.margin * 2
        self.canvas = tk.Canvas(self.root, width=canvas_width, height=canvas_width, bg="#E6C280")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)

    def draw_board(self):
        self.canvas.delete("all")
        for i in range(self.board_size):
            x = self.margin + i * self.cell_size
            self.canvas.create_line(x, self.margin, x, self.margin + (self.board_size - 1) * self.cell_size)
            y = self.margin + i * self.cell_size
            self.canvas.create_line(self.margin, y, self.margin + (self.board_size - 1) * self.cell_size, y)

        for r in range(self.board_size):
            for c in range(self.board_size):
                if self.game.grid[r][c] == 1:
                    self.draw_piece(r, c, "black")
                elif self.game.grid[r][c] == -1:
                    self.draw_piece(r, c, "white")

        if self.game.history:
            last_r, last_c = self.game.history[-1]
            x = self.margin + last_c * self.cell_size
            y = self.margin + last_r * self.cell_size
            r_indicator = self.cell_size * 0.15
            self.canvas.create_oval(x - r_indicator, y - r_indicator, x + r_indicator, y + r_indicator, fill="red",
                                    outline="red")

    def draw_piece(self, r, c, color):
        x = self.margin + c * self.cell_size
        y = self.margin + r * self.cell_size
        r_piece = self.cell_size * 0.4
        self.canvas.create_oval(x - r_piece, y - r_piece, x + r_piece, y + r_piece, fill=color, outline="grey")

    def on_click(self, event):
        if self.is_game_over or self.current_player != self.human_color: return

        c = round((event.x - self.margin) / self.cell_size)
        r = round((event.y - self.margin) / self.cell_size)

        if 0 <= r < self.board_size and 0 <= c < self.board_size:
            if self.game.place_piece(r, c, self.human_color):
                self.draw_board()
                if self.game.check_win(r, c, self.human_color):
                    self.game_over("恭喜！玩家获胜！", "Human")
                else:
                    self.current_player = self.ai_color
                    self.status_var.set("AI思考中...")
                    self.root.update()
                    self.root.after(100, self.ai_turn)

    def ai_turn(self):
        if self.is_game_over: return
        r, c = self.ai.get_best_move(self.game, self.ai_color)
        self.game.place_piece(r, c, self.ai_color)
        self.draw_board()

        if self.game.check_win(r, c, self.ai_color):
            self.game_over("很遗憾，AI获胜！", "AI")
        else:
            self.current_player = self.human_color
            color_str = "黑子(先手)" if self.human_color == 1 else "白子(后手)"
            self.status_var.set(f"玩家({color_str})回合")

            current_eval = self.ai.evaluate_board(self.game.grid, self.ai_color)
            self.voice.trigger_context_voice(current_eval)

    def undo(self):
        if self.is_game_over or self.current_player != self.human_color: return
        if self.game.undo_move() and self.game.undo_move():
            self.draw_board()

    def game_over(self, msg, winner):
        self.is_game_over = True
        self.status_var.set(msg)
        self.voice.trigger_context_voice(0, is_game_over=True, winner=winner)
        messagebox.showinfo("游戏结束", msg)

    def reset_game(self):
        self.game = GomokuBoard(self.board_size)
        self.is_game_over = False
        self.human_color *= -1
        self.ai_color = -self.human_color
        self.current_player = 1
        self.draw_board()
        color_str = "黑子(先手)" if self.human_color == 1 else "白子(后手)"

        if self.current_player == self.human_color:
            self.status_var.set(f"玩家({color_str})回合")
        else:
            self.status_var.set("AI思考中 (执黑先行)...")
            self.root.update()
            self.root.after(300, self.ai_turn)


if __name__ == "__main__":
    root = tk.Tk()
    root.resizable(False, False)
    app = GomokuGUI(root)
    root.mainloop()