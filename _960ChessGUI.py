import tkinter as tk
from PIL import Image, ImageTk
import chess
import chess.variant
import chess.engine
import chess.pgn
import datetime
import random
import os
import cairosvg
from itertools import combinations
import json
import threading

with open("config.json", "r") as f:
    config = json.load(f)

SQUARE_SIZE = 64
ASSET_PATH = "assets/"

input_folder = config["svg_input_folder"]
output_folder = config["png_output_folder"]

os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(input_folder):
    if filename.endswith(".svg"):
        name = os.path.splitext(filename)[0]
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, f"{name}.png")
        cairosvg.svg2png(url=input_path, write_to=output_path, output_width=64, output_height=64)
        print(f"Converted {filename} -> {name}.png")

class Chess960GUI:
    def __init__(self, root):
        self.root = root
        self.board = chess.Board(chess960=True)
        self.frame = tk.Frame(root)
        self.frame.pack()
        self.eval_canvas_left = tk.Canvas(self.frame, width=50, height=8*SQUARE_SIZE, bg="white", highlightthickness=0)
        self.eval_canvas_left.grid(row=0, column=0, sticky='ns')
        self.canvas = tk.Canvas(self.frame, width=8*SQUARE_SIZE, height=8*SQUARE_SIZE)
        self.canvas.grid(row=0, column=1)
        self.move_log = tk.Text(self.frame, width=30, height=30, state='disabled', bg="#eee", font=("Consolas", 10))
        self.move_log.grid(row=0, column=2, sticky='ns')
        self.eval_canvas_right = tk.Canvas(self.frame, width=50, height=8*SQUARE_SIZE, bg="white", highlightthickness=0)
        self.eval_canvas_right.grid(row=0, column=3, sticky='ns')
        tk.Button(self.root, text="New Game (Random SP)", command=self.reset_game).pack(pady=10)
        self.pieces = {}
        self.selected_square = None
        self.load_images()
        self.generate_chess960_position()
        self.draw_board()
        self.canvas.bind("<Button-1>", self.on_click)
        self.completed_games = []
        self.engine_list = config["engine_paths"]
        self.engine_white_path = self.engine_list["Stockfish"]
        self.engine_black_path = self.engine_list["Revenge"]
        self.engine_a = None
        self.engine_b = None
        self.engine_white = None
        self.engine_black = None
        self.engine_white = chess.engine.SimpleEngine.popen_uci(self.engine_white_path)
        if "clover" in self.engine_white.id.get("name", "").lower():
            if "UCI_Chess960" in self.engine_white.options:
                try:
                    self.engine_white.configure({"UCI_Chess960": True})
                    print("960 set to true")
                except chess.engine.EngineError:
                    print("Could not set 960 due to manual set error")
                    pass
        self.engine_black = chess.engine.SimpleEngine.popen_uci(self.engine_black_path)
        if "clover" in self.engine_black.id.get("name", "").lower():
            if "UCI_Chess960" in self.engine_black.options:
                try:
                    self.engine_black.configure({"UCI_Chess960": True})
                except chess.engine.EngineError:
                    pass
        tk.Button(self.root, text="Start Engine vs Engine", command=self.play_engine_vs_engine).pack(pady=5)
        tk.Button(self.root, text="Match Setup", command=self.open_match_setup).pack(pady=5)
        tk.Button(self.root, text="Tournament", command=self.open_tournament_setup).pack(pady=5)
        tk.Button(self.root, text="Test Engine Castling", command=self.open_castling_test_popup).pack(pady=5)


    def load_images(self):
        pieces = ['P', 'N', 'B', 'R', 'Q', 'K']
        colors = ['w', 'b']
        for color in colors:
            for piece in pieces:
                img_path = os.path.join(config["piece_path"], f"{color}{piece}.png")
                img = Image.open(img_path)
                self.pieces[color + piece] = ImageTk.PhotoImage(img.resize((SQUARE_SIZE, SQUARE_SIZE)))

    def generate_chess960_position(self):
        self.starting_sp = random.randint(0, 959)
        self.board = chess.Board.from_chess960_pos(self.starting_sp)
        print("SP:", self.starting_sp)
        print(self.board)

    def draw_board(self):
        self.canvas.delete("all")
        for rank in range(8):
            for file in range(8):
                x1 = file * SQUARE_SIZE
                y1 = rank * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE
                color = "#f0d9b5" if (rank + file) % 2 == 0 else "#b58863"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color)

                piece = self.board.piece_at(chess.square(file, 7 - rank))
                if piece:
                    key = ('w' if piece.color else 'b') + piece.symbol().upper()
                    self.canvas.create_image(x1, y1, anchor='nw', image=self.pieces[key])

    def open_castling_test_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Test Engine Castling")

        tk.Label(popup, text="Select Engine:").grid(row=0, column=0, sticky="w")
        engine_names = list(self.engine_list.keys())
        engine_var = tk.StringVar(value=engine_names[0])
        tk.OptionMenu(popup, engine_var, *engine_names).grid(row=0, column=1)

        tk.Label(popup, text="Number of Tests:").grid(row=1, column=0, sticky="w")
        num_var = tk.StringVar(value="1")
        tk.Entry(popup, textvariable=num_var).grid(row=1, column=1)

        def run_test():
            selected_engine = engine_var.get()
            try:
                count = int(num_var.get())
            except:
                count = 1
            popup.destroy()
            self.play_castling_test_game(selected_engine, count)

        tk.Button(popup, text="Run Test", command=run_test).grid(row=2, column=0, columnspan=2, pady=10)

    def open_match_setup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Match Setup")

        engine_names = list(self.engine_list.keys())

        tk.Label(popup, text="Engine A").grid(row=0, column=0, sticky='e')
        engine_a_var = tk.StringVar(value=engine_names[0])
        tk.OptionMenu(popup, engine_a_var, *engine_names).grid(row=0, column=1)

        tk.Label(popup, text="Engine B").grid(row=1, column=0, sticky='e')
        engine_b_var = tk.StringVar(value=engine_names[1] if len(engine_names) > 1 else engine_names[0])
        tk.OptionMenu(popup, engine_b_var, *engine_names).grid(row=1, column=1)

        tk.Label(popup, text="Engine A starts as:").grid(row=2, column=0, sticky='e')
        color_var = tk.StringVar(value="white")
        tk.Radiobutton(popup, text="White", variable=color_var, value="white").grid(row=2, column=1, sticky='w')
        tk.Radiobutton(popup, text="Black", variable=color_var, value="black").grid(row=2, column=2, sticky='w')

        tk.Label(popup, text="Time per move (seconds)").grid(row=3, column=0, sticky='e')
        time_entry = tk.Entry(popup)
        time_entry.insert(0, "1.0")
        time_entry.grid(row=3, column=1)

        tk.Label(popup, text="Number of rounds").grid(row=4, column=0, sticky='e')
        rounds_entry = tk.Entry(popup)
        rounds_entry.insert(0, "4")
        rounds_entry.grid(row=4, column=1)

        def confirm():
            try:
                engine_a_name = engine_a_var.get()
                engine_b_name = engine_b_var.get()

                self.match_settings = {
                    "engine_a_name": engine_a_name,
                    "engine_b_name": engine_b_name,
                    "engine_a_path": self.engine_list[engine_a_name],
                    "engine_b_path": self.engine_list[engine_b_name],
                    "engine_a_color": color_var.get(),
                    "time_per_move": float(time_entry.get()),
                    "rounds": int(rounds_entry.get()),
                    "current_round": 0,
                    "score": {"A": 0, "B": 0}
        }
                popup.destroy()
                self.start_match()
            except ValueError:
                tk.messagebox.showerror("Invalid input", "Please enter valid numbers for time and rounds.")

        tk.Button(popup, text="Start Match", command=confirm).grid(row=5, column=1, pady=10)

    def start_match(self, callback = None):
        self.match_callback = callback
        settings = self.match_settings

        if settings["engine_a_color"] == "white":
            self.engine_white = self.engine_a
            self.engine_black = self.engine_b
        else:
            self.engine_white = self.engine_b
            self.engine_black = self.engine_a

        self.engine_white_name = settings["engine_a_name"] if settings["engine_a_color"] == "white" else settings["engine_b_name"]
        self.engine_black_name = settings["engine_b_name"] if settings["engine_a_color"] == "white" else settings["engine_a_name"]

        self.engine_a_path = self.engine_list[settings["engine_a_name"]]
        self.engine_b_path = self.engine_list[settings["engine_b_name"]]

        self.engine_a = chess.engine.SimpleEngine.popen_uci(self.engine_a_path)
        self.engine_b = chess.engine.SimpleEngine.popen_uci(self.engine_b_path)

        self.match_settings["current_white"] = self.engine_white_name
        self.match_settings["current_black"] = self.engine_black_name

        self.engine_white = chess.engine.SimpleEngine.popen_uci(self.engine_list[self.engine_white_name])
        self.engine_black = chess.engine.SimpleEngine.popen_uci(self.engine_list[self.engine_black_name])
            
        self.match_settings["current_round"] = 1
        self.play_single_round()

    def play_single_round(self):
        round_num = self.match_settings["current_round"]
        total_rounds = self.match_settings["rounds"]

        print(f"Starting Round {round_num}/{total_rounds}")
        self.safe_quit_engine(self.engine_white, label="White")
        self.safe_quit_engine(self.engine_black, label="Black")

        white_name = self.match_settings["current_white"]
        black_name = self.match_settings["current_black"]

        self.engine_white = chess.engine.SimpleEngine.popen_uci(self.engine_list[white_name])
        self.engine_black = chess.engine.SimpleEngine.popen_uci(self.engine_list[black_name])
        self.engine_white_name = self.match_settings["current_white"]
        self.engine_black_name = self.match_settings["current_black"]
        self.generate_chess960_position()
        self.draw_board()
        self.update_move_log()

        self.root.after(300, self.play_engine_turn)

    def positions_with_king_on(self, file_letter: str):
        file_index = ord(file_letter.lower()) - ord('a')
        matches = []

        for sp in range(960):
            board = chess.Board.from_chess960_pos(sp)
            king_square = board.king(chess.WHITE)
            if chess.square_file(king_square) == file_index:
                matches.append(sp)

        return matches

    def play_castling_test_game(self, engine_name, count=1):
        engine_path = self.engine_list[engine_name]
        sp_candidates = self.positions_with_king_on('g') + self.positions_with_king_on('c')
        test_sps = random.sample(sp_candidates, min(count, len(sp_candidates)))

        def play_game(sp):
            self.starting_sp = sp
            self.board = chess.Board.from_chess960_pos(sp)
            self.draw_board()
            self.update_move_log()

            engine = chess.engine.SimpleEngine.popen_uci(engine_path)
            if "clover" in engine.id.get("name", "").lower():
                if "UCI_Chess960" in engine.options:
                    try:
                        engine.configure({"UCI_Chess960": True})
                        print("960 set to true")
                    except chess.engine.EngineError:
                        print("Could not set 960 due to manual set error")
                        pass
            self.engine_white = engine
            self.engine_black = engine
            self.engine_white_name = engine_name
            self.engine_black_name = engine_name

            self.match_settings = {
                "engine_a_name": engine_name,
                "engine_b_name": engine_name,
                "engine_a_path": engine_path,
                "engine_b_path": engine_path,
                "engine_a_color": "white",
                "time_per_move": 0.2,
                "rounds": 1,
                "current_round": 1,
                "score": {"A": 0, "B": 0},
                "current_white": engine_name,
                "current_black": engine_name
        }

            self.root.after(300, self.play_engine_turn)

        threading.Thread(target=lambda: play_game(test_sps[0]), daemon=True).start()


    def play_engine_turn(self):
        if self.board.is_game_over():
            self.handle_round_end()
            return

        current_engine = self.engine_white if self.board.turn == chess.WHITE else self.engine_black
        move_time = self.match_settings["time_per_move"]

        def run_engine():
            try:
                board_copy = chess.Board(self.board.fen(), chess960=True)
                result = current_engine.play(board_copy, chess.engine.Limit(time=move_time))
                self.root.after(0, lambda: self.apply_engine_move(result.move))
            except Exception as e:
                print("Engine failed:", e)

        threading.Thread(target=run_engine, daemon=True).start()
        
    def apply_engine_move(self, move):
        self.board.push(move)
        self.update_move_log()
        self.draw_board()
        self.update_eval_bars()
        self.root.after(200, self.play_engine_turn)

    def handle_round_end(self):
        res = self.board.result()
        white_name = self.match_settings["current_white"]
        black_name = self.match_settings["current_black"]

        print(f"\n--- Round {self.match_settings['current_round']} Complete ---")
        print(f"Result: {white_name} (White) vs {black_name} (Black) - {res}")

        if res == "1-0":
            winner = "white"
        elif res == "0-1":
            winner = "black"
        else:
            winner = "draw"

        white = self.match_settings["current_white"]
        black = self.match_settings["current_black"]

        if winner == "white":
            self.tournament["scores"][white] += 1
        elif winner == "black":
            self.tournament["scores"][black] += 1
        else:
            self.tournament["scores"][white] += 0.5
            self.tournament["scores"][black] += 0.5

        self.match_settings["current_white"] = self.engine_white_name
        self.match_settings["current_black"] = self.engine_black_name

        self.engine_a = self.engine_list[self.match_settings["engine_a_name"]]
        self.engine_b = self.engine_list[self.match_settings["engine_b_name"]]

        print(f"Score: {white}: {self.tournament['scores'][white]} | {black}: {self.tournament['scores'][black]}")
        
        tournament_name = None
        if self.match_callback:
            tournament_name = f"{self.tournament['type'].capitalize()}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        game = self.build_game_pgn(tournament_name=tournament_name)
        self.save_game_to_pgn(game, is_tournament=bool(self.match_callback), tournament_name=tournament_name)


        self.safe_quit_engine(self.engine_white, label="White")
        self.safe_quit_engine(self.engine_black, label="Black")

        self.engine_white = chess.engine.SimpleEngine.popen_uci(
            self.match_settings["engine_a_path"] if self.match_settings["current_white"] == self.match_settings["engine_a_name"]
            else self.match_settings["engine_b_path"]
)

        self.engine_black = chess.engine.SimpleEngine.popen_uci(
            self.match_settings["engine_a_path"] if self.match_settings["current_black"] == self.match_settings["engine_a_name"]
            else self.match_settings["engine_b_path"]
)

        self.match_settings["current_round"] += 1
        if self.match_settings["current_round"] <= self.match_settings["rounds"]:
            prev_white = self.match_settings["current_white"]
            prev_black = self.match_settings["current_black"]

            self.match_settings["current_white"] = prev_black
            self.match_settings["current_black"] = prev_white

            self.engine_white = chess.engine.SimpleEngine.popen_uci(
                self.engine_list[self.match_settings["current_white"]]
            )
            self.engine_black = chess.engine.SimpleEngine.popen_uci(
                self.engine_list[self.match_settings["current_black"]]
            )

            self.root.after(1000, self.play_single_round)
        else:
            print("\nMatch complete!")
            print("Final Score:")
            for name, score in self.tournament["scores"].items():
                print(f"  {name}: {score}")

            if self.match_callback:
                tournament_name = f"{self.tournament['type'].capitalize()}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                game = self.build_game_pgn(tournament_name=tournament_name)
                self.save_game_to_pgn(game, is_tournament=bool(self.match_callback), tournament_name=tournament_name)

                self.safe_quit_engine(self.engine_a, label="A")
                self.safe_quit_engine(self.engine_b, label="B")
                self.root.after(500, self.match_callback)
            else:
                game = self.build_game_pgn()
                self.save_game_to_pgn(game)
                self.safe_quit_engine(self.engine_a, label="A")
                self.safe_quit_engine(self.engine_b, label="B")

    def open_tournament_setup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Tournament Setup")

        engine_names = list(self.engine_list.keys())
        selected_engines = []

        tk.Label(popup, text="Select Engines:").grid(row=0, column=0, sticky="w")
        for i, name in enumerate(engine_names):
            var = tk.BooleanVar()
            cb = tk.Checkbutton(popup, text=name, variable=var)
            cb.grid(row=i + 1, column=0, sticky="w")
            selected_engines.append((name, var))

        tk.Label(popup, text="Tournament Type:").grid(row=0, column=1, sticky="w")
        format_var = tk.StringVar(value="round_robin")
        tk.Radiobutton(popup, text="Round Robin", variable=format_var, value="round_robin").grid(row=1, column=1, sticky="w")
        tk.Radiobutton(popup, text="Swiss", variable=format_var, value="swiss").grid(row=2, column=1, sticky="w")

        tk.Label(popup, text="Rounds per pairing:").grid(row=3, column=1, sticky="w")
        rounds_entry = tk.Entry(popup)
        rounds_entry.insert(0, "2")
        rounds_entry.grid(row=4, column=1)

        tk.Label(popup, text="Time per move (s):").grid(row=5, column=1, sticky="w")
        time_entry = tk.Entry(popup)
        time_entry.insert(0, "1.0")
        time_entry.grid(row=6, column=1)

        def start_tournament():
            chosen = [name for name, var in selected_engines if var.get()]
            if len(chosen) < 2:
                tk.messagebox.showerror("Error", "Select at least two engines.")
                return
            try:
                settings = {
                    "engines": chosen,
                    "type": format_var.get(),
                    "rounds_per_pairing": int(rounds_entry.get()),
                    "time_per_move": float(time_entry.get())
            }
                popup.destroy()
                self.run_tournament(settings)
            except ValueError:
                tk.messagebox.showerror("Invalid Input", "Rounds and time must be valid numbers.")

        tk.Button(popup, text="Start Tournament", command=start_tournament).grid(row=7, column=1, pady=10)

    def safe_quit_engine(self, engine, label=""):
        try:
            engine.quit()
        except Exception as e:
            print(f"[{label}] Engine quit failed: {e}")
            try:
                engine.kill()
                print(f"[{label}] Engine killed successfully.")
            except Exception as kill_err:
                print(f"[{label}] Engine kill also failed: {kill_err}")


    def engine_move(self):
        if self.board.is_game_over():
            print("Game over:", self.board.result())
            return

        engine = self.engine_white if self.board.turn == chess.WHITE else self.engine_black
        result = engine.play(self.board, chess.engine.Limit(time=0.5))
        self.board.push(result.move)
        self.draw_board()
        self.update_move_log()
        
    def play_engine_vs_engine(self):
        if self.board.is_game_over():
            print("Game over:", self.board.result())
            return

        engine = self.engine_white if self.board.turn == chess.WHITE else self.engine_black

        result = engine.play(self.board, chess.engine.Limit(time=0.3))
        self.board.push(result.move)

        self.update_move_log()
        self.draw_board()

        self.root.after(300, self.play_engine_vs_engine)

    def update_move_log(self):
        self.move_log.configure(state='normal')
        self.move_log.delete(1.0, tk.END)

        temp_board = chess.Board.from_chess960_pos(self.starting_sp)
        moves = list(self.board.move_stack)
        lines = []

        for i in range(0, len(moves), 2):
            move_number = i // 2 + 1
            white_move = temp_board.san(moves[i])
            temp_board.push(moves[i])
            black_move = ""
            if i + 1 < len(moves):
                black_move = temp_board.san(moves[i+1])
                temp_board.push(moves[i+1])
            lines.append(f"{move_number}. {white_move} {black_move}")

        self.move_log.insert(tk.END, "\n".join(lines))
        self.move_log.configure(state='disabled')
        self.move_log.see(tk.END)
                    
    def update_eval_bars(self):
        board_copy = chess.Board(self.board.fen(), chess960=True)
        limit = chess.engine.Limit(time=0.1)

        def get_eval(engine):
            try:
                info = engine.analyse(board_copy, limit)
                return info["score"].white().score(mate_score=10000)
            except:
                return 0

        eval_white = get_eval(self.engine_white)
        eval_black = get_eval(self.engine_black)

        self.draw_eval_bar(self.eval_canvas_left, eval_white, self.engine_white_name)
        self.draw_eval_bar(self.eval_canvas_right, eval_black, self.engine_black_name)


    def draw_eval_bar(self, canvas, eval_score, engine_name):
        canvas.delete("all")
        canvas_height = 8 * SQUARE_SIZE
        center = canvas_height // 2

        score = max(min(eval_score, 1000), -1000)
        height = int((score + 1000) / 2000 * canvas_height)
        bar_color = "#4CAF50" if score > 0 else "#F44336" if score < 0 else "#888"

        canvas.create_rectangle(0, 0, 50, canvas_height, fill="#ddd", width=0)
        canvas.create_rectangle(10, canvas_height - height, 40, canvas_height, fill=bar_color)

        canvas.create_text(25, 15, text=engine_name, font=("Consolas", 9, "bold"))

        eval_text = "0.00" if eval_score == 0 else f"{eval_score/100:.2f}"
        canvas.create_text(25, canvas_height - height - 10, text=eval_text, font=("Consolas", 10))

    def run_tournament(self, settings):
        os.makedirs("SavedGames", exist_ok=True)
        self.tournament = {
            "type": settings["type"],
            "engines": settings["engines"],
            "rounds_per_pairing": settings["rounds_per_pairing"],
            "time_per_move": settings["time_per_move"],
            "scores": {name: 0 for name in settings["engines"]},
            "pairings": [],
            "current_match_index": 0,
             "pgn_filename": os.path.join("SavedGames", f"{settings['type'].capitalize()}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pgn")
    }

        pairings = list(combinations(settings["engines"], 2))
        expanded_pairings = []

        for a, b in pairings:
            for i in range(settings["rounds_per_pairing"]):
                if i % 2 == 0:
                    expanded_pairings.append((a, b))
                else:
                    expanded_pairings.append((b, a))
        random.shuffle(expanded_pairings)
        self.tournament["pairings"] = expanded_pairings

        self.play_next_tournament_match()

    def play_next_tournament_match(self):
        tournament = self.tournament
        if tournament["current_match_index"] >= len(tournament["pairings"]):
            self.end_tournament()
            return

        white, black = tournament["pairings"][tournament["current_match_index"]]
        print(f"Starting match: {white} (White) vs {black} (Black)")

        self.match_settings = {
            "engine_a_name": white,
            "engine_b_name": black,
            "engine_a_path": self.engine_list[white],
            "engine_b_path": self.engine_list[black],
            "engine_a_color": "white",
            "time_per_move": tournament["time_per_move"],
            "rounds": self.tournament["rounds_per_pairing"],
            "current_round": 1,
            "score": {"A": 0, "B": 0}
    }
        self.tournament["current_match_index"] += 1
        self.start_match(callback=self.play_next_tournament_match)

    def end_tournament(self):
        print("Tournament Complete!")
        self.safe_quit_engine(self.engine_a, label="A")
        self.safe_quit_engine(self.engine_b, label="B")
        sorted_scores = sorted(self.tournament["scores"].items(), key=lambda x: -x[1])
        for name, score in sorted_scores:
            print(f"{name}: {score} pts")

    def build_game_pgn(self, tournament_name=None):
        game = chess.pgn.Game()
        game.headers["Event"] = tournament_name if tournament_name else "Engine Match"
        game.headers["Site"] = "Chess960 GUI"
        game.headers["Date"] = datetime.datetime.now().strftime("%Y.%m.%d")
        game.headers["Round"] = str(self.match_settings["current_round"] - 1)
        game.headers["White"] = self.match_settings["current_white"]
        game.headers["Black"] = self.match_settings["current_black"]
        game.headers["Result"] = self.board.result()
        game.headers["FEN"] = chess.Board.from_chess960_pos(self.starting_sp).fen()
        game.headers["Variant"] = "Chess960"
        game.headers["Startpos"] = str(self.starting_sp)

        node = game
        board = chess.Board.from_chess960_pos(self.starting_sp)
        for move in self.board.move_stack:
            node = node.add_variation(move)
            board.push(move)

        return game

    def reset_game(self):
        self.generate_chess960_position()
        self.draw_board()
        self.update_move_log()
        self.selected_square = None

                    
    def on_click(self, event):
        file = event.x // SQUARE_SIZE
        rank = 7 - (event.y // SQUARE_SIZE)
        square = chess.square(file, rank)

        if self.selected_square is None:
            piece = self.board.piece_at(square)
            if piece and piece.color == self.board.turn:
                self.selected_square = square
        else:
            move = chess.Move(self.selected_square, square)
            if move in self.board.legal_moves:
                    self.board.push(move)
                    self.update_move_log()
                    self.draw_board()

                    self.root.after(100, self.engine_move)
            self.selected_square = None
            self.draw_board()
            
    def save_game_to_pgn(self, game, is_tournament=False, tournament_name=None):
        os.makedirs("SavedGames", exist_ok=True)

        if is_tournament and self.tournament and "pgn_filename" in self.tournament:
            full_filename = self.tournament["pgn_filename"]
        else:
            full_filename = os.path.join("SavedGames", "engine_vs_engine_matches.pgn")

        with open(full_filename, "a", encoding="utf-8") as f:
            print(game, file=f)

        print(f"Game saved to {full_filename}")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Chess960 GUI")
    gui = Chess960GUI(root)
    root.mainloop()

