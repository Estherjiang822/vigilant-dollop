import chess
from evaluate import evaluate

# Max Player = True means the player is playing White pieces
# Max Player = False means the player is playing Black pieces
def minimax(board, depth, alpha, beta, max_player):
    if depth == 0 or board.is_game_over():
        return evaluate(board) 
    
    if max_player:
        max_eval = -float("inf")
        for child in board:
            evaluation = minimax(child, depth - 1, alpha, beta, False)
            max_eval = max(max_eval, evaluation)
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        return max_eval
    
    else:
        min_eval = float("inf")
        for child in board:
            evaluation = minimax(child, depth - 1, alpha, beta, True)
            min_eval = min(min_eval, evaluation)
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval