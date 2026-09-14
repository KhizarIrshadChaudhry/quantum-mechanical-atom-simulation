# Quantum Mechanical Simulation of Hydrogen Orbitals

![3d orbital](3,2,0%20orbital.png)


The following .md file is written by AI.

This project is an interactive visualization of the quantum-mechanical
orbitals of a hydrogen atom. It samples the electron's probability
distribution from the wavefunction `ψ(n, l, m)` and renders the
resulting positions as a real-time particle cloud.

The project was developed as my **Programming B final examination
project in 3.G at the Danish HTX (Higher Technical Examination
Programme)** at **NEXT Sukkertoppen HTX**, and achieved a **grade 12**.

## Install dependencies

``` bash
pip install -r requirements.txt
```

## Run

``` bash
python main.py
```

## Controls

  Key / Action      Effect
  ----------------- --------------------------------------
  W / S             Increase / decrease n (energy level)
  E / D             Increase / decrease l (shape)
  R / F             Increase / decrease m (orientation)
  Left mouse drag   Orbit camera around the atom
  Mouse scroll      Zoom in / out

## Quantum number rules (enforced automatically)

-   `l` must be in `[0, n-1]`
-   `m` must be in `[-l, l]`

## Interesting orbitals to try

  n   l   m   Name   Shape
  --- --- --- ------ ---------------------
  1   0   0   1s     Sphere
  2   0   0   2s     Sphere with shell
  2   1   0   2p₀    Dumbbell (z-axis)
  2   1   1   2p±₁   Dumbbell (xy-plane)
  3   2   0   3d₀    Double dumbbell
  3   2   2   3d±₂   Four-leaf clover
  4   3   0   4f₀    Complex multi-lobe

## How it works

The application converts the mathematical probability distribution of a
hydrogen atom's electron into a visual particle cloud.

### 1. Wavefunction and probability distribution

For a hydrogen atom, the wavefunction is represented using the quantum
numbers `n`, `l`, and `m`. The program uses the probability density

`|ψ|²`

to determine where electron positions are likely to occur.

Rather than trying to render the continuous probability distribution
directly, the program generates discrete particle positions that follow
the same probability distribution.

### 2. CDF sampling

The core sampling algorithm uses **inverse transform sampling based on a
cumulative distribution function (CDF)**.

The process is approximately:

``` text
Probability distribution
        ↓
Evaluate probability at discrete points
        ↓
Normalize probabilities
        ↓
Build cumulative distribution (CDF)
        ↓
Generate random values between 0 and 1
        ↓
Map values onto the CDF
        ↓
Sample electron positions
```

The sampling is performed for the radial coordinate and polar angle,
while the azimuthal angle is sampled uniformly.

This produces a particle cloud whose density represents the probability
of finding the electron in different regions of space.

### 3. Electron class and quantum numbers

The project uses an object-oriented `Electron` class to keep the quantum
numbers, sampled positions, and particle colors together.

The class automatically enforces the physical rules:

``` text
n ≥ 1
0 ≤ l ≤ n - 1
-l ≤ m ≤ l
```

This means invalid combinations cannot be passed through to the rest of
the application.

### 4. Particle density and colours

After positions are sampled, the program estimates local particle
density using a voxel grid.

Higher-density regions receive stronger/brighter colours and greater
visibility, making the structure of the orbital easier to see.

### 5. OpenGL rendering

The visualization is rendered directly through **OpenGL using PyOpenGL
and GLFW**.

The project uses:

-   **VAO (Vertex Array Object)** to describe how vertex data is
    structured.
-   **VBO (Vertex Buffer Object)** to store particle positions and
    colours on the GPU.
-   **GLSL vertex shaders** to transform particles into screen
    coordinates.
-   **GLSL fragment shaders** to render particles as soft, glowing
    points.

This allows the application to render very large particle clouds in real
time. The project was designed to support up to **1,000,000 particles**.

### 6. Application structure

The codebase is split into separate modules with clear responsibilities:

  Module           Responsibility
  ---------------- ---------------------------------------------------------
  `main.py`        Application entry point, input handling and render loop
  `engine.py`      OpenGL setup, rendering, shaders, VAO/VBO and HUD
  `camera.py`      Orbit camera and camera transformations
  `electron.py`    Electron object and quantum-number handling
  `sampler.py`     Probability calculations and CDF sampling
  `particles.py`   Particle density calculation and colour mapping

The separation allows the sampling, object-oriented logic, camera, and
rendering systems to be developed independently.

## Project documentation

The full documented project paper is included in the repository as:

**`Quantum Mechanical Simulation of Hydrogen Orbitals DOCS.pdf`**

The document contains the project requirements, technical background,
architecture, CDF sampling implementation, object-oriented design,
OpenGL/GLSL GPU pipeline, development process, testing, discussion, and
conclusion.

The paper also documents the implementation of the `Electron` class, the
CDF sampler, the VAO/VBO pipeline, GLSL shaders, and the testing of
orbital configurations.

## Academic context

This was a **Programming B final examination project** completed during
**3.G at HTX in Denmark**.

-   **Programme:** HTX (Higher Technical Examination Programme)
-   **Year:** 3.G
-   **Subject:** Programming B
-   **Project type:** Final examination project
-   **School:** NEXT Sukkertoppen HTX
-   **Author:** Khizar Irshad Chaudhry
-   **Submitted:** April 2026
-   **Grade:** 12

## Language disclaimer

**Please note:** The full project documentation/paper and other academic
materials are written in **Danish**, as the project was completed as
part of the Danish HTX education system.

This README is written in English to provide an accessible overview of
the project for readers who do not speak Danish.

## Technologies

-   Python
-   NumPy
-   PyOpenGL
-   GLFW
-   OpenGL
-   GLSL
-   Matplotlib colour mapping

## Project goal

The main goal was to design and implement an **object-oriented,
interactive Python program that visualizes a hydrogen atom's electron
probability distribution as a particle cloud and renders hundreds of
thousands of particles in real time through OpenGL**.

The project focuses primarily on the programming and
software-engineering challenges involved in turning a mathematical
probability distribution into an interactive GPU-rendered visualization.
