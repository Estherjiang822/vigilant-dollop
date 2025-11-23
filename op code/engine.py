#!/usr/bin/env python3
"""
XBoard/WinBoard Protocol Engine for Forced Capture Chess
强制吃子国际象棋的XBoard协议引擎

这是整个引擎的主入口点，实现了XBoard通信协议（也称CECP协议）。

【什么是XBoard协议】
XBoard是一个标准的国际象棋GUI和引擎之间的通信协议。
引擎通过stdin接收命令，通过stdout发送响应。
这种设计使得引擎可以与任何支持XBoard协议的GUI配合使用。

【比赛中的工作流程】
1. 比赛系统启动引擎：xboard -fcp "./run.sh"
2. 引擎接收命令：xboard, protover, new, go, usermove等
3. 引擎计算并返回走法：move e2e4
4. 循环直到游戏结束

使用方式：
    python engine.py

与xboard配合：
    xboard -fcp "python3 engine.py"

协议文档: https://www.gnu.org/software/xboard/engine-intf.html
"""

import sys
import chess
import time
from typing import Optional

from forced_capture import get_legal_moves_with_forced_capture
from search import ChessSearcher, SearchResult
from evaluate import evaluate


# ============================================================================
# XBoard协议引擎主类
# ============================================================================

class ForcedCaptureEngine:
    """
    XBoard协议引擎 - 比赛的主程序
    XBoard protocol engine for forced capture chess

    这个类负责：
    1. 解析XBoard协议命令
    2. 维护棋盘状态
    3. 调用搜索算法找到最佳走法
    4. 管理时间控制
    """

    def __init__(self):
        """初始化引擎"""
        self.board = chess.Board()          # 棋盘状态
        self.searcher = ChessSearcher()     # 搜索引擎
        self.force_mode = False             # 强制模式（不自动走棋）
        self.time_left = 60000              # 剩余时间（厘秒，即60秒）
        self.opponent_time = 60000          # 对手剩余时间
        self.moves_to_go = 40               # 到下次时间控制的步数
        self.engine_color = chess.BLACK     # 引擎执黑（默认）
        self.debug = False                  # 调试模式

    def log(self, message: str):
        """Log debug messages (only shown if debug mode is on)"""
        if self.debug:
            print(f"# {message}", flush=True)

    def send(self, message: str):
        """Send a message to XBoard"""
        print(message, flush=True)
        self.log(f"Sent: {message}")

    def handle_xboard(self):
        """Handle 'xboard' command"""
        self.log("Entering XBoard mode")
        # Just acknowledge, no response needed

    def handle_protover(self, version: str):
        """Handle 'protover' command"""
        self.log(f"Protocol version: {version}")

        # Declare engine features
        features = [
            "feature myname=\"ForcedCaptureChess v1.0\"",
            "feature setboard=1",
            "feature ping=1",
            "feature usermove=1",
            "feature time=1",
            "feature colors=0",
            "feature analyze=0",
            "feature variants=\"normal\"",
            "feature done=1"
        ]

        for feature in features:
            self.send(feature)

    def handle_ping(self, n: str):
        """Handle 'ping' command"""
        self.send(f"pong {n}")

    def handle_new(self):
        """Handle 'new' command - start new game"""
        self.log("Starting new game")
        self.board = chess.Board()
        self.force_mode = False
        self.engine_color = chess.BLACK  # Engine plays Black in new game
        self.time_left = 60000
        self.opponent_time = 60000

    def handle_quit(self):
        """Handle 'quit' command"""
        self.log("Quitting")
        sys.exit(0)

    def handle_force(self):
        """Handle 'force' command - enter force mode"""
        self.log("Entering force mode")
        self.force_mode = True

    def handle_go(self):
        """Handle 'go' command - engine should move now"""
        self.log("Leaving force mode, engine to move")
        self.force_mode = False
        self.engine_color = self.board.turn
        self.make_move()

    def handle_usermove(self, move_str: str):
        """Handle 'usermove' command"""
        self.log(f"User move: {move_str}")

        try:
            # Parse the move
            move = chess.Move.from_uci(move_str)

            # Validate it's legal under forced capture rules
            legal_moves = get_legal_moves_with_forced_capture(self.board)

            if move not in legal_moves:
                self.send(f"Illegal move: {move_str}")
                return

            # Make the move
            self.board.push(move)

            # If not in force mode and it's our turn, make a move
            if not self.force_mode and self.board.turn == self.engine_color:
                self.make_move()

        except Exception as e:
            self.send(f"Error: {e}")
            self.log(f"Error parsing move {move_str}: {e}")

    def handle_time(self, time_str: str):
        """Handle 'time' command - our remaining time"""
        try:
            self.time_left = int(time_str)
            self.log(f"Our time: {self.time_left} centiseconds")
        except ValueError:
            self.log(f"Invalid time: {time_str}")

    def handle_otim(self, time_str: str):
        """Handle 'otim' command - opponent's remaining time"""
        try:
            self.opponent_time = int(time_str)
            self.log(f"Opponent time: {self.opponent_time} centiseconds")
        except ValueError:
            self.log(f"Invalid time: {time_str}")

    def handle_setboard(self, fen: str):
        """Handle 'setboard' command - set position from FEN"""
        try:
            self.board = chess.Board(fen)
            self.log(f"Board set to: {fen}")
        except Exception as e:
            self.send(f"Error: {e}")
            self.log(f"Error setting board: {e}")

    def handle_level(self, moves: str, base_time: str, increment: str):
        """Handle 'level' command - set time control"""
        try:
            self.moves_to_go = int(moves)
            # base_time is in minutes or minutes:seconds
            if ':' in base_time:
                minutes, seconds = base_time.split(':')
                time_in_seconds = int(minutes) * 60 + int(seconds)
            else:
                time_in_seconds = int(base_time) * 60

            self.time_left = time_in_seconds * 100  # Convert to centiseconds
            self.log(f"Time control: {moves} moves in {time_in_seconds}s + {increment}s increment")
        except Exception as e:
            self.log(f"Error parsing level: {e}")

    def calculate_time_for_move(self) -> float:
        """Calculate how much time to use for this move"""
        # Simple time management: divide remaining time by expected moves
        time_in_seconds = self.time_left / 100.0

        if self.moves_to_go > 0:
            # Use 1/N of remaining time, where N is moves to go
            time_for_move = time_in_seconds / (self.moves_to_go + 5)
        else:
            # No moves to go specified, use 1/40 of time (assume 40 moves left)
            time_for_move = time_in_seconds / 40

        # Ensure minimum and maximum time
        time_for_move = max(0.1, min(time_for_move, time_in_seconds * 0.3))

        self.log(f"Allocated {time_for_move:.2f}s for this move")
        return time_for_move

    def make_move(self):
        """Make the engine's move"""
        # Check if game is over
        if self.board.is_game_over():
            self.log("Game is over")
            return

        # Get legal moves under forced capture rules
        legal_moves = get_legal_moves_with_forced_capture(self.board)

        if not legal_moves:
            self.log("No legal moves available")
            return

        # If only one legal move, play it immediately
        if len(legal_moves) == 1:
            best_move = legal_moves[0]
            self.log(f"Only one legal move: {best_move}")
        else:
            # Calculate time for move
            time_for_move = self.calculate_time_for_move()

            # Search for best move
            self.log(f"Searching with time limit {time_for_move:.2f}s...")
            result = self.searcher.search(self.board, time_limit=time_for_move)

            best_move = result.best_move

            if best_move is None:
                # Fallback: pick first legal move
                best_move = legal_moves[0]
                self.log("Search returned no move, using first legal move")
            else:
                self.log(f"Search result: move={best_move}, score={result.score}, "
                        f"depth={result.depth}, nodes={result.nodes_searched}")

        # Make the move
        self.board.push(best_move)

        # Send the move to XBoard
        self.send(f"move {best_move.uci()}")

        # Check if game is over after our move
        if self.board.is_checkmate():
            # Opponent is checkmated
            result = "1-0" if self.board.turn == chess.BLACK else "0-1"
            self.send(f"{result} {{Checkmate}}")
        elif self.board.is_stalemate():
            self.send("1/2-1/2 {Stalemate}")
        elif self.board.is_insufficient_material():
            self.send("1/2-1/2 {Insufficient material}")
        elif self.board.can_claim_draw():
            self.send("1/2-1/2 {Draw by repetition or 50-move rule}")

    def run(self):
        """Main event loop"""
        self.log("Forced Capture Chess Engine starting...")

        while True:
            try:
                # Read command from stdin
                line = sys.stdin.readline()

                if not line:
                    break

                line = line.strip()

                if not line:
                    continue

                self.log(f"Received: {line}")

                # Parse command
                parts = line.split()
                command = parts[0]

                # Handle commands
                if command == "xboard":
                    self.handle_xboard()

                elif command == "protover":
                    self.handle_protover(parts[1])

                elif command == "ping":
                    self.handle_ping(parts[1])

                elif command == "new":
                    self.handle_new()

                elif command == "quit":
                    self.handle_quit()

                elif command == "force":
                    self.handle_force()

                elif command == "go":
                    self.handle_go()

                elif command == "usermove":
                    self.handle_usermove(parts[1])

                elif command == "time":
                    self.handle_time(parts[1])

                elif command == "otim":
                    self.handle_otim(parts[1])

                elif command == "setboard":
                    # FEN is rest of line after "setboard "
                    fen = line[9:]
                    self.handle_setboard(fen)

                elif command == "level":
                    if len(parts) >= 4:
                        self.handle_level(parts[1], parts[2], parts[3])

                elif command == "?":
                    # Move now
                    self.log("Move now requested")
                    if not self.force_mode:
                        self.searcher.stop_search = True

                elif command == "result":
                    # Game result reported
                    self.log(f"Game result: {' '.join(parts[1:])}")

                elif command == "white":
                    self.engine_color = chess.BLACK
                    self.log("Engine plays Black")

                elif command == "black":
                    self.engine_color = chess.WHITE
                    self.log("Engine plays White")

                else:
                    # Try to parse as a move (some GUIs don't send "usermove")
                    try:
                        move = chess.Move.from_uci(command)
                        self.handle_usermove(command)
                    except:
                        self.log(f"Unknown command: {command}")

            except Exception as e:
                self.log(f"Error in main loop: {e}")
                import traceback
                self.log(traceback.format_exc())


if __name__ == "__main__":
    engine = ForcedCaptureEngine()
    engine.run()
