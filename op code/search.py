"""
Search algorithms for forced capture chess engine.
强制吃子国际象棋搜索算法

本模块实现了国际象棋引擎的搜索算法，是课程中讲解的核心算法的实际应用。

实现的算法（对应课程内容）：
1. Minimax算法 - 博弈树的基本搜索策略
2. Alpha-Beta剪枝 - 减少搜索节点数的优化技术
3. 迭代加深（Iterative Deepening）- 时间管理策略
4. 走法排序（Move Ordering）- 提高剪枝效率
5. 静态搜索（Quiescence Search）- 避免水平线效应

【强制吃子变体优势】
在强制吃子规则下，当存在吃子走法时分支因子大大减少，
这使得搜索可以达到更深的深度。

Search algorithms for forced capture chess engine.
The search takes advantage of reduced branching when captures are forced.
"""

import chess
import time
from typing import Optional, Tuple, List
from dataclasses import dataclass

from evaluate import evaluate
from forced_capture import get_legal_moves_with_forced_capture


# ============================================================================
# 搜索结果数据类
# ============================================================================


@dataclass
class SearchResult:
    """
    搜索结果数据类
    Result of a search operation

    包含搜索完成后的所有重要信息
    """
    best_move: Optional[chess.Move]  # 最佳走法
    score: int                        # 评估分数
    depth: int                        # 搜索深度
    nodes_searched: int               # 搜索的节点数
    time_taken: float                 # 耗时（秒）
    pv: List[chess.Move]              # 主变例（Principal Variation）


class SearchStats:
    """
    搜索统计信息类
    Statistics for search debugging and optimization

    用于调试和分析搜索效率
    """
    def __init__(self):
        self.nodes_searched = 0
        self.alpha_cutoffs = 0
        self.beta_cutoffs = 0
        self.tt_hits = 0
        self.tt_misses = 0
        self.qsearch_nodes = 0

    def reset(self):
        self.__init__()

    def __str__(self):
        return (
            f"Nodes: {self.nodes_searched}, "
            f"α-cutoffs: {self.alpha_cutoffs}, "
            f"β-cutoffs: {self.beta_cutoffs}, "
            f"TT hits: {self.tt_hits}, "
            f"Q-nodes: {self.qsearch_nodes}"
        )


# ============================================================================
# 主搜索引擎类
# ============================================================================

class ChessSearcher:
    """
    主搜索引擎类
    Main search engine for forced capture chess

    这是国际象棋引擎的核心类，实现了课程中讲解的搜索算法。
    """

    def __init__(self, use_transposition_table: bool = True):
        """初始化搜索引擎"""
        self.stats = SearchStats()           # 搜索统计
        self.use_tt = use_transposition_table  # 是否使用置换表
        self.tt = {}                         # 置换表
        self.stop_search = False             # 停止搜索标志
        self.time_limit = None               # 时间限制
        self.start_time = None               # 搜索开始时间

    def order_moves(self, board: chess.Board, moves: List[chess.Move],
                   pv_move: Optional[chess.Move] = None) -> List[chess.Move]:
        """
        走法排序 - 提高Alpha-Beta剪枝效率
        Order moves for better alpha-beta pruning.

        【为什么走法排序重要】
        Alpha-Beta剪枝的效率取决于走法的搜索顺序。
        如果先搜索好的走法，可以更早地建立好的边界，剪掉更多分支。

        排序优先级：
        1. PV走法（上一次迭代的最佳走法）- 最有可能还是最佳
        2. 吃子走法（按MVV-LVA排序）- 高价值目标，低价值攻击者优先
        3. 将军走法
        4. 其他走法

        参数 Args:
            board: 当前局面
            moves: 要排序的走法列表
            pv_move: 主变例走法（来自上一次搜索）

        返回 Returns:
            排序后的走法列表
        """
        def move_score(move: chess.Move) -> int:
            score = 0

            # PV move gets highest priority
            if pv_move and move == pv_move:
                return 1000000

            # Captures: MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
            if board.is_capture(move):
                from evaluate import PIECE_VALUES

                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)

                if victim:
                    victim_value = PIECE_VALUES.get(victim.piece_type, 0)
                else:
                    # En passant
                    victim_value = PIECE_VALUES[chess.PAWN]

                attacker_value = PIECE_VALUES.get(attacker.piece_type, 0) if attacker else 0

                # MVV-LVA score: prioritize high-value victims, low-value attackers
                score += 10000 + victim_value - attacker_value // 10

            # Checks
            board.push(move)
            if board.is_check():
                score += 5000
            board.pop()

            # Promotions
            if move.promotion:
                score += 8000

            return score

        return sorted(moves, key=move_score, reverse=True)

    def quiescence_search(self, board: chess.Board, alpha: int, beta: int,
                         depth_left: int = 0) -> int:
        """
        静态搜索（Quiescence Search）- 避免水平线效应
        Quiescence search to avoid horizon effect.

        【什么是水平线效应】
        如果在搜索深度用完时局面正在进行激烈的战术交换，
        静态评估可能会给出错误的结果。

        例如：深度搜索在你吃掉对方皇后后停止，
        看起来你领先，但下一步对方会吃回来。

        【解决方案】
        在达到搜索深度后，继续搜索"战术走法"（吃子、将军），
        直到局面变得"安静"（没有战术走法）。

        参数 Args:
            board: 当前局面
            alpha: Alpha边界
            beta: Beta边界
            depth_left: 剩余深度（限制静态搜索深度）

        返回 Returns:
            局面评估分数
        """
        self.stats.qsearch_nodes += 1

        # Check time limit
        if self.should_stop():
            return 0

        # Stand pat: can we just stay in this position?
        stand_pat = evaluate(board)

        # Beta cutoff
        if stand_pat >= beta:
            return beta

        # Update alpha
        if stand_pat > alpha:
            alpha = stand_pat

        # Limit quiescence search depth
        if depth_left < -10:
            return stand_pat

        # Only search captures and checks in quiescence
        moves = get_legal_moves_with_forced_capture(board)

        # In quiescence, only look at captures and checks
        tactical_moves = []
        for move in moves:
            if board.is_capture(move):
                tactical_moves.append(move)
            else:
                # Check if it's a check
                board.push(move)
                is_check = board.is_check()
                board.pop()
                if is_check:
                    tactical_moves.append(move)

        # If no tactical moves, return stand pat
        if not tactical_moves:
            return stand_pat

        # Order captures by MVV-LVA
        tactical_moves = self.order_moves(board, tactical_moves)

        for move in tactical_moves:
            board.push(move)
            score = -self.quiescence_search(board, -beta, -alpha, depth_left - 1)
            board.pop()

            if score >= beta:
                return beta

            if score > alpha:
                alpha = score

        return alpha

    def alpha_beta(self, board: chess.Board, depth: int, alpha: int, beta: int,
                  pv_move: Optional[chess.Move] = None) -> Tuple[int, Optional[chess.Move]]:
        """
        Alpha-Beta搜索 - 课程核心算法
        Alpha-Beta search with pruning.

        【Alpha-Beta剪枝原理（课程内容）】
        - Alpha：当前搜索路径上MAX玩家已经确保能获得的最低分数
        - Beta：当前搜索路径上MIN玩家已经确保能获得的最高分数

        如果 Beta ≤ Alpha，说明这条路径不会被选择，可以剪掉（剪枝）。

        【Negamax框架】
        本实现使用Negamax（负极大值）框架，简化代码：
        - 总是从当前玩家角度评估
        - 递归调用时取负值并交换Alpha和Beta

        参数 Args:
            board: 当前局面
            depth: 剩余搜索深度
            alpha: Alpha边界（MAX玩家的下界）
            beta: Beta边界（MIN玩家的上界）
            pv_move: 主变例走法提示

        返回 Returns:
            元组 (分数, 最佳走法)
        """
        self.stats.nodes_searched += 1

        # Check if we should stop
        if self.should_stop():
            return 0, None

        # Check for terminal nodes
        if board.is_checkmate():
            # Return a score that accounts for depth (prefer shorter mates)
            return -30000 + (100 - depth), None

        if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
            return 0, None

        # Depth limit reached - use quiescence search
        if depth <= 0:
            return self.quiescence_search(board, alpha, beta), None

        # Generate and order moves
        moves = get_legal_moves_with_forced_capture(board)

        if not moves:
            # No legal moves
            if board.is_check():
                return -30000 + (100 - depth), None  # Checkmate
            else:
                return 0, None  # Stalemate

        moves = self.order_moves(board, moves, pv_move)

        best_move = None
        best_score = -999999

        for i, move in enumerate(moves):
            board.push(move)

            # Recursive search with negamax framework
            score, _ = self.alpha_beta(board, depth - 1, -beta, -alpha)
            score = -score

            board.pop()

            # Update best move
            if score > best_score:
                best_score = score
                best_move = move

            # Alpha-Beta pruning
            if score >= beta:
                self.stats.beta_cutoffs += 1
                return beta, best_move  # Beta cutoff

            if score > alpha:
                alpha = score
                self.stats.alpha_cutoffs += 1

        return alpha, best_move

    def iterative_deepening(self, board: chess.Board, max_depth: int = 50,
                           time_limit: float = None) -> SearchResult:
        """
        迭代加深搜索 - 时间管理的关键
        Iterative deepening search.

        【什么是迭代加深】
        依次搜索深度1、2、3、4...直到时间用完。

        【为什么使用迭代加深】
        1. 时间管理：比赛有时间限制，必须在时间内返回走法
        2. 走法排序：上一次迭代的最佳走法可以作为下一次的提示
        3. 任意时刻中断：即使被中断，也有上一次迭代的结果

        【看起来重复搜索很浪费？】
        实际上不是！由于分支因子的存在，大部分时间花在最后一层。
        搜索深度d的时间约等于搜索深度1到d-1的总时间。

        参数 Args:
            board: 当前局面
            max_depth: 最大搜索深度
            time_limit: 时间限制（秒），None表示无限制

        返回 Returns:
            包含最佳走法和统计信息的SearchResult
        """
        self.start_time = time.time()
        self.time_limit = time_limit
        self.stop_search = False
        self.stats.reset()

        best_move = None
        best_score = 0
        pv = []

        # Try each depth
        for depth in range(1, max_depth + 1):
            if self.should_stop():
                break

            # Search at this depth
            alpha = -999999
            beta = 999999

            score, move = self.alpha_beta(board, depth, alpha, beta, best_move)

            # If search was interrupted, use previous iteration's result
            if not self.should_stop() and move:
                best_move = move
                best_score = score

                # Build principal variation
                pv = [move]

            # Print info (for debugging)
            time_taken = time.time() - self.start_time
            nps = self.stats.nodes_searched / max(time_taken, 0.001)

            print(f"Depth {depth}: score={score}, move={move}, "
                  f"nodes={self.stats.nodes_searched}, nps={nps:.0f}, "
                  f"time={time_taken:.2f}s")

            # If we found a mate, no need to search deeper
            if abs(score) > 29000:
                print(f"Mate found at depth {depth}!")
                break

        time_taken = time.time() - self.start_time

        return SearchResult(
            best_move=best_move,
            score=best_score,
            depth=depth,
            nodes_searched=self.stats.nodes_searched,
            time_taken=time_taken,
            pv=pv
        )

    def should_stop(self) -> bool:
        """
        检查是否应该停止搜索
        Check if search should be stopped (due to time limit)
        """
        if self.stop_search:
            return True

        if self.time_limit and self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed >= self.time_limit:
                return True

        return False

    def search(self, board: chess.Board, depth: int = 5,
              time_limit: float = None) -> SearchResult:
        """
        主搜索接口 - 外部调用的入口
        Main search interface.

        这是引擎调用搜索的主要接口。

        参数 Args:
            board: 当前局面
            depth: 搜索深度（固定深度搜索时使用）
            time_limit: 时间限制（秒），用于比赛时的时间管理

        返回 Returns:
            SearchResult 包含最佳走法和搜索统计
        """
        if time_limit:
            return self.iterative_deepening(board, max_depth=50, time_limit=time_limit)
        else:
            return self.iterative_deepening(board, max_depth=depth, time_limit=None)


if __name__ == "__main__":
    print("Testing search engine...\n")

    # Test 1: Mate in 1
    print("Test 1: Mate in 1")
    board = chess.Board("r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4")
    print(board)
    print()

    searcher = ChessSearcher()
    result = searcher.search(board, depth=3)
    print(f"Best move: {result.best_move}")
    print(f"Score: {result.score}")
    print(f"Nodes: {result.nodes_searched}")
    print()

    # Test 2: Starting position
    print("Test 2: Starting position")
    board = chess.Board()
    result = searcher.search(board, depth=4, time_limit=2.0)
    print(f"Best move: {result.best_move}")
    print(f"Score: {result.score}")
    print(f"Nodes: {result.nodes_searched}")
    print(f"Time: {result.time_taken:.2f}s")
