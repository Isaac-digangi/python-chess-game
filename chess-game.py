import pygame, os, chess
import threading
import chess.engine

SQUARE = 100
WINDOW = SQUARE * 8

# loads images for each chess piece and move marker. scales them to fit the board squares.

def load_images(size=SQUARE):
    base = os.path.join(os.path.dirname(__file__), 'imgs')
    codes = ['wp','wr','wn','wb','wq','wk','bp','br','bn','bb','bq','bk']
    imgs = {}
    for code in codes:
        path = os.path.join(base, f"{code}.png")
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, (size, size))
            imgs[code] = img
        else:
            imgs[code] = None
    # Load identifier image
    identifier_path = os.path.join(base, 'identifier.png')
    if os.path.exists(identifier_path):
        imgs['identifier'] = pygame.image.load(identifier_path).convert_alpha()
        imgs['identifier'] = pygame.transform.smoothscale(imgs['identifier'], (size, size))
    else:
        imgs['identifier'] = None
    return imgs

#  returns the starting pos of the pieces and board.

def starting_board():
    # Standard starting position using piece codes
    return [
        ['br','bn','bb','bq','bk','bb','bn','br'],
        ['bp']*8,
        [None]*8,
        [None]*8,
        [None]*8,
        [None]*8,
        ['wp']*8,
        ['wr','wn','wb','wq','wk','wb','wn','wr']
    ]

# draws the chessboard and places the images of the pieces in their squares. 
# It also highlights the legal moves for a selected piece using an marker image.

def draw_board(screen, board, images, legal_moves=None):
    white = (255, 213, 153)
    black = (177, 110, 65)
    font = pygame.font.SysFont(None, 28)
    for row in range(8):
        for col in range(8):
            color = white if (row + col) % 2 == 0 else black
            rect = (col * SQUARE, row * SQUARE, SQUARE, SQUARE)
            pygame.draw.rect(screen, color, rect)
            piece = board[row][col]
            if piece:
                img = images.get(piece)
                if img:
                    screen.blit(img, (col * SQUARE, row * SQUARE))
                else:
                    # fallback: draw a simple text marker if image missing
                    lbl = font.render(piece, True, (255,0,0))
                    screen.blit(lbl, (col * SQUARE + 8, row * SQUARE + 8))
            # Draw identifier on legal move squares
            if legal_moves and images.get('identifier'):
                for move in legal_moves:
                    to_sq = move.to_square
                    to_file = chess.square_file(to_sq)
                    to_rank = chess.square_rank(to_sq)
                    to_row = 7 - to_rank
                    to_col = to_file
                    if to_row == row and to_col == col:
                        screen.blit(images['identifier'], (col * SQUARE, row * SQUARE))

# sets up the Pygame window, handles events, and updates the display. It uses the python-chess library to manage the game state and determine legal moves.

def board():
    pygame.init()
    screen = pygame.display.set_mode((1200, WINDOW))  # later set first WINDOW to 1200 for move list area
    pygame.display.set_caption("Chess Board with Images")
    pygame.draw.line(screen, (255, 255, 255), (1000, 0), (1000, WINDOW), 3) #|| Draw a line to separate the board from the move list area (soon)


    images = load_images()
    # use python-chess Board for legal-move logic
    board_obj = chess.Board()

    # --- Engine configuration (edit `STOCKFISH_PATH` to your binary) ---
    STOCKFISH_PATH = r"C:\\Users\\ameri\\Downloads\\stockfish\\stockfish\\stockfish-windows-x86-64-avx2.exe"
    play_vs_engine = True
    engine_color = chess.BLACK  # engine plays as BLACK by default

    engine = None
    engine_lock = threading.Lock()
    engine_thinking = False
    is_checkmate = False
    is_stalemate = False
    is_check = False
    is_insufficient_material = False
    is_threefold_repetition = False
    

    if play_vs_engine:
        try:
            engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        except Exception as e:
            print(f"Failed to start engine: {e}")
            engine = None

    def board_from_chess(b):
        # build 8x8 board_state from python-chess Board
        state = [[None for _ in range(8)] for _ in range(8)]
        for sq, piece in b.piece_map().items():
            file = chess.square_file(sq)  # 0..7
            rank = chess.square_rank(sq)  # 0..7 where 0 is rank1
            row = 7 - rank  # convert to drawing row (0 at top)
            col = file
            color = 'w' if piece.color == chess.WHITE else 'b'
            p = piece.symbol().lower()
            code = color + {'p':'p','r':'r','n':'n','b':'b','q':'q','k':'k'}[p]
            state[row][col] = code
        return state

    board_state = board_from_chess(board_obj)
    selected_legal_moves = []  # Track the current selection's legal moves
    selected_square = None

    clock = pygame.time.Clock()
    running = True

    # main loop handles user input, allowing players to click on pieces and view their legal moves.

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                # Ignore clicks while engine is thinking
                if engine_thinking:
                    continue

                x, y = event.pos
                col = x // SQUARE
                row = y // SQUARE
                # map (row,col) to python-chess square
                file = col
                rank = 7 - row
                sq = chess.square(file, rank)

                piece = board_obj.piece_at(sq)
                # First click: select a friendly piece
                if selected_square is None:
                    if piece and piece.color == board_obj.turn:
                        selected_square = sq
                        legal = [m for m in board_obj.legal_moves if m.from_square == sq]
                        selected_legal_moves = legal
                        if not legal:
                            print("No legal moves for this piece.")
                        # else:
                        #     print("Legal moves:")
                        #     for m in legal:
                        #         try:
                        #             san = board_obj.san(m)
                        #         except Exception:
                        #             san = ""
                        #         print(f"  {san}")
                    else:
                        selected_legal_moves = []
                else:
                    # Second click: attempt move
                    move = None
                    for m in board_obj.legal_moves:
                        if m.from_square == selected_square and m.to_square == sq:
                            move = m
                            break

                    if move:
                        board_obj.push(move)
                        board_state = board_from_chess(board_obj)
                        selected_square = None
                        selected_legal_moves = []

                        # Start engine reply in background if configured
                        if play_vs_engine and engine and board_obj.turn == engine_color:
                            def engine_play():
                                nonlocal engine_thinking, board_state
                                with engine_lock:
                                    engine_thinking = True
                                    try:
                                        res = engine.play(board_obj, chess.engine.Limit(time=0.3))
                                        board_obj.push(res.move)
                                        board_state = board_from_chess(board_obj)
                                    except Exception as e:
                                        print(f"Engine play failed: {e}")
                                    finally:
                                        engine_thinking = False

                            t = threading.Thread(target=engine_play, daemon=True)
                            t.start()
                    else:
                        selected_square = None
                        selected_legal_moves = []

        draw_board(screen, board_state, images, selected_legal_moves)
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()

if __name__ == "__main__":
    board()
