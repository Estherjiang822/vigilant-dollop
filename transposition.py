import chess
import chess.polyglot

class Transposition_Table:
    def __init__(self, size=100000):
        self.size = size
        self.table = [None] * size

    def index(self, key):
        return key % self.size
    
    def store(self, board: chess.Board, depth, score, flag, best_move):
        key = chess.polyglot.zobrist_hash(board)
        idx = self.index(key)

        entry = self.table[idx]

        if entry is None or depth >= entry.depth:
            self.table[idx] = Transposition_Entry(key, depth, score, flag, best_move)

    def lookup(self, board: chess.Board):
        key = chess.polyglot.zobrist_hash(board)
        idx = self.index(key)

        entry = self.table[idx]
        if entry is not None and entry.key == key:
            return entry
        return None
    
    def count_used(self):
        count = 0
        for zobrist in self.table:
            if zobrist is not None:
                count += 1
        return count
    

class Transposition_Entry:
    def __init__(self, key, depth, score, flag, best_move):
        self.key = key
        self.score = score
        self.flag = flag # One of ["EXACT", "LOWERBOUND", "UPPERBOUND"]
        self.depth = depth
        self.best_move = best_move

