"""
particles.py er håndtere hver eneste wavefunction punkt sampling og farveberegning baseret på densitet.

her betyder partiklen blot en position i rummet hvor elektronen kan være, og farven repræsenterer hvor sandsynligt det er at finde elektronen der (tæthed).

de regioner hvor der er mange partikler samlet (høj sandsynlighed) skal se lyse/white ud. 
De andre regioner (lav sandsynlighed) skal være mørke.

steps
1. del rummet op i voxels (n*n*n grid) (3D pixels) og tæl hvor mange partikler der er i hver voxel
2. udregn antallet af partikler i hvert voxel 
3. hver partikel får den tælling som dens voxel har (hvor mange partikler er i samme voxel)
4. normaliser tællingen til [0, 1] og map igennem inferno colormap for at få farver, color mappen fra matplotplib
5. juster alpha kanalen så tætte regioner mere opake (synlige) og sjældne regioner er mere transparente (så de ikke overvælder billedet)

inferno colormap går fra:
    0.0: sprt/mørk lilla  (sjældne positioner, lavsandsynlighed)
    0.5:  red/orange    (moderat sandsynlighed)
    1.0:  yellow/white (almindelige positioner, høj sandsynlighed)

"""

import numpy as np
import matplotlib.pyplot as plt

# matplotlibs inferno colormap, som vi bruger til at mappe densitet til farve
_colormap = plt.get_cmap("inferno") #evt. også magma eller hot https://matplotlib.org/stable/users/explain/colors/colormaps.html


def compute_colors(positions: np.ndarray, n_bins: int = 60) -> np.ndarray:
    """
    Estimere lokal partikel tæthed og returnere en RGBA farve per partikel.
    Args:
        positions : (N, 3) float32 array — partikel xyz positioner i pm
        n_bins: opløsning af 3D tæthetsgrid (60^3 = 216,000 voxels)
    Retruner:
        (N, 4) float32 array af RGBA farver, hver værdi i [0, 1]

    Højere n_bins = finere tæthetsopløsning, men langsommere at beregne
    60 bins er en god balance mellem kvalitet og hastighed udfra erfaring nu
    """

    coords = positions.copy()

    # positioner mapping til voxels:
    # 1. find bounding box for alle partiklerne
    # 2. normaliser positionerne til [0, n_bins-1] i hver dimension
    # 3. konverter til int for at få voxel index
    mins   = coords.min(axis=0)
    maxs   = coords.max(axis=0)
    ranges = maxs - mins
    ranges[ranges == 0] = 1.0    # ingen division me 0 for dimensioner med ingen spredning

    voxel = ((coords - mins) / ranges * (n_bins - 1)).astype(int)
    voxel = np.clip(voxel, 0, n_bins - 1)

    # tæl partikler pr voxel
    #konverter voxel index (ix, iy, iz) til enkelt flat index for tælling fordi np.bincount kun virker på 1D arrays
    #   flat = ix * n^2 + iy * n + iz wikipedia 3D array indexing https://en.wikipedia.org/wiki/Row-_and_column-major_order#Multidimensional_arrays
    flat   = (voxel[:, 0] * n_bins**2 +
              voxel[:, 1] * n_bins    +
              voxel[:, 2])
    counts = np.bincount(flat, minlength=n_bins**3).astype(np.float32)

    # udregn density for hver partikel baseret på tællingen i dens voxel og normalisere til range af 0 til 1
    density = counts[flat]                     
    density = density / density.max()          # normaliser [0, 1]

    # densitity range 0 til 1 mappes til inferno colormap for at få RGBA farver
    rgba = _colormap(density).astype(np.float32)   # RGBA farver i [0, 1]

    # alpha justeres, så tætte regioner er mere opake (synlige) og sjældne regioner er mere transparente (så de ikke overvælder billedet).
    #ganges med 2.0 så selv moderate tætheder er tydelige, og klippes til [0.05, 0.95] for at undgå helt gennemsigtige eller helt opake partikler
    rgba[:, 3] = np.clip(density * 2.0, 0.05, 0.95)

    return rgba
