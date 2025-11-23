"""
Transposition Table for chess search.
国际象棋搜索的置换表

【什么是置换表】
置换表存储之前评估过的局面，避免重复计算。
这对国际象棋很重要，因为同一局面可以通过不同的走法顺序到达（换位）。

例如：1.e4 e5 2.Nf3 和 1.Nf3 e5 2.e4 到达相同局面。

【实现原理】
使用Zobrist哈希（python-chess内置）作为局面的唯一标识。
Zobrist哈希是一种高效的哈希方法，专门为棋类游戏设计。

A transposition table stores previously evaluated positions to avoid
re-computing them. Uses Zobrist hashing for position keys.
"""

import chess
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# 置换表条目类型
# ============================================================================

class TTEntryType(Enum):
    """
    置换表条目类型
    Type of transposition table entry

    Alpha-Beta搜索时，我们可能得到三种类型的分数：
    """
    EXACT = 1       # 精确值：在alpha和beta之间找到的值
    LOWER_BOUND = 2  # 下界：发生Beta截断，真实值 >= 存储值
    UPPER_BOUND = 3  # 上界：发生Alpha截断，真实值 <= 存储值


@dataclass
class TTEntry:
    """
    置换表条目
    Transposition table entry
    """
    zobrist_key: int                  # Zobrist哈希键
    depth: int                         # 搜索深度
    score: int                         # 评估分数
    entry_type: TTEntryType           # 分数类型
    best_move: Optional[chess.Move]   # 最佳走法（用于走法排序）
    age: int                           # 年龄（用于替换策略）


# ============================================================================
# 置换表主类
# ============================================================================

class TranspositionTable:
    """
    置换表类（带替换策略）
    Transposition table with replacement scheme.

    【替换策略】
    当表满或发生冲突时，决定是否替换旧条目：
    1. 新位置（空槽）- 直接存入
    2. 搜索深度更大 - 替换
    3. 条目太旧 - 替换
    """

    def __init__(self, size_mb: int = 64):
        """
        初始化置换表
        Initialize transposition table.

        参数 Args:
            size_mb: 近似大小（MB）
        """
        # Estimate entries: each entry ~50 bytes
        # 1 MB ≈ 20,000 entries
        self.max_entries = size_mb * 20000
        self.table = {}
        self.hits = 0
        self.misses = 0
        self.collisions = 0
        self.current_age = 0

    def clear(self):
        """Clear the transposition table"""
        self.table.clear()
        self.hits = 0
        self.misses = 0
        self.collisions = 0

    def new_search(self):
        """Increment age for new search (helps with replacement)"""
        self.current_age += 1

        # Every 100 searches, clean old entries
        if self.current_age % 100 == 0:
            self._clean_old_entries()

    def _clean_old_entries(self):
        """Remove entries older than 10 generations"""
        old_keys = [
            key for key, entry in self.table.items()
            if self.current_age - entry.age > 10
        ]

        for key in old_keys:
            del self.table[key]

    def store(self, board: chess.Board, depth: int, score: int,
             entry_type: TTEntryType, best_move: Optional[chess.Move] = None):
        """
        存储局面到置换表
        Store a position in the transposition table.

        参数 Args:
            board: 棋盘局面
            depth: 搜索深度
            score: 评估分数
            entry_type: 分数类型（精确/上界/下界）
            best_move: 最佳走法（如果有）
        """
        zobrist_key = chess.polyglot.zobrist_hash(board)

        # Check if we should replace existing entry
        if zobrist_key in self.table:
            existing = self.table[zobrist_key]

            # Replace if deeper or newer search
            if depth < existing.depth and (self.current_age - existing.age) < 2:
                return  # Don't replace

            self.collisions += 1

        # Store entry
        self.table[zobrist_key] = TTEntry(
            zobrist_key=zobrist_key,
            depth=depth,
            score=score,
            entry_type=entry_type,
            best_move=best_move,
            age=self.current_age
        )

        # Limit table size
        if len(self.table) > self.max_entries:
            # Remove oldest 10% of entries
            sorted_entries = sorted(
                self.table.items(),
                key=lambda x: x[1].age
            )
            remove_count = len(sorted_entries) // 10

            for key, _ in sorted_entries[:remove_count]:
                del self.table[key]

    def probe(self, board: chess.Board, depth: int, alpha: int, beta: int) -> \
            Tuple[Optional[int], Optional[chess.Move]]:
        """
        查询置换表
        Probe the transposition table.

        【查询逻辑】
        1. 如果找到条目且深度足够：
           - EXACT类型：直接返回分数
           - LOWER_BOUND：如果分数>=beta，可用于截断
           - UPPER_BOUND：如果分数<=alpha，可用于截断
        2. 即使分数不能用，最佳走法仍可用于走法排序

        参数 Args:
            board: 棋盘局面
            depth: 当前搜索深度
            alpha: Alpha边界
            beta: Beta边界

        返回 Returns:
            (分数, 最佳走法) 如果可用；(None, 最佳走法) 如果只有走法提示
        """
        zobrist_key = chess.polyglot.zobrist_hash(board)

        if zobrist_key not in self.table:
            self.misses += 1
            return None, None

        entry = self.table[zobrist_key]

        # Verify it's the same position (paranoid check)
        if entry.zobrist_key != zobrist_key:
            self.misses += 1
            return None, None

        # Entry found
        self.hits += 1

        # Can we use this score?
        if entry.depth >= depth:
            if entry.entry_type == TTEntryType.EXACT:
                return entry.score, entry.best_move

            elif entry.entry_type == TTEntryType.LOWER_BOUND:
                if entry.score >= beta:
                    return entry.score, entry.best_move

            elif entry.entry_type == TTEntryType.UPPER_BOUND:
                if entry.score <= alpha:
                    return entry.score, entry.best_move

        # Can't use score, but can use best move for move ordering
        return None, entry.best_move

    def get_stats(self) -> dict:
        """Get transposition table statistics"""
        total_queries = self.hits + self.misses

        return {
            'size': len(self.table),
            'max_size': self.max_entries,
            'hits': self.hits,
            'misses': self.misses,
            'collisions': self.collisions,
            'hit_rate': self.hits / max(total_queries, 1) * 100,
            'fill_rate': len(self.table) / self.max_entries * 100
        }

    def __str__(self):
        stats = self.get_stats()
        return (
            f"TT: {stats['size']}/{stats['max_size']} entries "
            f"({stats['fill_rate']:.1f}% full), "
            f"hit rate: {stats['hit_rate']:.1f}%"
        )


if __name__ == "__main__":
    print("Testing Transposition Table...\n")

    tt = TranspositionTable(size_mb=1)

    # Test 1: Store and retrieve
    board = chess.Board()
    tt.store(board, depth=5, score=100, entry_type=TTEntryType.EXACT,
            best_move=chess.Move.from_uci("e2e4"))

    score, move = tt.probe(board, depth=5, alpha=-1000, beta=1000)
    print(f"Test 1 - Store and retrieve: score={score}, move={move}")
    assert score == 100
    assert move == chess.Move.from_uci("e2e4")

    # Test 2: Depth requirement
    score, move = tt.probe(board, depth=6, alpha=-1000, beta=1000)
    print(f"Test 2 - Insufficient depth: score={score}, move={move}")
    assert score is None  # Depth 6 > stored depth 5
    assert move == chess.Move.from_uci("e2e4")  # But move hint is available

    # Test 3: Alpha-beta bounds
    board.push_san("e4")
    tt.store(board, depth=5, score=200, entry_type=TTEntryType.LOWER_BOUND)

    score, move = tt.probe(board, depth=5, alpha=-1000, beta=150)
    print(f"Test 3 - Lower bound cutoff: score={score}")
    assert score == 200  # Lower bound >= beta (150)

    # Test 4: Statistics
    print(f"\nStatistics: {tt}")
    print(tt.get_stats())

    print("\nAll tests passed!")
