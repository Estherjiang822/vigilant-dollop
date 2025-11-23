"""
Position Evaluation Function for Forced Capture Chess
强制吃子国际象棋的局面评估函数

本模块实现静态评估函数，为棋盘局面分配分数。
评估函数是国际象棋引擎的核心组件之一，用于判断局面的优劣。

评估考虑以下因素：
1. 子力平衡（Material balance）- 双方棋子的总价值差
2. 棋子位置（Piece positioning）- 棋子占据的格子好坏
3. 国王安全（King safety）- 国王周围的防护情况
4. 棋子暴露（Piece exposure）- 【强制吃子变体特有】无防守棋子的风险
5. 战术机会（Tactical opportunities）- 强制吃子序列的机会

评分规则：
- 正分：白方优势
- 负分：黑方优势
- 零分：局面均势

This module implements the static evaluation function that assigns
a score to chess positions. The evaluation is adapted for the forced
capture variant.
"""

import chess
from typing import Dict, Tuple


# ============================================================================
# 棋子价值定义（单位：厘兵，即1兵=100）
# ============================================================================

# 标准棋子价值 - 这是国际象棋程序设计中的经典数值
PIECE_VALUES = {
    chess.PAWN: 100,      # 兵
    chess.KNIGHT: 320,    # 马（略高于3兵，因为马的跳跃能力）
    chess.BISHOP: 330,    # 象（双象加成，略高于马）
    chess.ROOK: 500,      # 车
    chess.QUEEN: 900,     # 后
    chess.KING: 20000     # 王（极大值，失去国王=输棋）
}


# ============================================================================
# 棋子-格子表（Piece-Square Tables）
# ============================================================================
# 这些表格鼓励棋子占据好的位置
# 例如：马在中心强，兵在推进时更有价值
# 表格从白方视角，黑方需要垂直翻转

PAWN_TABLE = [
    0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5,  5, 10, 25, 25, 10,  5,  5,
    0,  0,  0, 20, 20,  0,  0,  0,
    5, -5,-10,  0,  0,-10, -5,  5,
    5, 10, 10,-20,-20, 10, 10,  5,
    0,  0,  0,  0,  0,  0,  0,  0
]

KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]

ROOK_TABLE = [
    0,  0,  0,  0,  0,  0,  0,  0,
    5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    0,  0,  0,  5,  5,  0,  0,  0
]

QUEEN_TABLE = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
    -5,  0,  5,  5,  5,  5,  0, -5,
    0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
]

KING_MIDDLE_GAME_TABLE = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
    20, 20,  0,  0,  0,  0, 20, 20,
    20, 30, 10,  0,  0, 10, 30, 20
]

KING_END_GAME_TABLE = [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50
]

PIECE_SQUARE_TABLES = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
    chess.KING: KING_MIDDLE_GAME_TABLE  # Will switch to endgame in endgame
}


# ============================================================================
# 评估函数组件
# ============================================================================

def evaluate_material(board: chess.Board) -> int:
    """
    评估子力平衡
    Evaluate material balance.

    这是最基本的评估：计算双方所有棋子的价值差。
    子力优势通常意味着局面优势。

    返回 Returns:
        子力分数（正值=白方优势，负值=黑方优势）
    """
    score = 0

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None:
            value = PIECE_VALUES[piece.piece_type]
            if piece.color == chess.WHITE:
                score += value
            else:
                score -= value

    return score


def evaluate_piece_square_tables(board: chess.Board, is_endgame: bool = False) -> int:
    """
    使用棋子-格子表评估棋子位置
    Evaluate piece positioning using piece-square tables.

    不同的格子对不同的棋子有不同的价值。
    例如：马在中心d4/e4/d5/e5更强，边缘较弱。

    参数 Args:
        board: 当前局面
        is_endgame: 是否使用残局国王表（残局时国王应该活跃）

    返回 Returns:
        位置分数（正值=白方位置好，负值=黑方位置好）
    """
    score = 0

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue

        piece_type = piece.piece_type

        # Select the appropriate table
        if piece_type == chess.KING and is_endgame:
            table = KING_END_GAME_TABLE
        else:
            table = PIECE_SQUARE_TABLES.get(piece_type, [0] * 64)

        # Get the square index
        # For white, use square directly
        # For black, flip vertically (rank 1 <-> rank 8)
        if piece.color == chess.WHITE:
            table_index = square
            score += table[table_index]
        else:
            # Flip the square vertically for black
            table_index = chess.square_mirror(square)
            score -= table[table_index]

    return score


def evaluate_exposure(board: chess.Board) -> int:
    """
    评估棋子暴露度（强制吃子变体的关键评估项）
    Evaluate piece exposure (critical for forced capture variant).

    【强制吃子变体特有】
    在强制吃子规则下，暴露的棋子非常危险！
    因为对手如果能吃，就必须吃，所以：
    - 无防守的棋子 = 几乎必丢
    - 防守不足的棋子 = 可能被换子

    返回 Returns:
        暴露惩罚分（己方棋子暴露时为负分）
    """
    score = 0

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None or piece.piece_type == chess.KING:
            continue

        # Check if this piece is attacked
        is_attacked_by_opponent = board.is_attacked_by(not piece.color, square)
        is_defended = board.is_attacked_by(piece.color, square)

        if is_attacked_by_opponent:
            piece_value = PIECE_VALUES[piece.piece_type]

            if not is_defended:
                # Undefended piece - very bad in forced capture variant!
                penalty = piece_value // 2
            else:
                # Defended but attacked - still risky
                penalty = piece_value // 10

            if piece.color == chess.WHITE:
                score -= penalty
            else:
                score += penalty

    return score


def evaluate_king_safety(board: chess.Board) -> int:
    """
    评估国王安全
    Evaluate king safety.

    在强制吃子变体中，暴露的国王特别危险，
    因为弃子攻击可以强制把国王引入开放位置。

    评估方式：计算国王周围8格被对方攻击的数量

    返回 Returns:
        国王安全分数（正值=白方国王更安全）
    """
    score = 0

    for color in [chess.WHITE, chess.BLACK]:
        king_square = board.king(color)
        if king_square is None:
            continue

        # Count attackers around the king
        king_zone = []
        rank = chess.square_rank(king_square)
        file = chess.square_file(king_square)

        for dr in [-1, 0, 1]:
            for df in [-1, 0, 1]:
                if dr == 0 and df == 0:
                    continue
                new_rank, new_file = rank + dr, file + df
                if 0 <= new_rank <= 7 and 0 <= new_file <= 7:
                    king_zone.append(chess.square(new_file, new_rank))

        # Count how many squares around king are attacked by opponent
        attacks_on_king_zone = sum(
            1 for sq in king_zone
            if board.is_attacked_by(not color, sq)
        )

        # Penalize for attacks around king
        safety_penalty = attacks_on_king_zone * 20

        if color == chess.WHITE:
            score -= safety_penalty
        else:
            score += safety_penalty

    return score


def evaluate_forced_capture_tactics(board: chess.Board) -> int:
    """
    评估强制吃子变体特有的战术机会
    Evaluate tactical opportunities specific to forced capture variant.

    【强制吃子变体战术】
    在这个变体中，弃子战术特别重要：
    - 用低价值棋子攻击高价值棋子
    - 对手被迫吃子后可能陷入不利位置
    - 可以通过连续弃子创造将死机会

    返回 Returns:
        战术分数
    """
    score = 0

    # Check if current player can force opponent to make bad captures
    from forced_capture import has_forced_captures

    # Simulate: if opponent has forced captures, that might be good for us
    # (we set up a sacrifice trap)

    # Make a null move to check opponent's options
    # (This is a simplified heuristic)

    # Count how many of our pieces are "bait" (low value, attacks high value)
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue

        # Check if this piece attacks higher value pieces
        attackers_and_defenders = list(board.attackers(piece.color, square))

        for target_square in attackers_and_defenders:
            if board.piece_at(target_square):
                target_piece = board.piece_at(target_square)
                if target_piece.color != piece.color:
                    our_value = PIECE_VALUES[piece.piece_type]
                    their_value = PIECE_VALUES[target_piece.piece_type]

                    if their_value > our_value:
                        # We're attacking a more valuable piece - good!
                        bonus = (their_value - our_value) // 20
                        if piece.color == chess.WHITE:
                            score += bonus
                        else:
                            score -= bonus

    return score


def is_endgame(board: chess.Board) -> bool:
    """
    判断是否为残局阶段
    Determine if the position is an endgame.

    残局判断标准（简单启发式）：
    - 双方皇后都不在了，或者
    - 双方的轻重子（马、象、车、后）总数都 ≤ 2

    残局阶段国王需要积极参与，使用不同的国王位置表。

    返回 Returns:
        True 如果是残局
    """
    # Count queens
    white_queens = len(board.pieces(chess.QUEEN, chess.WHITE))
    black_queens = len(board.pieces(chess.QUEEN, chess.BLACK))

    # Count minor and major pieces (excluding pawns and kings)
    white_pieces = (
        len(board.pieces(chess.KNIGHT, chess.WHITE)) +
        len(board.pieces(chess.BISHOP, chess.WHITE)) +
        len(board.pieces(chess.ROOK, chess.WHITE)) +
        white_queens
    )
    black_pieces = (
        len(board.pieces(chess.KNIGHT, chess.BLACK)) +
        len(board.pieces(chess.BISHOP, chess.BLACK)) +
        len(board.pieces(chess.ROOK, chess.BLACK)) +
        black_queens
    )

    # Endgame if:
    # - Both queens are off, OR
    # - Each side has ≤ 2 minor/major pieces
    return (white_queens == 0 and black_queens == 0) or (white_pieces <= 2 and black_pieces <= 2)


# ============================================================================
# 主评估函数
# ============================================================================

def evaluate(board: chess.Board) -> int:
    """
    主评估函数 - 为棋盘局面打分
    Main evaluation function for a chess position.

    这是搜索算法调用的核心函数，用于判断一个局面的好坏。
    搜索算法会根据这个分数来选择最佳走法。

    评分从白方视角：
    - 正分：白方优势（越大越好）
    - 负分：黑方优势（越小对黑方越好）
    - 零分：局面均势

    特殊情况处理：
    - 将死：返回极大/极小值（±30000）
    - 和棋：返回0

    参数 Args:
        board: 当前棋盘局面

    返回 Returns:
        评估分数（厘兵单位）
    """
    # 处理终局情况
    if board.is_checkmate():
        # 被将死：返回极端分数
        # 白方回合被将死 = 黑方赢 = -30000
        # 黑方回合被将死 = 白方赢 = +30000
        return -30000 if board.turn == chess.WHITE else 30000

    if board.is_stalemate() or board.is_insufficient_material():
        # 和棋情况：逼和或子力不足
        return 0

    # 检查可主张和棋（三次重复或50步规则）
    if board.can_claim_draw():
        return 0

    # 判断游戏阶段（中局 vs 残局）
    endgame = is_endgame(board)

    # 计算各评估组件
    material_score = evaluate_material(board)           # 子力
    positional_score = evaluate_piece_square_tables(board, endgame)  # 位置
    exposure_score = evaluate_exposure(board)           # 暴露惩罚【变体关键】
    king_safety_score = evaluate_king_safety(board)     # 国王安全
    tactical_score = evaluate_forced_capture_tactics(board)  # 战术

    # 组合各项分数（使用权重）
    total_score = (
        material_score +           # 子力最重要
        positional_score // 10 +   # 位置次之
        exposure_score +           # 暴露在强制吃子中很关键
        king_safety_score +        # 国王安全重要
        tactical_score // 5        # 战术加成
    )

    return total_score


if __name__ == "__main__":
    # Test the evaluation function
    print("Testing evaluation function...\n")

    # Test 1: Starting position
    board = chess.Board()
    score = evaluate(board)
    print(f"Starting position: {score} (should be close to 0)")

    # Test 2: Position where White is up a pawn
    board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPP1/RNBQKBNR w KQkq - 0 1")
    score = evaluate(board)
    print(f"White up a pawn: {score} (should be ~100+)")

    # Test 3: Position where Black is up a queen
    board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1")
    score = evaluate(board)
    print(f"Black up a queen: {score} (should be very negative)")

    # Test 4: Checkmate position
    board = chess.Board("r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4")
    score = evaluate(board)
    print(f"Black checkmated: {score} (should be ~30000)")
