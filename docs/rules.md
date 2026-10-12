# FrontLine Rules (v1)

## Board
- 5×5 grid. Columns A–E, rows 1–5 (A1 is top-left, E5 is bottom-right).
- Cells are adjacent up, down, left, or right. Diagonals do not count.
- Each cell is empty or owned by one player, and owned cells have a strength from 1 to 5.

## Setup
- Coral's home is A1. Teal's home is E5.
- The first mover's home starts at strength 3, the second mover's at 2. All other cells start empty.
  (Offsets the second mover's last-turn edge, like komi in Go. Greedy vs greedy: 54% / 47% first/second.)
- Players swap who moves first each game.

## Turns
- Players alternate turns. Each player gets 12 turns (24 total).
- On each turn, a player takes exactly one action.

## Actions

### 1. Claim
- Take an empty cell adjacent to a cell you own.
- The claimed cell starts at strength 1.

### 2. Reinforce
- Add 1 strength to any cell you own.
- Strength cannot go above 5.

### 3. Attack
- Choose one of your cells and an adjacent enemy cell.
- **Attack power** = your attacking cell's strength + 1 for each other cell you own that also touches the target.
- **If attack power is greater than the target's strength:** you capture the target.
  - The captured cell's strength = your attacking cell's strength − the target's strength (minimum 1). Support does not add to this.
  - Your attacking cell drops to 1.
- **Otherwise the attack fails:** your attacking cell loses 1 strength. Ties favor the defender.

## Supply
- After every turn, each of a player's cells must connect to that player's home through a path of their own adjacent cells.
- Any cell without that connection loses 1 strength.
- A cell that reaches 0 becomes empty.

## Home cells
- A home cell can only change owner by being captured in an attack.
- A home cell's strength can never drop below 1.
- Capturing the enemy home wins the game immediately.

## Game end
1. Capturing the enemy home wins immediately.
2. Otherwise, after 12 turns each, the player who owns more cells wins.
3. If tied, the player with higher total strength wins.
4. If still tied, the game is a draw.

## Illegal actions
- An illegal action forfeits the turn.
- The engine logs the action and the reason it was illegal.

## Worked example
Coral's C3 has strength 4, and Coral also owns C2, which touches Teal's D3 (strength 3)...
