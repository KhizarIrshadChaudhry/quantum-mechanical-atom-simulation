"""
elektron.py er til Elektron klassen der repræsenterer ET elektron i et hydrogen-lignende atom
samler kvantetal (n, l, m), partikeldata (positioner og farver) og logikken for at sample bølgefunktionen et sted

nogle regler for kvantetal, fra mit SOP om kvantemekanik:
n >= 1
l IN [0, n-1]
m IN [-l, l]
"""

import numpy as np
from sampler import sample_orbital
from particles import compute_colors


class Electron:
    def __init__(self, n: int, l: int, m: int, n_particles: int):
        """
        Opret en elektron skyen med kvantetal og sample positionernene 

        Args:
            n: Orbital nummer (energiniveau), n => 1
            l: Azimutalt (orbitalform), 0 =< l =< n-1 (0=s, 1=p, 2=d, 3=f ...)
            m: Magnetisk kvantumtal (orientering), -l =< m =< l
            n_particles: Antal punkter der samples fra bølgefunktionen kommer fra slideren fra enginne.py
        """
        self.n_particles = n_particles

        # Sæt kvantumtal og sample 
        self._n = n
        self._l = l
        self._m = m

        #type declarations for positions og colors, som bliver udfyldt i sample() metoden clean code babyyy
        self.positions: np.ndarray | None = None
        self.colors:    np.ndarray | None = None

        self.sample()

    # ÆNDRE metoderne til properties så de er read-only udefra, og ændres kun gennem set_kvantumtal() metoden der håndhæver reglerne for kvantetal
    @property
    def n(self) -> int:
        return self._n

    @property
    def l(self) -> int:
        return self._l

    @property
    def m(self) -> int:
        return self._m

    # methoods to update kvantetal, sample og repræsentation

    def set_kvantumtal(self, n: int, l: int, m: int):
        """
        Opdater kvantumtallene og re-sample elektronen.

         automatisk reglerne
            l = min(l, n-1)  l kan aldrig overstige n-1
            m = clamp(m, -l, l)  m skal ligge inden for [-l, l]
        """
        self._n = max(1, n)
        self._l = min(max(0, l), self._n - 1)
        self._m = max(-self._l, min(self._l, m))
        self.sample()

    def sample(self):
        """
        Sample elektronen positioner fra bølgefunktionen psi(n, l, m)
        og beregn farver baseret på densiity  tæthed.

        Resultater gemmes i self.positions og self.colors.
        """
        print(f"\nSampler orbital  n={self._n}  l={self._l}  m={self._m} med {self.n_particles} partikler")
        self.positions = sample_orbital(self._n, self._l, self._m, self.n_particles)
        self.colors    = compute_colors(self.positions)
        print("Rendereed done")