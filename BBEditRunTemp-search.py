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
    
    
    def iterative_deepening(self, board: chess.Board, max_depth: int = 50, 
    						time_limit:float = None):
        self.start_time = time.time()
        self.time_limit = time_limit()
        self.stop_search = False
        self.stats.reset()
        
        best_move = None
        best_score = -float("inf") 
        pv = []
        window = 25
        
        for depth in range(1, max_depth + 1):
        	if self.should_stop():
        		break
        	if depth == 1 or best_move is None:
        		alpha = -999999   
        		beta = 999999
        	else:
        		alpha = best_score - window
        		beta = best_score + window
        		
        	score = self.minimax(board, depth, alpha, beta, max_player=board.turn)  
        	if score <= alpha and not self.should_stop():
        		alpha = -999999
        		score = self.minimax(board, depth, alpha, beta, max_player=board.turn)
        	elif score >= beta and not self.should_stop():
        		beta = 999999
        		score = self.minimax(board, depth, alpha, beta, max_player=board.turn)
        		
        	moves = list(forced_legal_moves(board))
			if moves:
				best _move = max(moves. key = lambda mv: TT.lookup(board, mv).score if
								 TT.lookup(board, mv) else -999999)
			else:
				best_move = None
				
			best_score = score
			pv = [best_move]
			
			elapsed = time.time() - self.start_time
			nps = self.stats.nodes_searched / max(elapsed, 0.001)
			
			print(f"[Depth {depth}] score={score} move={best_move} "
              	  f"nodes={self.stats.nodes_searched} nps={nps:.0f} "
              	  f"time={elapsed:.2f}s")

			if abs(score) > 29000:
				print(f"Mate confirmed at depth {depth}")
            	break
            
            if self.should_stop():
            	break
            	
        return SearchResult(best_move = best_move, score = best_score, depth = depth,
        					nodes_searched = self.stats.nodes_searched, 
        					time_taken = time.time() - self.start_time, pv = pv)
        				
        					
    def quiescence_search(self, board: chess.Board, alpha:int, beta:int, 
    					  depth_left: int = 0) -> int:
    					  
    	self.stats.qsearch_nodes += 1
    	
    	if self.should_stop():
    		return alpha
    	stand_pat = evaluate(board)
    	
		if stand_pat >= beta:
			return beta
			
		if stand_pat > alpha:
			alpha = stand_pat
			
		if depth_left < -8:
			return stand_pat
			
		moves = forced_legal_moves(board)
		
		if not moves:
			return stand_pat
			
		tactical_moves = []
		for move in moves:
			if board.is_capture(move):
				tactical_moves.append(move)
			else:
				board.push(move)
				gives_check = board.is_check()
				board.pop()
				if gives_check:
					tactical_moves.append(move)
		
		if not tactical_moves:
			return stand_pat
			
		tactical_moves = self.order_moves(board, tactical_moves)
		
		for move in tactical_moves:
			board.push(move)
			score = -self.quiescence_search(board, -beta, -alpha, depth_left - 1)
			board.pop()
			
			if score >= beta:
				return beta
			
			if score > alpha:
				return score
		
		return alpha

        		
    def order_moves(self, board: chess.Board, moves: List[chess.Move], 
    				pv_move: Optional[chess.Move] = None) -> List[chess.Move]:
    	PIECE_VALUES = {chess.PAWN: 100, 
    					chess.KNIGHT: 320,
    					chess.BISHOP: 330,
    					chess.ROOK: 500,
    					chess.QUEEN: 900,
    					chess.KING: 20000,}
    	tt_entry = TT.lookup(board)
    	tt_move = tt_entry.best_move if tt_entry else None
    	
    	def score(move: chess.Move) -> Int:
    		s = 0
    		if pv_move and move == pv_move:
    			return 2_000_000
    			
    		if tt_move and move == tt_move:
    			return 1_500_000
    			
    		if board.is_capture(move):
    			victim_piece = board.piece_at(move.to_square)
    			attacker_piece = board.piece_at(move.from_square)
    			
    			if victim_piece:
    				victim = PIECE_VALUES[victim_piece.piece_type]
    			else:
    				victim = PIECE_VALUES[chess.PAWN]
    				
    			attacker = PIECE_VALUES[attacker_piece.piece_type] if attacker_piece else 0
    			s += 50_000 + 10 * victim - attacker
    			
    			board.push(move)
    			gives_check = board.is_check()
    			board.pop()
    			
    			if gives_check:
    				s += 20_000
    			
    			if move.promption:
    				s += 40_000 + PIECE_VALUES.get(move.promotion, 0)
    				
    			return s
    		return sorted(moves, key = score, reverse = True)    	
        	
        	
        	
        	  						