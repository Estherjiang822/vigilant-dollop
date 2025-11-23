import chess

def forced_legal_moves(board):
    """Return legal moves under the forced-capture rule."""
    legal_moves = list(board.legal_moves)
    captures = [m for m in legal_moves if board.is_capture(m)]
    return captures if captures else legal_moves


def print_board(board):
    print(board, "\n")
    print("{} to move.".format("White" if board.turn else "Black"))
    forced_moves = forced_legal_moves(board)
    captures = [m for m in forced_moves if board.is_capture(m)]
    if captures:
        print("⚔️  Forced capture rule active — you must capture!")
    print("Available moves:", [board.san(m) for m in forced_moves])
    print()


def play_move(board, move_str):
    """Attempt to play a move (SAN or UCI) under forced-capture rules."""
    try:
        move = board.parse_san(move_str)
    except Exception:
        try:
            move = chess.Move.from_uci(move_str)
        except Exception:
            raise ValueError("Invalid move format. Use SAN (e.g. Nf3) or UCI (e.g. g1f3).")

    if move not in board.legal_moves:
        raise ValueError("Illegal move.")

    forced_moves = forced_legal_moves(board)
    if move not in forced_moves:
        raise ValueError("Captures are available — you must capture one!")

    board.push(move)


def main():
    print("Welcome to Forced Capture Chess")
    print("Rules: If a capture is available, you must make a capture.\n")

    board = chess.Board()

    while not board.is_game_over():
        print_board(board)
        move_str = input("Enter your move: ").strip()

        if move_str.lower() in {"quit", "exit"}:
            print("Game ended.")
            return
        elif move_str.lower() == "undo":
            if board.move_stack:
                board.pop()
                continue
            else:
                print("No moves to undo.")
                continue
        elif move_str.lower() == "help":
            print("Commands:")
            print("  undo - take back last move")
            print("  quit/exit - end the game")
            print("  help - show this message\n")
            continue

        try:
            play_move(board, move_str)
        except ValueError as e:
            print("Invalid Move: ", e)
            continue

    print_board(board)
    print("Game over:", board.result())


if __name__ == "__main__":
    main()
