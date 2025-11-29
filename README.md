🎮 MAZE ESCAPE (Python + Pygame)

Simple and fun 2D maze game built with Python + Pygame.
Choose your ghost (Pink or Blue) and reach the Exit (E) without hitting the walls.


✨ FEATURES

5 playable levels

2D outline cartoon style

Smooth movement

Character selection (Pink / Blue ghost)

Timer + best-time saving (local best_time.json)

Map loading from .txt files

Online scoreboard integration (n8n + Base44)

Saves player_name and total time

Displays real-time leaderboard on a Base44 app


🎮 CONTROLS

W A S D → Move

R → Restart

ESC → Quit


🚀 RUN THE GAME
pip install -r requirements.txt
python main.py


🌐 ONLİNE SCOREBOARD (n8n + Base44)

When a player finishes all levels, the game:

1️⃣ Sends a POST request to an n8n webhook:
{
  "player_name": "<name>",
  "score": <total_time_in_seconds>
}

2️⃣ n8n stores this in the maze_scores data table.
3️⃣ Another n8n workflow exposes a GET endpoint that returns all scores as JSON.
4️⃣ A Base44 App (Maze Escape Scoreboard):

Fetches this data in real-time

Sorts players by best (lowest) time

Shows a clean leaderboard UI


👉 PUBLIC LEADERBOARD:
https://maze-escape-scoreboard-1f552fa2.base44.app


FEYZA BALABAN
