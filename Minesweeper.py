import numpy as np
import random
import tkinter as tk
from tkinter import messagebox
from collections import defaultdict, deque
import math
import time

## MinesweeperEnv ##
class MinesweeperEnv:
    def __init__(self, rows = 16, cols = 16, num_mines = 40): # Chessboard settings: 16*16 chessboard, 40 mines
        self.rows = rows
        self.cols = cols
        self.num_mines = num_mines
        self.action_size = rows * cols * 2
        self.reset()
    
    def reset(self): # Game initialization
        self.game_over = False # Game over flag
        self.won = False # Game win flag
        self.revealed = [[False for _ in range(self.cols)] for _ in range(self.rows)] # Whether cell is clicked, False = not clicked
        self.flagged = [[False for _ in range(self.cols)] for _ in range(self.rows)] # Whether cell is flagged, False = not flagged
        self.board = [[0 for _ in range(self.cols)] for _ in range(self.rows)] # Number of adjacent mines for cell, 0 = no adjacent mines
        self.mine_locations = set() # Set of mine positions
        self.first_move = True # First click flag, ensure no mine on first click
        return self.get_state()
    
    def place_mines(self, first_r, first_c): # Place mines on the board
        self.mine_locations = set()
        all_positions = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        # Safe zone: the first clicked cell and its 8 surrounding neighbors
        safe_zone = [(first_r + dr, first_c + dc) for dr in [-1,0,1] for dc in [-1,0,1] if 0 <= first_r + dr < self.rows and 0 <= first_c + dc < self.cols]
        safe_zone.append((first_r, first_c))
        # Available positions for placing mines (exclude safe zone)
        available = [p for p in all_positions if p not in safe_zone]
        self.mine_locations = set(random.sample(available, min(self.num_mines, len(available))))
        
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) in self.mine_locations:
                    self.board[r][c] = -1 # Cell = mine
                else:
                    self.board[r][c] = 0 # Cell = unknown
        
        # Number of mines around the cell
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] == -1:
                    continue
                count = 0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr = r + dr
                        nc = c + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            if self.board[nr][nc] == -1:
                                count += 1
                self.board[r][c] = count
    
    def get_state(self): # Cell state
        state = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.revealed[r][c]:
                    state.append(self.board[r][c] + 10) # Clicked cell: 10
                elif self.flagged[r][c]:
                    state.append(20) # Flagged cell: 20
                else:
                    state.append(0) # Unknown cell: 0
        return tuple(state)
    
    def get_valid_actions(self): # Play the game
        valid = []
        cells = self.rows * self.cols
        
        # Click cell
        for i in range(cells):
            r = i // self.cols
            c = i % self.cols
            if not self.revealed[r][c] and not self.flagged[r][c]:
                valid.append(i)
        
        # Flag cell
        for i in range(cells, 2 * cells):
            r = (i - cells) // self.cols
            c = (i - cells) % self.cols
            if not self.revealed[r][c]:
                valid.append(i)
        
        return valid
    
    def get_safe_cells(self): # Logical reasoning
        safe_cells = set()
        mine_cells = set()
        constraints = []

        for r in range(self.rows):
            for c in range(self.cols):
                if self.revealed[r][c] and self.board[r][c] > 0: # Current cell is clicked and has mines around
                    neighbors = [] # Used to store the number of unclicked adjacent cells around the current cell
                    flagged_count = 0 # Number of flagged cells around the current cell
                    # Traverse the 8 cells around the current cell in turn                    
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            nr = r + dr
                            nc = c + dc
                            if 0 <= nr < self.rows and 0 <= nc < self.cols: # Boundary check
                                if self.flagged[nr][nc]:
                                    flagged_count += 1
                                elif not self.revealed[nr][nc]:
                                    neighbors.append((nr, nc))
                    
                    remaining_mines = self.board[r][c] - flagged_count # Number of unmarked mines around the current cell
                    if neighbors and remaining_mines >= 0:
                        constraints.append((set(neighbors), remaining_mines))
        
        for cells, count in constraints:
            if len(cells) == count and count > 0: # All mines
                for cell in cells:
                    mine_cells.add(cell)
            elif count == 0: # No mines
                for cell in cells:
                    safe_cells.add(cell)
        
        return safe_cells, mine_cells
    
    def step(self, action):
        if self.game_over:
            return self.get_state(), -1, True, {} # If game over, get penalty score -1
        # Total number of cells
        cells = self.rows * self.cols
        
        # Click cell
        if action < cells:
            r = action // self.cols
            c = action % self.cols
            # If cell is clicked or flagged, get penalty score -1, game continues
            if self.revealed[r][c] or self.flagged[r][c]:
                return self.get_state(), -1, False, {}
            # Place mines in mine zone after first click
            if self.first_move:
                self.place_mines(r, c)
                self.first_move = False
            self.revealed[r][c] = True 
            # If click a cell with mine, get penalty score -20, game over
            if self.board[r][c] == -1:
                self.game_over = True
                return self.get_state(), -20, True, {}
            # If click empty cell, auto expand adjacent empty area
            if self.board[r][c] == 0:
                self.auto_expand(r, c)
             # Valid click, get reward score: 2
            reward = 2.0
            # Check if victory condition is met, if win, get reward score: 200
            if self.check_victory():
                self.game_over = True
                self.won = True
                return self.get_state(), 200, True, {}
            
            return self.get_state(), reward, False, {}
        
        # Flag cell
        else:
            flag_action = action - cells
            r = flag_action // self.cols
            c = flag_action % self.cols
            # If cell is clicked or flagged, get penalty score -1, game continues
            if self.revealed[r][c]:
                return self.get_state(), -1, False, {}
            # Toggle cell flag status
            self.flagged[r][c] = not self.flagged[r][c]
            
            if self.flagged[r][c] and (r, c) in self.mine_locations:
                reward = 10.0 # Correctly flag mine: 10
            elif not self.flagged[r][c] and (r, c) in self.mine_locations:
                reward = -4.0 # Cancel correctly flagged mine: -4
            elif self.flagged[r][c] and (r, c) not in self.mine_locations:
                reward = -5.0 # Wrongly flag mine: -5
            else:
                reward = 1.0 # Cancel wrongly flagged mine: 1
            # Check if victory condition is met, if win, get reward score: 200
            if self.check_victory():
                self.game_over = True
                self.won = True
                return self.get_state(), 200, True, {}
            
            return self.get_state(), reward, False, {}
    
    def auto_expand(self, r, c): # Auto expand empty area
        queue = deque([(r, c)]) # Initialize queue of all pending empty cells
        visited = set([(r, c)]) # Initialize set of processed cells
        # Loop when queue is not empty
        while queue:
            cr, cc = queue.popleft()
            # Traverse the 8 cells around the current cell in turn
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    nr = cr + dr
                    nc = cc + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols: # Boundary check
                        # Process unvisited, unclicked, unflagged cells
                        if (nr, nc) not in visited and not self.revealed[nr][nc] and not self.flagged[nr][nc]:
                            visited.add((nr, nc)) # Mark as visited
                            self.revealed[nr][nc] = True # Click this adjacent cell
                            # If this cell has no mines around, add to queue
                            if self.board[nr][nc] == 0:
                                queue.append((nr, nc))
    
    def check_victory(self): # Win or not
        for r in range(self.rows):
            for c in range(self.cols):
                # If there are non-mine cells not clicked, not win
                if (r, c) not in self.mine_locations and not self.revealed[r][c]:
                    return False
        return True


## ImprovedMinesweeperAgent(Q-Learning) ##
class ImprovedMinesweeperAgent:
    def __init__(self, action_size, rows = 16, cols = 16, num_mines = 40):
        self.action_size = action_size # Total number of click + flag operations
        self.rows = rows
        self.cols = cols
        self.num_mines = num_mines
        # Q-table settings
        self.q_table = defaultdict(lambda: np.zeros(action_size)) # Parameter settings
        self.lr = 0.2 # Learning rate
        self.gamma = 0.99 # Discount factor
        self.epsilon = 1.0 # Exploration rate
        self.epsilon_decay = 0.995 # Exploration rate decay coefficient
        self.epsilon_min = 0.01 # Minimum exploration rate
        self.visit_count = defaultdict(lambda: np.zeros(action_size)) # Visit count (number of visits for each state-action pair)
        self.win_history = [] # Historical wins
        
    def choose_action(self, state, env, is_training=True): # Strategy selection
        valid_actions = env.get_valid_actions()
        if not valid_actions:
            return None
        # 1.Logical reasoning
        safe_cells, mine_cells = env.get_safe_cells()
        cells = self.rows * self.cols
        # Prioritize clicking safe cells
        if safe_cells:
            safe_actions = [r * self.cols + c for r, c in safe_cells]
            safe_actions = [a for a in safe_actions if a in valid_actions]
            if safe_actions:
                return random.choice(safe_actions)
        # Then flag mine cells
        if mine_cells:
            mine_actions = [r * self.cols + c + cells for r, c in mine_cells]
            mine_actions = [a for a in mine_actions if a in valid_actions]
            if mine_actions:
                return random.choice(mine_actions)
        
        # 2.Random selection (Explore unknown areas)
        if is_training and random.random() < self.epsilon:
            return random.choice(valid_actions)
        
        # 3.Choose high-score actions (Select high-score actions when no reasoning results and no exploration)
        action_scores = []
        for action in valid_actions:
            q_score = self.q_table[state][action] # Get Q value
            
            if action < cells: # A.Click
                r = action // self.cols
                c = action % self.cols
                
                # (1).Corner > Edge > Center
                if (r == 0 or r == self.rows-1) and (c == 0 or c == self.cols-1): 
                    heuristic = 3.0
                elif r == 0 or r == self.rows-1 or c == 0 or c == self.cols-1:
                    heuristic = 2.0
                else:
                    heuristic = 1.0
                
                # (2).More clicked surrounding cells are better
                surrounding = 0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr = r + dr
                        nc = c + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols: # Boundary check
                            if env.revealed[nr][nc]: # Count the number of clicked surrounding cells
                                surrounding += 1
                # Calculate score: Q value*3 + Position weight*3 + Number of clicked surrounding cells*1
                total = q_score * 3 + heuristic * 3 + surrounding * 1.0 

            else: # B.Flag
                total = q_score * 2.0 # Calculate score: Q value*2
            
            action_scores.append((action, total))
        # Sort by score in descending order
        action_scores.sort(key=lambda x: x[1], reverse=True) 
        # Randomly select one from the top 3 highest-score actions
        top_actions = [a for a, _ in action_scores[:3]] 
        return random.choice(top_actions)
    
    def update(self, state, action, reward, next_state, done, env):
        self.visit_count[state][action] += 1 # Number of visits
        # Dynamic learning rate: more visits lead to more stable convergence in later stages
        alpha = self.lr / (1 + 0.05 * math.log1p(self.visit_count[state][action]))
        current_q = self.q_table[state][action] # Current Q value
        # TD learning
        if done:
            max_next_q = 0
        else:
            valid_next = env.get_valid_actions()
            if valid_next: # epsilon-greedy exploration
                max_next_q = max([self.q_table[next_state][a] for a in valid_next])
            else:
                max_next_q = 0
        # Updated Q value: Current Q value + Learning rate (Immediate reward + Discount*Future Q value - Current Q value)
        new_q = current_q + alpha * (reward + self.gamma * max_next_q - current_q)
        self.q_table[state][action] = new_q
    
    def decay_epsilon(self): # Exploration decay rate
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay


## Training ##
def train_model(episodes=1000):
    print("16x16 Minesweeper AI Training System (40 mines)")
    print(f"Number of training games: {episodes}")
    
    env = MinesweeperEnv(rows = 16, cols = 16, num_mines = 40)
    # Initialize agent
    agent = ImprovedMinesweeperAgent(
        action_size = env.action_size,
        rows = 16,
        cols = 16,
        num_mines = 40
    )
    # Initialize training variables
    win_count = 0 # Total number of wins
    best_win_rate = 0 # Best win rate
    recent_wins = deque(maxlen =  100) # Win/loss records of the last 100 games
    # Training start time
    start_time = time.time()
    
    for episode in range(1, episodes + 1):
        state = env.reset() # Initial state
        done = False # End flag
        steps = 0 # Number of steps
        # Main game loop
        while not done and steps < 300: # Game not ended and steps less than 300
            # Choose action
            action = agent.choose_action(state, env, is_training = True)
            if action is None:
                break
            # Execute the selected action, feedback next state, reward, game end status, additional information
            next_state, reward, done, info = env.step(action)
            # Update Q-table
            agent.update(state, action, reward, next_state, done, env)
            # Enter next state and start a new round of decision-making
            state = next_state
            # Steps +1
            steps += 1
        
        if env.won: # Win
            win_count += 1
            recent_wins.append(1)
        else: # Lose
            recent_wins.append(0)
        # Decay exploration rate
        agent.decay_epsilon()
        # Print information every 100 episodes
        if episode % 100 == 0:
            current_win_rate = win_count / episode # Cumulative win rate
            recent_rate = sum(recent_wins) / len(recent_wins) # Win rate of the last 100 games
            elapsed = time.time() - start_time # Time elapsed
            # Update best win rate
            if recent_rate > best_win_rate:
                best_win_rate = recent_rate
            
            print(f"Episode {episode:4d}/{episodes}")
            print(f"Win rate: {current_win_rate:.3f} | Recent 100: {recent_rate:.3f}")
            print(f"Best win rate: {best_win_rate:.3f} | Epsilon: {agent.epsilon:.3f}")
            print(f"Elapsed: {elapsed:.1f}s")
    
    final_win_rate = win_count / episodes # Final win rate

    print(f"Training completed")
    print(f"Final win rate: {final_win_rate:.3f}")
    print(f"Best win rate: {best_win_rate:.3f}")
    print(f"Total elapsed: {time.time() - start_time:.1f}s")
    
    return env, agent, best_win_rate


## MinesweeperGUI ##
class MinesweeperGUI:
    def __init__(self, env, agent, win_rate):
        self.env = env
        self.agent = agent
        self.win_rate = win_rate
        self.root = tk.Tk() # Main window
        self.root.title("Minesweeper AI Demonstration (16x16, 40 mines)") # Window title
        self.root.resizable(False, False) # Fixed window size
        self.cell_size = 30 # Size of each cell
        self.padding = 3 # SChessboard padding
        self.canvas_width = env.cols * self.cell_size + 2 * self.padding # Width
        self.canvas_height = env.rows * self.cell_size + 2 * self.padding # Height
        # Color of numbers corresponding to the number of mines in adjacent cells
        self.colors = {
            1: "#0000FF", 2: "#008000", 3: "#FF0000", 4: "#000080",
            5: "#800000", 6: "#008080", 7: "#000000", 8: "#808080"
        }
        
        self.root.update() # Main window update
        self.setup_ui()
        self.ai_thinking = False # AI thinking
        self.auto_mode = False # Manual step
        self.stats = {"wins": 0, "losses": 0, "games": 0} # Data statistics
        self.root.minsize(width=self.canvas_width + 50, height=self.canvas_height + 150)
    
    def setup_ui(self):
        self.root.grid_columnconfigure(0, weight=1)
        # 1.1.Top status bar
        info_frame = tk.Frame(self.root, bg='#f0f0f0', height=40)
        info_frame.grid(row=0, column=0, sticky="ew", pady=5)
        info_frame.grid_propagate(False)
        # Training win rate label
        self.training_label = tk.Label(info_frame, text=f"Training Win Rate: {self.win_rate*100:.1f}%", 
                                       font=("Arial", 10, "bold"), fg="blue", bg='#f0f0f0', width=20)
        self.training_label.pack(side=tk.LEFT, padx=10)
        # Game status label
        self.status_label = tk.Label(info_frame, text="Game Started", 
                                     font=("Arial", 11, "bold"), fg="green", bg='#f0f0f0', width=15)
        self.status_label.pack(side=tk.LEFT, padx=20)
        # Real-time win rate label
        self.stats_label = tk.Label(info_frame, text="Current Win Rate: 0% (0/0)",
                                   font=("Arial", 10), fg="purple", bg='#f0f0f0', width=20)
        self.stats_label.pack(side=tk.LEFT, padx=10)

        # 2.Canvas frame
        canvas_frame = tk.Frame(self.root, width=self.canvas_width, height=self.canvas_height)
        canvas_frame.grid(row=1, column=0, pady=10)
        canvas_frame.grid_propagate(False)
        self.canvas = tk.Canvas(canvas_frame, 
                               width=self.canvas_width,
                               height=self.canvas_height,
                               bg='#C0C0C0', highlightthickness=0)
        self.canvas.pack()
        # 3.Bottom operation area
        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.grid(row=2, column=0, pady=10)
        # Button style
        button_style = {"font": ("Arial", 10, "bold"), "width": 10, "height": 1}
        # New game button
        tk.Button(ctrl_frame, text="New Game", command=self.new_game,
                 bg="#90EE90", **button_style).pack(side=tk.LEFT, padx=5)
        # Manual step button
        tk.Button(ctrl_frame, text="Step Play", command=self.ai_move,
                 bg="#87CEEB", **button_style).pack(side=tk.LEFT, padx=5)
        # Auto step button
        tk.Button(ctrl_frame, text="Auto Play", command=self.toggle_auto,
                 bg="#F4E174", **button_style).pack(side=tk.LEFT, padx=5)
        # Exit button
        tk.Button(ctrl_frame, text="Exit", command=self.root.destroy,
                bg="#FEC7CF", **button_style).pack(side=tk.LEFT, padx=5)
        # Game activation
        self.game_active = True
        self.draw_board()
    
    # Draw canvas
    def draw_board(self):
        self.canvas.delete("all") # Initialize canvas
        
        for r in range(self.env.rows):
            for c in range(self.env.cols): # Top-left coordinates (x1,y1) and bottom-right coordinates (x2,y2)
                x1 = c * self.cell_size + self.padding
                y1 = r * self.cell_size + self.padding
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                # Draw black border of cell
                self.canvas.create_rectangle(x1, y1, x2, y2, outline='black', width=1)
                # 1.Cell is clicked
                if self.env.revealed[r][c]:
                    # Fill white
                    self.canvas.create_rectangle(x1+1, y1+1, x2-1, y2-1, 
                                                fill='white', outline='')
                    # 1.1.Cell has mines around: fill corresponding number字
                    if self.env.board[r][c] > 0:
                        color = self.colors.get(self.env.board[r][c], "black")
                        self.canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                                               text=str(self.env.board[r][c]), fill=color, font=("Arial", 16, "bold"))
                    # 1.2.Cell is mine: fill 💣 icon
                    elif self.env.board[r][c] == -1:
                        self.canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                                               text="💣", fill="red", font=("Arial", 16))
                # 2.Cell is flagged: fill light pink, fill 🚩 icon
                elif self.env.flagged[r][c]:
                    self.canvas.create_rectangle(x1+1, y1+1, x2-1, y2-1, 
                                                fill='#FFB6C1', outline='red', width=2)
                    self.canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                                           text="🚩", fill="red", font=("Arial", 18))
                # 3.Cell is not clicked or flagged: default gray
                else:
                    self.canvas.create_rectangle(x1+1, y1+1, x2-1, y2-1, 
                                                fill='#808080', outline='')
        self.root.update()
    
    # AI thinking
    def ai_move(self):
        if not self.game_active or self.ai_thinking:
            return
        # AI starts thinking
        self.ai_thinking = True
        self.status_label.config(text="Reasoning", fg="blue") # Update status label
        self.root.update()
        # AI chooses action
        state = self.env.get_state()
        action = self.agent.choose_action(state, self.env, is_training=False)
        # AI executes action
        if action is not None:
            _, reward, done, info = self.env.step(action)
            # Judge action type
            action_type = "open" if action < self.env.rows * self.env.cols else "flag"
            # Update status label
            self.status_label.config(text=f"{action_type} cell", fg="green")
            self.draw_board()
            
            if done:
                self.handle_game_end()
        # AI finishes thinking
        self.ai_thinking = False

        # Auto mode
        if self.auto_mode and self.game_active:
            self.root.after(300, self.ai_move)
    
    def handle_game_end(self): 
        if self.env.won: # Game win handling
            self.status_label.config(text="🎉 Win!! 🎉", fg="green")
            self.stats["wins"] += 1
        else: # Game loss handling
            self.status_label.config(text="Game Over", fg="red")
            self.stats["losses"] += 1
        
        self.stats["games"] += 1 # Total games +1
        self.game_active = False # Mark game as inactive
        self.auto_mode = False # Turn off auto mode
        # Calculate and update label
        win_rate = self.stats["wins"] / self.stats["games"] * 100
        self.stats_label.config(text=f"Current Win Rate: {win_rate:.1f}% ({self.stats['wins']}/{self.stats['games']})")
    
    def new_game(self): # Reset game environment
        self.env.reset()
        self.game_active = True
        self.auto_mode = False
        self.ai_thinking = False
        self.status_label.config(text="New Game", fg="green")
        self.draw_board()

    def toggle_auto(self): # Start new game first when game is inactive
        if not self.game_active:
            self.new_game()
        # Toggle auto mode
        self.auto_mode = not self.auto_mode
        if self.auto_mode: # Auto
            self.status_label.config(text="Auto Play Mode", fg="purple")
            self.root.after(500, self.ai_move)
        else: # Non-auto
            self.status_label.config(text="Manual Mode", fg="green")

    def run(self): #Start main loop
        self.root.mainloop()

if __name__ == "__main__":
    print("Minesweeper AI System Starting...")
    # Number of training episodes: 1000 games
    episodes = 1000
    print(f"Start auto training for {episodes} episodes, please wait...\n")
    # Call function to start training
    trained_env, trained_agent, best_win_rate = train_model(episodes=episodes)
    # Prompt message after training completion
    print("\nTraining completed, launching game interface...")
    
    try:
        gui = MinesweeperGUI(trained_env, trained_agent, best_win_rate)
        gui.run()
    except Exception as e:
        print(f"GUI launch failed: {e}")
        input("Press Enter to exit...")
