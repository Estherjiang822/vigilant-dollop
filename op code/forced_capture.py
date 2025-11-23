"""
Forced Capture Rule Implementation
强制吃子规则实现

本模块实现了国际象棋变体的核心规则：
如果玩家有任何合法的吃子走法，则玩家必须选择其中一个吃子走法。

这与标准国际象棋不同，在标准规则中吃子是可选的。

核心规则（来自课程要求）：
- 如果当前玩家有合法的吃子走法，则必须执行吃子
- 如果没有吃子走法，则可以走任何合法走法
- 胜负条件与标准国际象棋相同（将死对方国王获胜）
- 其他规则（王车易位、吃过路兵、50步规则等）保持不变

This module implements the core rule of the chess variant:
If a player has any legal move that captures an opponent's piece,
then the player MUST make a legal move that captures an opponent's piece.

This is different from standard chess where captures are optional.
"""

import chess
from typing import List


# ============================================================================
# 核心函数：获取强制吃子规则下的合法走法
# ============================================================================


def get_legal_moves_with_forced_capture(board: chess.Board) -> List[chess.Move]:
    """
    获取强制吃子规则下的合法走法（核心函数）
    Generate legal moves according to forced capture rules.

    这是整个变体规则的核心实现：
    1. 获取所有标准国际象棋的合法走法
    2. 筛选出其中的吃子走法
    3. 如果存在吃子走法，则只返回吃子走法（强制吃子）
    4. 如果不存在吃子走法，则返回所有合法走法

    Rules:
    1. If there are legal moves that capture a piece, ONLY return those
    2. If there are no capturing moves, return all legal moves
    3. When in check, only return moves that get out of check
       - If any of those moves capture, only return the capturing ones

    参数 Args:
        board: 当前棋盘位置 (chess.Board 对象)

    返回 Returns:
        符合强制吃子规则的合法走法列表
    """
    # 第一步：获取所有标准国际象棋的合法走法
    # python-chess 库已经处理了将军等情况，只返回不会让己方国王被吃的走法
    all_legal_moves = list(board.legal_moves)

    # 第二步：筛选出吃子走法
    # 吃子的定义：
    # 1. 目标格有对方棋子，或者
    # 2. 是吃过路兵（en passant）
    capturing_moves = [
        move for move in all_legal_moves
        if board.is_capture(move)
    ]

    # 第三步：应用强制吃子规则
    # 如果存在吃子走法，必须从中选择一个（强制吃子）
    if capturing_moves:
        return capturing_moves
    else:
        # 没有吃子走法，可以走任何合法走法
        return all_legal_moves


def is_forced_capture_legal(board: chess.Board, move: chess.Move) -> bool:
    """
    检查一个走法在强制吃子规则下是否合法
    Check if a move is legal according to forced capture rules.

    用途：验证用户或对手的走法是否符合变体规则

    参数 Args:
        board: 当前棋盘位置
        move: 要验证的走法

    返回 Returns:
        True 如果走法在强制吃子规则下合法
    """
    # 首先检查是否是标准国际象棋的合法走法
    if move not in board.legal_moves:
        return False

    # 获取强制吃子规则下的所有合法走法
    forced_legal_moves = get_legal_moves_with_forced_capture(board)

    # 检查这个走法是否在允许的集合中
    return move in forced_legal_moves


def has_forced_captures(board: chess.Board) -> bool:
    """
    检查当前玩家是否有强制吃子
    Check if the current player has any forced captures.

    用途：快速判断当前局面是否处于强制吃子状态

    参数 Args:
        board: 当前棋盘位置

    返回 Returns:
        True 如果存在吃子走法（此时吃子是强制的）
    """
    return any(board.is_capture(move) for move in board.legal_moves)


# ============================================================================
# 辅助函数：获取吃子走法的详细信息
# ============================================================================


def get_capture_info(board: chess.Board, move: chess.Move) -> dict:
    """
    获取吃子走法的详细信息
    Get information about a capture move.

    用途：分析一个吃子走法的价值，用于走法排序和评估

    参数 Args:
        board: 当前棋盘位置
        move: 要分析的走法

    返回 Returns:
        包含吃子信息的字典:
        - is_capture: 是否为吃子走法
        - captured_piece: 被吃的棋子
        - is_en_passant: 是否为吃过路兵
        - capture_value: 被吃棋子的子力价值
    """
    if not board.is_capture(move):
        return {
            'is_capture': False,
            'captured_piece': None,
            'is_en_passant': False,
            'capture_value': 0
        }

    # 标准棋子价值（厘兵为单位，即1兵=100）
    # 用于评估吃子的价值，帮助搜索算法优先考虑高价值吃子
    PIECE_VALUES = {
        chess.PAWN: 100,      # 兵
        chess.KNIGHT: 320,    # 马
        chess.BISHOP: 330,    # 象
        chess.ROOK: 500,      # 车
        chess.QUEEN: 900,     # 后
        chess.KING: 0         # 王（实际上不能被吃）
    }

    is_en_passant = board.is_en_passant(move)

    if is_en_passant:
        # En passant always captures a pawn
        captured_piece = chess.Piece(chess.PAWN, not board.turn)
        capture_value = PIECE_VALUES[chess.PAWN]
    else:
        # Normal capture
        captured_piece = board.piece_at(move.to_square)
        capture_value = PIECE_VALUES[captured_piece.piece_type] if captured_piece else 0

    return {
        'is_capture': True,
        'captured_piece': captured_piece,
        'is_en_passant': is_en_passant,
        'capture_value': capture_value
    }


def analyze_forced_capture_position(board: chess.Board) -> dict:
    """
    从强制吃子角度分析当前局面
    Analyze the current position from a forced capture perspective.

    用途：提供局面的完整分析，用于调试和界面显示

    参数 Args:
        board: 当前棋盘位置

    返回 Returns:
        包含局面分析的字典:
        - total_legal_moves: 总合法走法数
        - capturing_moves: 吃子走法数
        - non_capturing_moves: 非吃子走法数
        - is_capture_forced: 是否必须吃子
        - available_captures: 可用吃子走法列表（含详细信息）
    """
    all_legal_moves = list(board.legal_moves)
    capturing_moves = [m for m in all_legal_moves if board.is_capture(m)]
    non_capturing_moves = [m for m in all_legal_moves if not board.is_capture(m)]

    available_captures = []
    for move in capturing_moves:
        capture_info = get_capture_info(board, move)
        available_captures.append({
            'move': move,
            'san': board.san(move),
            'uci': move.uci(),
            **capture_info
        })

    # Sort by capture value (highest first)
    available_captures.sort(key=lambda x: x['capture_value'], reverse=True)

    return {
        'total_legal_moves': len(all_legal_moves),
        'capturing_moves': len(capturing_moves),
        'non_capturing_moves': len(non_capturing_moves),
        'is_capture_forced': len(capturing_moves) > 0,
        'available_captures': available_captures,
        'in_check': board.is_check(),
        'is_checkmate': board.is_checkmate(),
        'is_stalemate': board.is_stalemate()
    }


if __name__ == "__main__":
    # Example usage and testing
    board = chess.Board()

    print("Starting position:")
    print(board)
    print()

    analysis = analyze_forced_capture_position(board)
    print(f"Total legal moves: {analysis['total_legal_moves']}")
    print(f"Capturing moves: {analysis['capturing_moves']}")
    print(f"Is capture forced: {analysis['is_capture_forced']}")
    print()

    # Test position with captures available
    board = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2")
    print("Position after 1.e4 e5:")
    print(board)
    print()

    # Now move to a position where there's a capture available
    board.push_san("Nf3")
    board.push_san("Nc6")
    board.push_san("Bb5")  # Attacks the knight

    print("Position with capture available (Bb5 attacks Nc6):")
    print(board)
    print()

    analysis = analyze_forced_capture_position(board)
    print(f"Total legal moves: {analysis['total_legal_moves']}")
    print(f"Capturing moves: {analysis['capturing_moves']}")
    print(f"Is capture forced: {analysis['is_capture_forced']}")

    if analysis['is_capture_forced']:
        print("\nBlack MUST capture! Available captures:")
        for cap in analysis['available_captures']:
            print(f"  {cap['san']} (captures {cap['captured_piece']}, value={cap['capture_value']})")

    forced_moves = get_legal_moves_with_forced_capture(board)
    print(f"\nLegal moves under forced capture rule: {len(forced_moves)}")
    for move in forced_moves:
        print(f"  {board.san(move)}")
