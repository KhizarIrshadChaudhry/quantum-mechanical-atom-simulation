# Quantum Orbital Visualizer - Setup & Run

## Install dependencies
```bash
pip install -r requirements.txt
```

## Run
```bash
python main.py
```

## Controls
| Key / Action         | Effect                              |
|----------------------|-------------------------------------|
| W / S                | Increase / decrease n (energy level)|
| E / D                | Increase / decrease l (shape)       |
| R / F                | Increase / decrease m (orientation) |
| Left mouse drag      | Orbit camera around the atom        |
| Mouse scroll         | Zoom in / out                       |

## Quantum number rules (enforced automatically)
- `l` must be in `[0, n-1]`
- `m` must be in `[-l, l]`

## Interesting orbitals to try
| n | l | m | Name  | Shape              |
|---|---|---|-------|--------------------|
| 1 | 0 | 0 | 1s    | Sphere             |
| 2 | 0 | 0 | 2s    | Sphere with shell  |
| 2 | 1 | 0 | 2p₀   | Dumbbell (z-axis)  |
| 2 | 1 | 1 | 2p±₁  | Dumbbell (xy-plane)|
| 3 | 2 | 0 | 3d₀   | Double dumbbell    |
| 3 | 2 | 2 | 3d±₂  | Four-leaf clover   |
| 4 | 3 | 0 | 4f₀   | Complex multi-lobe |
