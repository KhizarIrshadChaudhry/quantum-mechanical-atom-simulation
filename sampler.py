"""
sampler.py sampler elektronens mulige positioner i rummet ved tilfældige sampling fra bølgefunktionen psi(n, l, m)
det er her alt fysikken sker, bølgefunktionen laves om til en sandsynlighedsfordeling, og så samples der positioner ud fra den fordeling

FYSIK NOTER FRA SOP:

I kvantemekanik er elektronen i et hydrogenatom ikke en partikel, der kredser om kernen.
Den er en STÅENDE BØLGE beskrevet af en bølgefunktion psi(r, theta, φ).

Sandsynligheden for at finde elektronen på en given position er |psi|².

På grund af den sfæriske symmetri i problemet, kan psi opdeles i to uafhængige dele, der kan løses separat, og opdelses 
    psi(r, theta, φ) =  R_nl(r)  *  Y_l^m(theta, φ)

  R_nl(r) Radial bølgefunktion
  Beskriver hvordan sandsynligheden varierer med afstanden fra kernen
  Bygget op af associerede Laguerre polynomier  https://en.wikipedia.org/wiki/Laguerre_polynomials

  Y_l^m(theta,φ) Sfæriske harmoniske
  Beskriver formen/orienteringen (lobes) af orbitalen
  Bygget op af associerede Legendre polynomier https://en.wikipedia.org/wiki/Associated_Legendre_polynomials

  disse to dele løses separat, og så kombineres de for at få den fulde bølgefunktion. 
  Derefter sandsynligheden |psi|² udregnes, og så samples der positioner ud fra den fordeling.




KVANTATAL:
nogle regler for kvantetal, fra mit SOP om kvantemekanik:
n >= 1
l IN [0, n-1]
m IN [-l, l]

SAMPLINGS ALGORITME (CDF sampling):

Vi kan ikke bare plukke partikel positioner direkte fra en formel.
I stedet bruger vi CDF (cumulative distribution function) sampling wiki: https://en.wikipedia.org/wiki/Inverse_transform_sampling
Algoritmen består af følgende trin:
  1. Evaluere sandsynlighedstætheden P(x) ved mange jævnt fordelte punkter.
  2. Normaliseringen: dividere med totalen så sandsynlighederne summerer til 1.
  3. Cumulative sum CDF: en trappefunktion fra 0 til 1, hvor brede trapper svarer til høje sandsynlighedsregioner.
  4. Tegn tilfældige tal u i [0, 1].
  5. For hver u, find hvor det lander på trappen: det x er en sample.
Dette konverterer enhver sandsynlighedsfordeling til et sæt diskrete punkter, der er fordelt præcis i henhold til den fordeling.

Dette gøres tre gange for at få de tre koordinater:
r  fra P(r) = r^2 |R_nl(r)|^2    (radial)
theta fra P(theta)   = |Y_l^m(theta,0)|^2 sin(theta)  (polære vinkel)
phi uniform in [0, 2pi] (azimutal vinkel er flad)
"""

import numpy as np
from scipy.special import genlaguerre # Laguerre polynomier til radial bølgefunktion

from scipy.special import sph_harm_y
def _spherical_harmonic(l: int, m: int, theta: np.ndarray, phi: float | np.ndarray):
    return sph_harm_y(l, m, theta, phi) #spherisk harmonisk funktion til angulære fordeling, bestemmer form og orientering af orbitalen 
# https://en.wikipedia.org/wiki/Spherical_harmonics


"""
from scipy.special import sph_harm

def _spherical_harmonic(l: int, m: int, theta: np.ndarray, phi: float | np.ndarray):
    return sph_harm(m, l, phi, theta)""" #gammel version, virker ik mer i ny scipy



# The Bohr radius: the most probable electron distance in the ground state.
# Value in picometers — used to scale coordinates to match the display.
# bohr radius er den astimeret afstand fra kernen hvor elektronen er mest sandsynligt at finde i 1s orbitalet
#  bruges til at skalere koordinaterne til picometers for at få det til at passe med displayet
A0_PM = 52.9   # piiico meters


# radial sandsynligheds densitiy P(r) = r^2 |R_nl(r)|^2

def _radial_prob(n: int, l: int, r_bohr: np.ndarray) -> np.ndarray:
    """
    Returnere radial probablity density PP(r) = r^2 |R_nl(r)|^2 for hydrogen orbital (n, l).

      R_nl(r) er den radiale bølgefunktion, der bestemmer hvordan sandsynligheden varierer med afstanden fra kernen.
      propotionaliteten:
      R_nl(r) propto: exp(-p/2) · p^l · L_{n-l-1}^{2l+1}(p)
    hvor p = 2r/n er en dimensionløs skaleret radius bruh


    de tre faktoreres fysiske betydning:
      exp(-p/2)    bølgen aftager til nul langt fra kernen
      p^l højere l orbitaler har en node ved r=0
      L_{n-l-1}^{2l+1}(p)  Laguerre polynomium: skaber radiale noder

    SKAL IKKE NORMALISERESERS NU MEN R_nl(r) er allerede normaliseret, så vi skal bare gange med r^2 for at få den radiale sandsynlighedstæhed P(r) = r^2 |R_nl(r)|^2

    r_bohr er i Bohr radius enheder, så resultatet er også i Bohr radius enheder. Det skaleres senere til picometers i sample_orbital() funktionen.

    """
    rho = 2.0 * r_bohr / n                       # dimensionløs radius
    L   = genlaguerre(n - l - 1, 2 * l + 1)     # Laguerre polynomial objekt
    R   = np.exp(-rho / 2.0) * (rho ** l) * L(rho)
    return r_bohr**2 * R**2                       # r^2 |R|^2 radial sandsynlighedstæthed


# angulær sandsynligheds densitiy P(theta) = |Y_l^m(theta, 0)|^2 sin(theta)
#den anden var afstanden, denne her er retning
def _angular_prob(l: int, m: int, theta: np.ndarray) -> np.ndarray:
    """
    returnere angulær sandsynligheds densitiy P(theta) = |Y_l^m(theta, 0)|^2 sin(theta)
    Y_l^m er de sfæriske harmoniske der  giver direkte lobe-formerne, der ses i orbitaldiagrammerne (s=sphere, p=dumbbell, d=four-leaf
    sin(theta) er Jacobian for sfæriske koordinater hvr volumen elementet ved vinkel theta er proportionalt med sin(theta)
    så vi skal inkludere det for at få den 

    modtag array af vinkler theta og l,m og returnere sandsynlighed for hver retning


    sin(theta) er jacobian sferisk koordinater, volume elemetn på vinkel theta er propto sin(thta)

    phi = theta her cuz 

    HUSK sph_harm er nu sph_harm_y og argumentereene er ændret, derfor bruges alternativ _spherical_harmonic
    """
    Y = _spherical_harmonic(l, abs(m), theta, 0.0)
    return np.abs(Y)**2 * np.sin(theta)


# CDF SAMPLING FUNC

def _cdf_sample(x_vals: np.ndarray, prob: np.ndarray, n_samples: int) -> np.ndarray:
    """
   Konvertere sandsynlighed distrubation til punkter
   Tegn n_samples værdier distruberet jf. (x_vals, prob)

   algo:
   1. prob| og normalise så summen er 1
   2. tegn uniform tilfældige u værdier
   3. np.searchsorteret, for hveret u, find index hvor u vil være inserted i CDF og sort. Index er så sampled x value der
   
   flere punkter ved højere sandsynlighed, færre ved mindre (sandsynlighed fra 0-1)
    """
    prob = np.abs(prob)   
    prob /= prob.sum()                              #  1: normalise
    cdf = np.cumsum(prob)                         #  2: CDF
    cdf /= cdf[-1]                                 # trappefunc 0-1

    u = np.random.uniform(0.0, 1.0, n_samples)  # step 3
    indices = np.searchsorted(cdf, u) # step 4
    indices = np.clip(indices, 0, len(x_vals) - 1)
    return x_vals[indices]


# Main sampling funktion

def sample_orbital(n: int, l: int, m: int, n_particles: int = 50_000) -> np.ndarray:
    """
    Funktionen sampler elektron positioner fra hydrogen orbital med n,l,m

    Returnere
    np.ndarray med formen (n_particles,3)
    med hvert række af (x, y, z) pos i picometer

    Til det samples der:
    r (radial afstand): P(r) = r^2 |R_nl(r)|^2
    theta (polær vinkler): P(theta) = Y_l^m(theta,0)|^2 sin(theta)
    phi (azimuthal vinkel) uniformt mellem 0, 2pi

    det hele converteres fra (r, theta, phi) til (x,y,z) i picometers
    """

    #Step 1 er at sample den radiale afstand r
    r_max  = 10 * n**2 # maksimale afstand (over det er bølgefunc 0) i Bohr radii
    #bruger offset 1e-6 så der ik divideres med 0
    r_vals = np.linspace(1e-6, r_max, 3000)  # P(r) er kontinuært og har værdi over alle r, derfor kun evaluere 3000 punkter jævnt fordelt
    r_prob = _radial_prob(n, l, r_vals) # beregn sandslynligheden ved de 3000 punkter
    r_samp = _cdf_sample(r_vals, r_prob, n_particles)   # plukke n_particles antal elektron positioner fordelt over den sandsynlighed - resultat i Bohr radii

    # Step 2: Polær vinkel theta
    # theta kører fra 0 til pi (nord til syd)
    theta_vals = np.linspace(1e-6, np.pi - 1e-6, 2000) #samme som før 2000 evaluerations jævnt fordelt
    theta_prob = _angular_prob(l, m, theta_vals) #sandsynligheden ved alle værdier af 2000 tehta
    theta_samp = _cdf_sample(theta_vals, theta_prob, n_particles) #lave n_partikler fordelt med disse theta værdier

    # step 3: Azimuthal phi uniformt da alle vinkler er lige sandslynige
    #derfor har hydrogen wave func ingen phi dependency i sandsynligheden
    #DERFOR ER CDF ALGORITMEN IKKE NØDVENDIG HER
    phi_samp = np.random.uniform(0.0, 2.0 * np.pi, n_particles) #uniformt fordelt liste værdi fra 0 til 2pi, listen er n_particles lang

    # Step 4: Konverter sferiske koordinat (r, theta, phi) til (x,y,z) i picometer
    r_pm = r_samp * A0_PM                             # Bohr radii til pm, A0_PM blev defineret i starten
    x    = r_pm * np.sin(theta_samp) * np.cos(phi_samp)
    y    = r_pm * np.cos(theta_samp)
    z    = r_pm * np.sin(theta_samp) * np.sin(phi_samp)

    

    return np.stack([x, y, z], axis=1).astype(np.float32) #returnere en 3d array
    """
        3d array ligner sådan noget her: 
    [
      [ x0,  y0,  z0],   # partikel 0
      [ x1,   y1,   z1],   # partikel 1
      ....            ,
      [ xn,  yn,   zn],   # partikel n
    ]
    

    indeholder n antal (x,y,z) positioner for electronen
    """
