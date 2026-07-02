import tkinter as tk
from tkinter import messagebox
import math


# ==========================================
# 模块1：核心逻辑模块 (3D 空间状态与 26方向规则引擎)
# ==========================================
class Gomoku3DBoard:
    def __init__(self, size=10):
        self.size = size
        self.grid = [[[0] * size for _ in range(size)] for _ in range(size)]
        self.history = []

    def place_piece(self, x, y, z, player):
        if self.grid[z][y][x] == 0:
            self.grid[z][y][x] = player
            self.history.append((x, y, z))
            return True
        return False

    def undo_move(self):
        if self.history:
            x, y, z = self.history.pop()
            self.grid[z][y][x] = 0
            return True
        return False

    def check_win(self, x, y, z, player):
        directions = [
            (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (0, 1, 1), (0, 1, -1),
            (1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1)
        ]

        for dx, dy, dz in directions:
            count = 1
            nx, ny, nz = x + dx, y + dy, z + dz
            while 0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size and self.grid[nz][ny][
                nx] == player:
                count += 1
                nx, ny, nz = nx + dx, ny + dy, nz + dz
            nx, ny, nz = x - dx, y - dy, z - dz
            while 0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size and self.grid[nz][ny][
                nx] == player:
                count += 1
                nx, ny, nz = nx - dx, ny - dy, nz - dz

            if count >= 5:
                return True
        return False

    def get_candidate_moves(self):
        moves = set()
        for z in range(self.size):
            for y in range(self.size):
                for x in range(self.size):
                    if self.grid[z][y][x] != 0:
                        for dz in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                for dx in [-1, 0, 1]:
                                    nz, ny, nx = z + dz, y + dy, x + dx
                                    if 0 <= nz < self.size and 0 <= ny < self.size and 0 <= nx < self.size and \
                                            self.grid[nz][ny][nx] == 0:
                                        moves.add((nx, ny, nz))
        return list(moves)


# ==========================================
# 模块2：AI算法模块 (3D 评估函数与 Alpha-Beta 剪枝)
# ==========================================
class Gomoku3DAI:
    def __init__(self, board_size=10, depth=1):
        self.size = board_size
        self.depth = depth

    def evaluate_board(self, board_obj, ai_player):
        score = 0
        grid = board_obj.grid
        directions = [
            (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (0, 1, 1), (0, 1, -1),
            (1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1)
        ]

        for z in range(self.size):
            for y in range(self.size):
                for x in range(self.size):
                    if grid[z][y][x] == 0: continue
                    player = grid[z][y][x]

                    for dx, dy, dz in directions:
                        px, py, pz = x - dx, y - dy, z - dz
                        if 0 <= px < self.size and 0 <= py < self.size and 0 <= pz < self.size and grid[pz][py][
                            px] == player:
                            continue

                        count = 1
                        nx, ny, nz = x + dx, y + dy, z + dz
                        while 0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size and grid[nz][ny][
                            nx] == player:
                            count += 1
                            nx += dx;
                            ny += dy;
                            nz += dz

                        blocks = 0
                        if not (0 <= px < self.size and 0 <= py < self.size and 0 <= pz < self.size) or grid[pz][py][
                            px] != 0: blocks += 1
                        if not (0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size) or grid[nz][ny][
                            nx] != 0: blocks += 1

                        pts = 0
                        if count >= 5:
                            pts = 100000
                        elif count == 4:
                            pts = 10000 if blocks == 0 else 1000
                        elif count == 3:
                            pts = 1000 if blocks == 0 else 100
                        elif count == 2:
                            pts = 100 if blocks == 0 else 10

                        if player == ai_player:
                            score += pts
                        else:
                            score -= pts * 2
        return score

    def minimax(self, board_obj, depth, alpha, beta, is_maximizing, ai_player):
        if depth == 0: return self.evaluate_board(board_obj, ai_player)

        moves = board_obj.get_candidate_moves()
        if not moves: return 0
        human_player = -ai_player

        if is_maximizing:
            max_eval = -math.inf
            for x, y, z in moves:
                board_obj.grid[z][y][x] = ai_player
                if board_obj.check_win(x, y, z, ai_player):
                    board_obj.grid[z][y][x] = 0
                    return 100000 + depth
                eval = self.minimax(board_obj, depth - 1, alpha, beta, False, ai_player)
                board_obj.grid[z][y][x] = 0
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha: break
            return max_eval
        else:
            min_eval = math.inf
            for x, y, z in moves:
                board_obj.grid[z][y][x] = human_player
                if board_obj.check_win(x, y, z, human_player):
                    board_obj.grid[z][y][x] = 0
                    return -100000 - depth
                eval = self.minimax(board_obj, depth - 1, alpha, beta, True, ai_player)
                board_obj.grid[z][y][x] = 0
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha: break
            return min_eval

    def get_best_move(self, board_obj, ai_player):
        best_val = -math.inf
        best_move = None
        moves = board_obj.get_candidate_moves()

        if not moves:
            mid = self.size // 2
            return (mid, mid, mid)

        for x, y, z in moves:
            board_obj.grid[z][y][x] = ai_player
            if board_obj.check_win(x, y, z, ai_player):
                board_obj.grid[z][y][x] = 0
                return (x, y, z)

            move_val = self.minimax(board_obj, self.depth - 1, -math.inf, math.inf, False, ai_player)
            board_obj.grid[z][y][x] = 0

            if move_val > best_val:
                best_move = (x, y, z)
                best_val = move_val

        return best_move if best_move else moves[0]


# ==========================================
# 模块3：多界面应用程序架构 (主菜单 + 游戏界面)
# ==========================================
class MainMenuFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#1E293B")
        self.controller = controller

        # UI 美化：背景与标题
        title_canvas = tk.Canvas(self, bg="#1E293B", highlightthickness=0, width=600, height=150)
        title_canvas.place(relx=0.5, rely=0.3, anchor="center")

        # 阴影效果
        title_canvas.create_text(303, 78, text="三维五子棋游戏", font=("Microsoft YaHei", 42, "bold"), fill="#0F172A")
        title_canvas.create_text(300, 75, text="三维五子棋游戏", font=("Microsoft YaHei", 42, "bold"), fill="#F8FAFC")
        title_canvas.create_text(300, 130, text="True 3D Spatial Gomoku AI", font=("Arial", 14), fill="#94A3B8")

        # 按钮样式配置
        btn_style = {
            "font": ("Microsoft YaHei", 16, "bold"),
            "width": 14,
            "bd": 0,
            "cursor": "hand2"
        }

        start_btn = tk.Button(self, text="开始游戏", bg="#3B82F6", fg="white",
                              activebackground="#2563EB", activeforeground="white",
                              command=self.show_role_selection, **btn_style)
        start_btn.place(relx=0.5, rely=0.55, anchor="center")

        exit_btn = tk.Button(self, text="结束游戏", bg="#EF4444", fg="white",
                             activebackground="#DC2626", activeforeground="white",
                             command=self.controller.root.quit, **btn_style)
        exit_btn.place(relx=0.5, rely=0.68, anchor="center")

    def show_role_selection(self):
        # 弹窗选择阵营
        popup = tk.Toplevel(self)
        popup.title("选择阵营")
        popup.geometry("340x220")
        popup.configure(bg="#F1F5F9")
        popup.resizable(False, False)

        # 使弹窗居中
        popup.update_idletasks()
        x = self.controller.root.winfo_x() + (self.controller.root.winfo_width() - 340) // 2
        y = self.controller.root.winfo_y() + (self.controller.root.winfo_height() - 220) // 2
        popup.geometry(f"+{x}+{y}")

        popup.grab_set()  # 模态窗口

        tk.Label(popup, text="请选择您的棋子颜色", font=("Microsoft YaHei", 14, "bold"), bg="#F1F5F9", fg="#333").pack(
            pady=30)

        btn_frame = tk.Frame(popup, bg="#F1F5F9")
        btn_frame.pack()

        def choose_black():
            popup.destroy()
            self.controller.start_game(1)  # 1 为黑棋

        def choose_white():
            popup.destroy()
            self.controller.start_game(-1)  # -1 为白棋

        tk.Button(btn_frame, text="执黑 (玩家先手)", font=("Microsoft YaHei", 11), bg="#1E293B", fg="white",
                  width=12, bd=0, command=choose_black).pack(side=tk.LEFT, padx=10)

        tk.Button(btn_frame, text="执白 (AI先手)", font=("Microsoft YaHei", 11), bg="#FFFFFF", fg="black",
                  width=12, bd=1, command=choose_white).pack(side=tk.LEFT, padx=10)


class GameFrame(tk.Frame):
    def __init__(self, parent, controller, human_color):
        super().__init__(parent, bg="#F3F4F6")
        self.controller = controller

        self.board_size = 10
        self.cell_size = 35
        self.margin = 30
        self.current_z = self.board_size // 2

        self.azimuth = math.pi / 4
        self.elevation = math.pi / 6
        self.scale_3d = 26
        self.last_mouse_x = 0
        self.last_mouse_y = 0

        # 定时器相关
        self.human_timer_id = None
        self.ai_wait_timer_id = None
        self.time_left = 60
        self.ai_wait_seconds = 5

        self.ai = Gomoku3DAI(self.board_size, depth=1)
        self.human_color = human_color
        self.ai_color = -human_color

        self.setup_ui()
        self.reset_game()

    def setup_ui(self):
        # 顶层控制面板
        top_frame = tk.Frame(self, bg="#FFFFFF", height=60)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=10)

        tk.Button(top_frame, text="重新开始", font=("Microsoft YaHei", 10), bg="#E5E7EB", bd=0,
                  command=self.reset_game).pack(side=tk.LEFT, padx=10, pady=15)
        tk.Button(top_frame, text="悔棋", font=("Microsoft YaHei", 10), bg="#E5E7EB", bd=0, command=self.undo).pack(
            side=tk.LEFT, padx=10, pady=15)

        self.timer_var = tk.StringVar()
        self.timer_var.set("倒计时: 60s")
        tk.Label(top_frame, textvariable=self.timer_var, font=("Arial", 12, "bold"), fg="#EF4444", bg="#FFFFFF").pack(
            side=tk.LEFT, padx=15)

        self.status_var = tk.StringVar()
        tk.Label(top_frame, textvariable=self.status_var, font=("Microsoft YaHei", 12, "bold"), bg="#FFFFFF",
                 fg="#374151").pack(side=tk.LEFT, padx=20)

        # ★ 游戏进行中常驻的结束游戏按钮 ★
        tk.Button(top_frame, text="结束游戏", font=("Microsoft YaHei", 10, "bold"), bg="#EF4444", fg="white",
                  bd=0, command=self.return_to_menu).pack(side=tk.RIGHT, padx=20, pady=15)

        # 核心视图区
        main_frame = tk.Frame(self, bg="#F3F4F6")
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_frame, bg="#F3F4F6")
        left_frame.pack(side=tk.LEFT, padx=20)

        tk.Label(left_frame, text="2D 切片操作区 (在此精准落子)", font=("Microsoft YaHei", 10, "bold"), bg="#F3F4F6",
                 fg="#4B5563").pack(pady=5)

        self.z_slider = tk.Scale(left_frame, from_=0, to=self.board_size - 1, orient=tk.HORIZONTAL,
                                 label="当前楼层 (Z轴)", command=self.on_z_change, bg="#F3F4F6", highlightthickness=0)
        self.z_slider.set(self.current_z)
        self.z_slider.pack(fill=tk.X, pady=5)

        canvas_width = self.cell_size * (self.board_size - 1) + self.margin * 2
        self.canvas_2d = tk.Canvas(left_frame, width=canvas_width, height=canvas_width, bg="#E6C280",
                                   highlightthickness=2, highlightbackground="#D1D5DB")
        self.canvas_2d.pack()
        self.canvas_2d.bind("<Button-1>", self.on_click_2d)

        right_frame = tk.Frame(main_frame, bg="#F3F4F6")
        right_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(right_frame, text="3D 空间全景预览 (拖拽旋转 / 滚轮缩放)", font=("Microsoft YaHei", 10, "bold"),
                 bg="#F3F4F6", fg="#4B5563").pack(pady=5)

        self.canvas_3d = tk.Canvas(right_frame, width=550, height=550, bg="#E8F0F8", highlightthickness=2,
                                   highlightbackground="#D1D5DB")
        self.canvas_3d.pack()

        self.canvas_3d.bind("<ButtonPress-1>", self.start_drag)
        self.canvas_3d.bind("<B1-Motion>", self.on_drag)
        self.canvas_3d.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas_3d.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas_3d.bind("<Button-5>", self.on_mouse_wheel)

        # --- 定时器逻辑控制 ---

    def cancel_all_timers(self):
        if self.human_timer_id:
            self.after_cancel(self.human_timer_id)
            self.human_timer_id = None
        if self.ai_wait_timer_id:
            self.after_cancel(self.ai_wait_timer_id)
            self.ai_wait_timer_id = None

    def start_human_timer(self):
        self.cancel_all_timers()
        self.time_left = 60
        self.update_human_timer()

    def update_human_timer(self):
        if self.is_game_over or self.current_player != self.human_color:
            return

        self.timer_var.set(f"倒计时: {self.time_left}s")

        if self.time_left <= 0:
            self.force_human_move_by_ai()
        else:
            self.time_left -= 1
            self.human_timer_id = self.after(1000, self.update_human_timer)

    def start_ai_wait_countdown(self, seconds=5):
        self.cancel_all_timers()
        self.ai_wait_seconds = seconds
        self.timer_var.set("--")
        self.update_ai_wait_timer()

    def update_ai_wait_timer(self):
        if self.is_game_over or self.current_player != self.ai_color:
            return

        if self.ai_wait_seconds > 0:
            self.status_var.set(f"等待 AI 落子... ({self.ai_wait_seconds}s)")
            self.ai_wait_seconds -= 1
            self.ai_wait_timer_id = self.after(1000, self.update_ai_wait_timer)
        else:
            self.status_var.set("AI 思考中(3D空间测算较慢)...")
            self.update()
            self.after(50, self.ai_turn)

    def force_human_move_by_ai(self):
        if self.is_game_over: return
        self.status_var.set("时间到！系统正在为您代下...")
        self.update()

        x, y, z = self.ai.get_best_move(self.game, self.human_color)
        self.game.place_piece(x, y, z, self.human_color)

        self.draw_2d_board()
        self.draw_3d_preview()

        if self.game.check_win(x, y, z, self.human_color):
            self.game_over("超时自动落子：恭喜玩家获胜！")
        else:
            self.current_player = self.ai_color
            self.start_ai_wait_countdown(5)

    def return_to_menu(self):
        """安全停止游戏并返回主菜单"""
        self.cancel_all_timers()
        self.controller.show_main_menu()

    # --- 交互与渲染引擎 ---
    def on_mouse_wheel(self, event):
        if event.num == 5 or event.delta < 0:
            self.scale_3d = max(10, self.scale_3d - 2)
        if event.num == 4 or event.delta > 0:
            self.scale_3d = min(60, self.scale_3d + 2)
        self.draw_3d_preview()

    def start_drag(self, event):
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

    def on_drag(self, event):
        dx = event.x - self.last_mouse_x
        dy = event.y - self.last_mouse_y
        self.azimuth -= dx * 0.01
        self.elevation -= dy * 0.01
        self.elevation = max(-math.pi / 2.5, min(math.pi / 2.5, self.elevation))
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
        self.draw_3d_preview()

    def on_z_change(self, val):
        self.current_z = int(val)
        self.draw_2d_board()
        self.draw_3d_preview()

    def draw_2d_board(self):
        self.canvas_2d.delete("all")
        for i in range(self.board_size):
            x = self.margin + i * self.cell_size
            self.canvas_2d.create_line(x, self.margin, x, self.margin + (self.board_size - 1) * self.cell_size)
            y = self.margin + i * self.cell_size
            self.canvas_2d.create_line(self.margin, y, self.margin + (self.board_size - 1) * self.cell_size, y)

        last_move = self.game.history[-1] if self.game.history else None

        for y in range(self.board_size):
            for x in range(self.board_size):
                piece = self.game.grid[self.current_z][y][x]
                if piece != 0:
                    px = self.margin + x * self.cell_size
                    py = self.margin + y * self.cell_size
                    r = self.cell_size * 0.4
                    color = "#222222" if piece == 1 else "#F8F8F8"
                    out_c = "#000000" if piece == 1 else "#999999"
                    self.canvas_2d.create_oval(px - r, py - r, px + r, py + r, fill=color, outline=out_c)

                    # ★ 新增：高亮显示最新落子 (红点) ★
                    if last_move and (x, y, self.current_z) == last_move:
                        self.canvas_2d.create_oval(px - 3, py - 3, px + 3, py + 3, fill="red", outline="red")

    def draw_3d_preview(self):
        self.canvas_3d.delete("all")
        cx, cy = 275, 275
        scale = self.scale_3d

        def map_3d(x, y, z):
            dx = x - (self.board_size - 1) / 2.0
            dy = y - (self.board_size - 1) / 2.0
            dz = z - (self.board_size - 1) / 2.0

            x1 = dx * math.cos(self.azimuth) - dy * math.sin(self.azimuth)
            y1 = dx * math.sin(self.azimuth) + dy * math.cos(self.azimuth)

            y2 = y1 * math.cos(self.elevation) - dz * math.sin(self.elevation)
            z2 = y1 * math.sin(self.elevation) + dz * math.cos(self.elevation)

            return cx + x1 * scale, cy + y2 * scale, z2

        grid_color = "#C5D3E8"
        for i in range(self.board_size):
            for j in range(self.board_size):
                sx1, sy1, _ = map_3d(0, i, j)
                sx2, sy2, _ = map_3d(self.board_size - 1, i, j)
                self.canvas_3d.create_line(sx1, sy1, sx2, sy2, fill=grid_color, width=1)

                sx1, sy1, _ = map_3d(i, 0, j)
                sx2, sy2, _ = map_3d(i, self.board_size - 1, j)
                self.canvas_3d.create_line(sx1, sy1, sx2, sy2, fill=grid_color, width=1)

                sx1, sy1, _ = map_3d(i, j, 0)
                sx2, sy2, _ = map_3d(i, j, self.board_size - 1)
                self.canvas_3d.create_line(sx1, sy1, sx2, sy2, fill=grid_color, width=1)

        mapped_pieces = []
        for z in range(self.board_size):
            for y in range(self.board_size):
                for x in range(self.board_size):
                    player = self.game.grid[z][y][x]
                    if player != 0:
                        sx, sy, depth = map_3d(x, y, z)
                        mapped_pieces.append((x, y, z, sx, sy, depth, player))

        mapped_pieces.sort(key=lambda p: p[5])  # 按深度排序
        last_move = self.game.history[-1] if self.game.history else None

        for x, y, orig_z, sx, sy, depth, player in mapped_pieces:
            r = max(4, self.scale_3d * 0.35)

            if player == 1:
                fill_c, out_c = "#1A1A1A", "#000000"
            else:
                fill_c, out_c = "#F8F8F8", "#999999"

            if orig_z == self.current_z:
                self.canvas_3d.create_oval(sx - r - 3, sy - r - 3, sx + r + 3, sy + r + 3, outline="#FF5722", width=2)

            self.canvas_3d.create_oval(sx - r, sy - r, sx + r, sy + r, fill=fill_c, outline=out_c)

            # ★ 新增：高亮显示最新落子 (在3D中心画个红点) ★
            if last_move and (x, y, orig_z) == last_move:
                self.canvas_3d.create_oval(sx - 3, sy - 3, sx + 3, sy + 3, fill="red", outline="red")
            else:
                # 正常的光泽高光
                hx, hy = sx - r / 3, sy - r / 3
                self.canvas_3d.create_oval(hx - r * 0.15, hy - r * 0.15, hx + r * 0.2, hy + r * 0.2, fill="#FFFFFF",
                                           outline="")

    def on_click_2d(self, event):
        if self.is_game_over or self.current_player != self.human_color: return

        x = round((event.x - self.margin) / self.cell_size)
        y = round((event.y - self.margin) / self.cell_size)
        z = self.current_z

        if 0 <= x < self.board_size and 0 <= y < self.board_size:
            if self.game.place_piece(x, y, z, self.human_color):
                self.draw_2d_board()
                self.draw_3d_preview()

                if self.game.check_win(x, y, z, self.human_color):
                    self.cancel_all_timers()
                    self.game_over("恭喜！玩家获胜！")
                else:
                    self.current_player = self.ai_color
                    self.start_ai_wait_countdown(5)

    def ai_turn(self):
        if self.is_game_over: return
        x, y, z = self.ai.get_best_move(self.game, self.ai_color)
        self.game.place_piece(x, y, z, self.ai_color)

        self.current_z = z
        self.z_slider.set(z)
        self.draw_2d_board()
        self.draw_3d_preview()

        if self.game.check_win(x, y, z, self.ai_color):
            self.cancel_all_timers()
            self.game_over("很遗憾，AI获胜！")
        else:
            self.current_player = self.human_color
            color_str = "黑棋" if self.human_color == 1 else "白棋"
            self.status_var.set(f"玩家回合 ({color_str})")
            self.start_human_timer()

    def undo(self):
        if self.is_game_over: return

        if self.current_player == self.ai_color:
            if len(self.game.history) >= 1:
                self.cancel_all_timers()
                self.game.undo_move()
                self.current_player = self.human_color
                self.start_human_timer()
                color_str = "黑棋" if self.human_color == 1 else "白棋"
                self.status_var.set(f"玩家回合 ({color_str})")
                self.draw_2d_board()
                self.draw_3d_preview()
        elif self.current_player == self.human_color:
            if len(self.game.history) >= 2:
                self.cancel_all_timers()
                self.game.undo_move()
                self.game.undo_move()
                self.start_human_timer()
                color_str = "黑棋" if self.human_color == 1 else "白棋"
                self.status_var.set(f"玩家回合 ({color_str})")
                self.draw_2d_board()
                self.draw_3d_preview()

    def game_over(self, msg):
        self.cancel_all_timers()
        self.is_game_over = True
        self.timer_var.set("--")
        self.status_var.set(msg)
        messagebox.showinfo("游戏结束", msg)

    def reset_game(self):
        self.cancel_all_timers()
        self.game = Gomoku3DBoard(self.board_size)
        self.is_game_over = False

        # 始终保持进入时的阵营选择 (黑棋规定为 1, 白棋 -1)
        # 约定：黑棋(1)永远先手
        self.current_player = 1

        self.draw_2d_board()
        self.draw_3d_preview()
        color_str = "黑棋" if self.human_color == 1 else "白棋"

        if self.current_player == self.human_color:
            self.status_var.set(f"玩家回合 ({color_str})")
            self.start_human_timer()
        else:
            # 第一手免受5秒折磨，立刻下
            self.start_ai_wait_countdown(1)


# ==========================================
# 应用程序总控制器
# ==========================================
class GomokuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("三维五子棋游戏")
        self.root.geometry("1000x700")
        self.root.configure(bg="#1E293B")

        self.current_frame = None
        self.show_main_menu()

    def switch_frame(self, frame_class, **kwargs):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame_class(self.root, self, **kwargs)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_main_menu(self):
        self.switch_frame(MainMenuFrame)

    def start_game(self, human_color):
        self.switch_frame(GameFrame, human_color=human_color)


if __name__ == "__main__":
    root = tk.Tk()
    root.resizable(False, False)
    app = GomokuApp(root)
    root.mainloop()