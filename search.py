import chess
from evaluate import evaluate
from transposition import Transposition_Table
from forced_chess import forced_legal_moves

TT = Transposition_Table(size=100000)

# Max Player = True means the player is playing White pieces
# Max Player = False means the player is playing Black pieces
def minimax(board: chess.Board, depth, alpha, beta, max_player):
    # Transposition Table Logic
    alpha_orig = alpha
    beta_orig = beta

    entry = TT.lookup(board)
    if entry and entry.depth >= depth:
        if entry.flag == "EXACT":
            return entry.score
        elif entry.flag == "UPPERBOUND":
            beta = min(beta, entry.score)
        elif entry.flag == "LOWERBOUND":
            alpha = max(alpha, entry.score)

        if alpha >= beta:
            return entry.score


    if depth == 0 or board.is_game_over():
        return evaluate(board) 

    if max_player:
        m_eval = -float("inf")
        for move in forced_legal_moves(board):
            board.push(move)
            evaluation = minimax(board, depth - 1, alpha, beta, False)
            board.pop()

            m_eval = max(m_eval, evaluation)
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
    
    else:
        m_eval = float("inf")
        for move in forced_legal_moves(board):
            board.push(move)
            evaluation = minimax(board, depth - 1, alpha, beta, True)
            board.pop()

            m_eval = min(m_eval, evaluation)
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
    
    if m_eval <= alpha_orig:
        flag = "UPPERBOUND"
    elif m_eval >= beta_orig:
        flag = "LOWERBOUND"
    else:
        flag = "EXACT"

    TT.store(board, depth, m_eval, flag, best_move=None)

    return m_eval