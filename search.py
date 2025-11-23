import chess
import math
from evaluate import evaluate

def minimax(pos, depth, alpha, beta, max_player):
    if depth == 0 or evaluate(pos) == False: # ig we make evaluate(checkmate position) = False? for now at least
        return evaluate(pos) 
    
    if max_player:
        max_eval = -math.inf
        for child in pos:
            evaluation = minimax(child, depth - 1, alpha, beta, False)
            max_eval = max(max_eval, evaluation)
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        return max_eval
    
    else:
        min_eval = math.inf
        for child in pos:
            evaluation = minimax(child, depth - 1, alpha, beta, True)
            min_eval = min(min_eval, evaluation)
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval