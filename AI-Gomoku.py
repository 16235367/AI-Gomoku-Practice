import tkinter as tk
from tkinter import messagebox
import math
import copy


# ==========================================
# 模块1：核心逻辑模块 (15x15x15, 融解与凝固规则引擎)
# ==========================================
class Gomoku3DBoard:
    def __init__(self, size=15):
        self.size = size
        # grid状态: 0=空, 1=黑, -1=白, 2=凝固的废棋
        self.grid = [[[0] * size for _ in range(size)] for _ in range(size)]
        self.history = []
        self.scores = {1: 0, -1: 0}  # 双方得分

    def place_piece(self, x, y, z, player):
        if self.grid[z][y][x] == 0:
            # 深拷贝保存历史，用于玩家真实的悔棋操作
            self.history.append((copy.deepcopy(self.grid), self.scores.copy()))
            self.grid[z][y][x] = player
            self._process_chains(x, y, z)
            return True
        return False

    def undo_move(self):
        if self.history:
            last_grid, last_scores = self.history.pop()
            self.grid = last_grid
            self.scores = last_scores
            return True
        return False

    def _process_chains(self, x, y, z):
        """核心：扫描 13 个轴向的 5 子链，触发凝固或融解"""
        directions = [
            (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (0, 1, 1), (0, 1, -1),
            (1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1)
        ]

        for dx, dy, dz in directions:
            for offset in range(-4, 1):
                chain = []
                valid = True
                for i in range(5):
                    nx = x + dx * (offset + i)
                    ny = y + dy * (offset + i)
                    nz = z + dz * (offset + i)

                    if 0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size:
                        state = self.grid[nz][ny][nx]
                        if state in [1, -1]:
                            chain.append((nx, ny, nz, state))
                        else:
                            valid = False;
                            break
                    else:
                        valid = False;
                        break

                if valid and len(chain) == 5:
                    c_black = sum(1 for _, _, _, s in chain if s == 1)
                    c_white = sum(1 for _, _, _, s in chain if s == -1)

                    if c_black == 5 or c_white == 5:
                        for cx, cy, cz, _ in chain:
                            self.grid[cz][cy][cx] = 2
                    elif c_black + c_white == 5:
                        majority = 1 if c_black > c_white else -1
                        self.scores[majority] += 1
                        for cx, cy, cz, _ in chain:
                            self.grid[cz][cy][cx] = 0

    def check_win(self):
        if self.scores[1] >= 5: return 1
        if self.scores[-1] >= 5: return -1
        return 0

    def get_candidate_moves(self):
        moves = set()
        for z in range(self.size):
            for y in range(self.size):
                for x in range(self.size):
                    if self.grid[z][y][x] in [1, -1]:
                        for dz in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                for dx in [-1, 0, 1]:
                                    nz, ny, nx = z + dz, y + dy, x + dx
                                    if 0 <= nz < self.size and 0 <= ny < self.size and 0 <= nx < self.size and \
                                            self.grid[nz][ny][nx] == 0:
                                        moves.add((nx, ny, nz))
        return list(moves)

    # ---------------------------------------------------------
    # 新增：专为 AI 设计的“极速状态推演引擎” (避免深度拷贝造成的卡顿)
    # ---------------------------------------------------------
    def simulate_place(self, x, y, z, player):
        """高效模拟落子，返回被改变的差异数据，实现毫秒级推演"""
        if self.grid[z][y][x] != 0:
            return None

        changes = []  # 记录 (cx, cy, cz, 改变前的值)
        old_scores = self.scores.copy()

        self.grid[z][y][x] = player
        changes.append((x, y, z, 0))

        directions = [
            (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (0, 1, 1), (0, 1, -1),
            (1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1)
        ]
        for dx, dy, dz in directions:
            for offset in range(-4, 1):
                chain = []
                valid = True
                for i in range(5):
                    nx = x + dx * (offset + i)
                    ny = y + dy * (offset + i)
                    nz = z + dz * (offset + i)
                    if 0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size:
                        state = self.grid[nz][ny][nx]
                        if state in [1, -1]:
                            chain.append((nx, ny, nz, state))
                        else:
                            valid = False; break
                    else:
                        valid = False; break

                if valid and len(chain) == 5:
                    c_black = sum(1 for _, _, _, s in chain if s == 1)
                    c_white = sum(1 for _, _, _, s in chain if s == -1)

                    if c_black == 5 or c_white == 5:
                        for cx, cy, cz, _ in chain:
                            if self.grid[cz][cy][cx] != 2:
                                changes.append((cx, cy, cz, self.grid[cz][cy][cx]))
                                self.grid[cz][cy][cx] = 2
                    elif c_black + c_white == 5:
                        majority = 1 if c_black > c_white else -1
                        self.scores[majority] += 1
                        for cx, cy, cz, _ in chain:
                            if self.grid[cz][cy][cx] != 0:
                                changes.append((cx, cy, cz, self.grid[cz][cy][cx]))
                                self.grid[cz][cy][cx] = 0
        return changes, old_scores

    def simulate_undo(self, changes, old_scores):
        """利用差异数据快速恢复棋盘，不留痕迹"""
        for cx, cy, cz, old_val in reversed(changes):
            self.grid[cz][cy][cx] = old_val
        self.scores = old_scores


# ==========================================
# 模块2：AI算法模块 (全面升级的高级战术评估网络)
# ==========================================
class Gomoku3DAI:
    def __init__(self, board_size=15):
        self.size = board_size

    def get_best_move(self, board_obj, ai_player):
        hu_player = -ai_player
        moves = board_obj.get_candidate_moves()

        if not moves:  # 应对开局第一手
            mid = self.size // 2
            return (mid, mid, mid)

        best_move = None
        max_score = -math.inf

        for x, y, z in moves:
            # 1. 使用极速引擎推演落子后的平行宇宙状态
            sim_result = board_obj.simulate_place(x, y, z, ai_player)
            if not sim_result: continue
            changes, old_scores = sim_result

            ai_gain = board_obj.scores[ai_player] - old_scores[ai_player]
            hu_gain = board_obj.scores[hu_player] - old_scores[hu_player]

            # 【绝杀检测】如果这步棋能让AI直接得分，这是完美的终极目标，直接选它！
            if ai_gain > 0:
                board_obj.simulate_undo(changes, old_scores)
                return (x, y, z)

            # 【排雷避险】如果这步棋下了反而导致玩家得分（融解出玩家占优的链条），绝对不能下！
            if hu_gain > 0:
                board_obj.simulate_undo(changes, old_scores)
                continue

            # 2. 如果没有立即发生融解，则审视落子后形成的空间阵法（形状打分）
            shape_score = self.evaluate_shapes(board_obj, x, y, z, ai_player)

            # 添加一点向心力，优先占据空间中心
            dist_to_center = -((x - self.size // 2) ** 2 + (y - self.size // 2) ** 2 + (z - self.size // 2) ** 2)
            eval_score = shape_score + dist_to_center * 0.1

            if eval_score > max_score:
                max_score = eval_score
                best_move = (x, y, z)

            # 清理平行宇宙，恢复棋盘
            board_obj.simulate_undo(changes, old_scores)

        return best_move if best_move else moves[0]

    def evaluate_shapes(self, board_obj, x, y, z, ai_player):
        """
        高智商评估函数：根据“融解凝固”规则重写了所有棋型的价值观
        """
        hu_player = -ai_player
        score = 0
        directions = [
            (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (0, 1, 1), (0, 1, -1),
            (1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1)
        ]
        for dx, dy, dz in directions:
            for offset in range(-4, 1):
                window = []
                valid = True
                for i in range(5):
                    nx = x + dx * (offset + i)
                    ny = y + dy * (offset + i)
                    nz = z + dz * (offset + i)
                    if 0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size:
                        st = board_obj.grid[nz][ny][nx]
                        if st in [1, -1, 0]:
                            window.append(st)
                        else:  # 废棋(2) 就像一堵墙，阻断一切
                            valid = False;
                            break
                    else:
                        valid = False;
                        break

                if valid and len(window) == 5:
                    c_ai = window.count(ai_player)
                    c_hu = window.count(hu_player)

                    # ----------------------------------------------------
                    # 战术选择 1: 构建致命陷阱与绞杀网
                    # ----------------------------------------------------
                    if c_ai == 3 and c_hu == 1:
                        # 完美威胁：4个子中我有3个，下轮我再点一子就能得1分！
                        score += 5000
                    elif c_ai == 2 and c_hu == 1:
                        # 战术牵制：形成 2:1 的包夹，逼迫玩家响应。玩家若应对不当就会送分
                        score += 500
                    elif c_ai == 1 and c_hu == 1:
                        # 寻找战机：主动贴近玩家的孤子，创造异色融解条件
                        score += 50

                    # ----------------------------------------------------
                    # 战术选择 2: 杜绝送人头，极其谨慎
                    # ----------------------------------------------------
                    elif c_ai == 2 and c_hu == 2:
                        # 致命漏洞：因为现在轮到玩家下棋，2:2 意味着玩家一下就能拿到 3:2 得分。绝不走这一步！
                        score -= 10000
                    elif c_ai == 1 and c_hu == 3:
                        # 送分童子：帮玩家补齐了最缺的异色子，下轮玩家绝杀。
                        score -= 10000
                    elif c_ai == 1 and c_hu == 2:
                        # 糟糕的试探：让玩家占据了局部人数优势。
                        score -= 500

                    # ----------------------------------------------------
                    # 战术选择 3: 对待纯色链的极度聪明处理
                    # ----------------------------------------------------
                    elif c_hu == 4 and c_ai == 0:
                        # 看着对手作死：玩家已经连了4个纯色，再连就变石头了。AI不但不堵，反而心里暗爽。
                        score += 200
                    elif c_ai == 4 and c_hu == 0:
                        # 避免死胡同：自己走纯色是没前途的（除非想强行造墙）
                        score -= 100
                    elif c_ai == 3 and c_hu == 0:
                        score += 10
                    elif c_ai == 2 and c_hu == 0:
                        score += 5
                    elif c_ai == 1 and c_hu == 0:
                        score += 1

        return score


# ==========================================
# 模块3：多界面应用程序架构 (主菜单 + 自适应15格的游戏界面)
# ==========================================
class MainMenuFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#1E293B")
        self.controller = controller

        title_canvas = tk.Canvas(self, bg="#1E293B", highlightthickness=0, width=800, height=180)
        title_canvas.place(relx=0.5, rely=0.3, anchor="center")

        title_canvas.create_text(403, 78, text="融解与凝固：三维五子棋", font=("Microsoft YaHei", 40, "bold"),
                                 fill="#0F172A")
        title_canvas.create_text(400, 75, text="融解与凝固：三维五子棋", font=("Microsoft YaHei", 40, "bold"),
                                 fill="#F8FAFC")
        title_canvas.create_text(400, 130, text="15x15x15 异色消除规则 | 高级战术博弈", font=("Arial", 16),
                                 fill="#94A3B8")

        btn_style = {"font": ("Microsoft YaHei", 16, "bold"), "width": 14, "bd": 0, "cursor": "hand2"}

        start_btn = tk.Button(self, text="开始游戏", bg="#3B82F6", fg="white",
                              activebackground="#2563EB", activeforeground="white",
                              command=self.show_role_selection, **btn_style)
        start_btn.place(relx=0.5, rely=0.55, anchor="center")

        exit_btn = tk.Button(self, text="结束游戏", bg="#EF4444", fg="white",
                             activebackground="#DC2626", activeforeground="white",
                             command=self.controller.root.quit, **btn_style)
        exit_btn.place(relx=0.5, rely=0.68, anchor="center")

    def show_role_selection(self):
        popup = tk.Toplevel(self)
        popup.title("选择阵营")
        popup.geometry("340x220")
        popup.configure(bg="#F1F5F9")
        popup.resizable(False, False)

        popup.update_idletasks()
        x = self.controller.root.winfo_x() + (self.controller.root.winfo_width() - 340) // 2
        y = self.controller.root.winfo_y() + (self.controller.root.winfo_height() - 220) // 2
        popup.geometry(f"+{x}+{y}")
        popup.grab_set()

        tk.Label(popup, text="请选择您的阵营颜色", font=("Microsoft YaHei", 14, "bold"), bg="#F1F5F9", fg="#333").pack(
            pady=30)

        btn_frame = tk.Frame(popup, bg="#F1F5F9")
        btn_frame.pack()

        def choose_black(): popup.destroy(); self.controller.start_game(1)

        def choose_white(): popup.destroy(); self.controller.start_game(-1)

        tk.Button(btn_frame, text="黑棋 (玩家先)", font=("Microsoft YaHei", 11), bg="#1A1A1A", fg="white", width=12,
                  bd=0, command=choose_black).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="白棋 (AI先)", font=("Microsoft YaHei", 11), bg="#FFFFFF", fg="black", width=12, bd=1,
                  command=choose_white).pack(side=tk.LEFT, padx=10)


class GameFrame(tk.Frame):
    def __init__(self, parent, controller, human_color):
        super().__init__(parent, bg="#F3F4F6")
        self.controller = controller

        self.board_size = 15
        self.cell_size = 28
        self.margin = 25
        self.current_z = self.board_size // 2

        self.azimuth = math.pi / 4
        self.elevation = math.pi / 6
        self.scale_3d = 16
        self.last_mouse_x = 0
        self.last_mouse_y = 0

        self.human_timer_id = None
        self.ai_wait_timer_id = None
        self.time_left = 60
        self.ai_wait_seconds = 5

        self.ai = Gomoku3DAI(self.board_size)
        self.human_color = human_color
        self.ai_color = -human_color

        self.setup_ui()
        self.reset_game()

    def setup_ui(self):
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
                 fg="#374151").pack(side=tk.LEFT, padx=15)

        self.score_var = tk.StringVar()
        self.score_var.set("得分战况 >> 黑棋: 0/5 | 白棋: 0/5")
        tk.Label(top_frame, textvariable=self.score_var, font=("Microsoft YaHei", 12, "bold"), bg="#FEF3C7",
                 fg="#D97706", padx=15).pack(side=tk.LEFT, padx=10)

        tk.Button(top_frame, text="结束游戏", font=("Microsoft YaHei", 10, "bold"), bg="#EF4444", fg="white",
                  bd=0, command=self.return_to_menu).pack(side=tk.RIGHT, padx=20, pady=15)

        main_frame = tk.Frame(self, bg="#F3F4F6")
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_frame, bg="#F3F4F6")
        left_frame.pack(side=tk.LEFT, padx=20)

        tk.Label(left_frame, text=f"2D 切片 ({self.board_size}x{self.board_size}) 自由落子",
                 font=("Microsoft YaHei", 10, "bold"), bg="#F3F4F6", fg="#4B5563").pack(pady=5)

        self.z_slider = tk.Scale(left_frame, from_=0, to=self.board_size - 1, orient=tk.HORIZONTAL,
                                 label="当前楼层深度 (Z轴)", command=self.on_z_change, bg="#F3F4F6",
                                 highlightthickness=0)
        self.z_slider.set(self.current_z)
        self.z_slider.pack(fill=tk.X, pady=5)

        canvas_width = self.cell_size * (self.board_size - 1) + self.margin * 2
        self.canvas_2d = tk.Canvas(left_frame, width=canvas_width, height=canvas_width, bg="#E6C280",
                                   highlightthickness=2, highlightbackground="#D1D5DB")
        self.canvas_2d.pack()
        self.canvas_2d.bind("<Button-1>", self.on_click_2d)

        right_frame = tk.Frame(main_frame, bg="#F3F4F6")
        right_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(right_frame, text="3D 全景空间 (拖拽旋转 / 滚轮缩放 / 满5同色凝固)",
                 font=("Microsoft YaHei", 10, "bold"), bg="#F3F4F6", fg="#4B5563").pack(pady=5)

        self.canvas_3d = tk.Canvas(right_frame, width=580, height=550, bg="#E8F0F8", highlightthickness=2,
                                   highlightbackground="#D1D5DB")
        self.canvas_3d.pack()

        self.canvas_3d.bind("<ButtonPress-1>", self.start_drag)
        self.canvas_3d.bind("<B1-Motion>", self.on_drag)
        self.canvas_3d.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas_3d.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas_3d.bind("<Button-5>", self.on_mouse_wheel)

    def update_score_board(self):
        scores = self.game.scores
        self.score_var.set(f"融解战况 >> 黑棋: {scores[1]}/5 | 白棋: {scores[-1]}/5")

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
            self.status_var.set("AI 计算最佳消除点...")
            self.update()
            self.after(50, self.ai_turn)

    def force_human_move_by_ai(self):
        if self.is_game_over: return
        self.status_var.set("时间到！系统代下...")
        self.update()

        x, y, z = self.ai.get_best_move(self.game, self.human_color)
        self.game.place_piece(x, y, z, self.human_color)

        self.update_score_board()
        self.draw_2d_board()
        self.draw_3d_preview()

        winner = self.game.check_win()
        if winner != 0:
            winner_str = "玩家" if winner == self.human_color else "AI"
            self.game_over(f"积分达到 5 分，{winner_str} 获胜！")
        else:
            self.current_player = self.ai_color
            self.start_ai_wait_countdown(5)

    def return_to_menu(self):
        self.cancel_all_timers()
        self.controller.show_main_menu()

    def on_mouse_wheel(self, event):
        if event.num == 5 or event.delta < 0: self.scale_3d = max(8, self.scale_3d - 1.5)
        if event.num == 4 or event.delta > 0: self.scale_3d = min(50, self.scale_3d + 1.5)
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
            self.canvas_2d.create_line(x, self.margin, x, self.margin + (self.board_size - 1) * self.cell_size,
                                       fill="#B8905B")
            y = self.margin + i * self.cell_size
            self.canvas_2d.create_line(self.margin, y, self.margin + (self.board_size - 1) * self.cell_size, y,
                                       fill="#B8905B")

        last_move = None
        if len(self.game.history) > 0:
            last_grid = self.game.history[-1][0]
            for z in range(self.board_size):
                for y in range(self.board_size):
                    for x in range(self.board_size):
                        if last_grid[z][y][x] == 0 and self.game.grid[z][y][x] != 0:
                            last_move = (x, y, z)

        for y in range(self.board_size):
            for x in range(self.board_size):
                piece = self.game.grid[self.current_z][y][x]
                if piece != 0:
                    px = self.margin + x * self.cell_size
                    py = self.margin + y * self.cell_size
                    r = self.cell_size * 0.4

                    if piece == 1:
                        color, out_c = "#1A1A1A", "#000000"
                    elif piece == -1:
                        color, out_c = "#F8F8F8", "#999999"
                    elif piece == 2:
                        color, out_c = "#6B7280", "#374151"

                    self.canvas_2d.create_oval(px - r, py - r, px + r, py + r, fill=color, outline=out_c)

                    if piece == 2:
                        self.canvas_2d.create_line(px - r / 2, py - r / 2, px + r / 2, py + r / 2, fill="#9CA3AF",
                                                   width=2)
                        self.canvas_2d.create_line(px + r / 2, py - r / 2, px - r / 2, py + r / 2, fill="#9CA3AF",
                                                   width=2)

                    if last_move and (x, y, self.current_z) == last_move and piece in [1, -1]:
                        self.canvas_2d.create_oval(px - 3, py - 3, px + 3, py + 3, fill="red", outline="red")

    def draw_3d_preview(self):
        self.canvas_3d.delete("all")
        cx, cy = 290, 275
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
                sx1, sy1, _ = map_3d(0, i, j);
                sx2, sy2, _ = map_3d(self.board_size - 1, i, j)
                self.canvas_3d.create_line(sx1, sy1, sx2, sy2, fill=grid_color, width=1)
                sx1, sy1, _ = map_3d(i, 0, j);
                sx2, sy2, _ = map_3d(i, self.board_size - 1, j)
                self.canvas_3d.create_line(sx1, sy1, sx2, sy2, fill=grid_color, width=1)
                sx1, sy1, _ = map_3d(i, j, 0);
                sx2, sy2, _ = map_3d(i, j, self.board_size - 1)
                self.canvas_3d.create_line(sx1, sy1, sx2, sy2, fill=grid_color, width=1)

        mapped_pieces = []
        last_move = None
        if len(self.game.history) > 0:
            last_grid = self.game.history[-1][0]
            for z in range(self.board_size):
                for y in range(self.board_size):
                    for x in range(self.board_size):
                        if last_grid[z][y][x] == 0 and self.game.grid[z][y][x] != 0:
                            last_move = (x, y, z)

        for z in range(self.board_size):
            for y in range(self.board_size):
                for x in range(self.board_size):
                    player = self.game.grid[z][y][x]
                    if player != 0:
                        sx, sy, depth = map_3d(x, y, z)
                        mapped_pieces.append((x, y, z, sx, sy, depth, player))

        mapped_pieces.sort(key=lambda p: p[5])

        for x, y, orig_z, sx, sy, depth, player in mapped_pieces:
            r = max(3, self.scale_3d * 0.35)

            if player == 1:
                fill_c, out_c = "#1A1A1A", "#000000"
            elif player == -1:
                fill_c, out_c = "#F8F8F8", "#999999"
            elif player == 2:
                fill_c, out_c = "#6B7280", "#4B5563"

            if orig_z == self.current_z:
                self.canvas_3d.create_oval(sx - r - 3, sy - r - 3, sx + r + 3, sy + r + 3, outline="#FF5722", width=2)

            self.canvas_3d.create_oval(sx - r, sy - r, sx + r, sy + r, fill=fill_c, outline=out_c)

            if last_move and (x, y, orig_z) == last_move and player in [1, -1]:
                self.canvas_3d.create_oval(sx - 2, sy - 2, sx + 2, sy + 2, fill="red", outline="red")
            elif player in [1, -1]:
                hx, hy = sx - r / 3, sy - r / 3
                self.canvas_3d.create_oval(hx - r * 0.15, hy - r * 0.15, hx + r * 0.2, hy + r * 0.2, fill="#FFFFFF",
                                           outline="")
            elif player == 2:
                self.canvas_3d.create_line(sx - r / 2, sy - r / 2, sx + r / 2, sy + r / 2, fill="#9CA3AF")
                self.canvas_3d.create_line(sx + r / 2, sy - r / 2, sx - r / 2, sy + r / 2, fill="#9CA3AF")

    def on_click_2d(self, event):
        if self.is_game_over or self.current_player != self.human_color: return

        x = round((event.x - self.margin) / self.cell_size)
        y = round((event.y - self.margin) / self.cell_size)
        z = self.current_z

        if 0 <= x < self.board_size and 0 <= y < self.board_size:
            if self.game.place_piece(x, y, z, self.human_color):
                self.update_score_board()
                self.draw_2d_board()
                self.draw_3d_preview()

                winner = self.game.check_win()
                if winner != 0:
                    self.cancel_all_timers()
                    self.game_over(f"积分达到 5 分，恭喜玩家获胜！")
                else:
                    self.current_player = self.ai_color
                    self.start_ai_wait_countdown(5)

    def ai_turn(self):
        if self.is_game_over: return
        x, y, z = self.ai.get_best_move(self.game, self.ai_color)
        self.game.place_piece(x, y, z, self.ai_color)

        self.current_z = z
        self.z_slider.set(z)
        self.update_score_board()
        self.draw_2d_board()
        self.draw_3d_preview()

        winner = self.game.check_win()
        if winner != 0:
            self.cancel_all_timers()
            self.game_over("积分达到 5 分，很遗憾，AI 获胜！")
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
        elif self.current_player == self.human_color:
            if len(self.game.history) >= 2:
                self.cancel_all_timers()
                self.game.undo_move()
                self.game.undo_move()
                self.start_human_timer()

        color_str = "黑棋" if self.human_color == 1 else "白棋"
        self.status_var.set(f"玩家回合 ({color_str})")
        self.update_score_board()
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
        self.current_player = 1

        self.update_score_board()
        self.draw_2d_board()
        self.draw_3d_preview()
        color_str = "黑棋" if self.human_color == 1 else "白棋"

        if self.current_player == self.human_color:
            self.status_var.set(f"玩家回合 ({color_str})")
            self.start_human_timer()
        else:
            self.start_ai_wait_countdown(1)


# ==========================================
# 应用程序总控制器
# ==========================================
class GomokuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("融解与凝固：三维五子棋")
        self.root.geometry("1100x750")
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