"""
camera.py er ansvarlig for at håndtere kamearaets position og orientering i 3d rummet
samt at generere MVP matrix der bruges i vertex shaderen til at transformere 3d koordinaterne til 2d screen space koordinater
når kameraet flyttes eller zoomes opdateres view matricen og dermed MVP matricen så det ser ud som om kameraet bevæger sig

kamearets  kigget altid på origo altså kernen
vælger at bruge polære koordinater:

azimuth   = vinkel horizontal ved y aksen altså venstre/højre 
elevation = vinkel vertikalt fra top altså op/ned 
radius    = afstanden til origo, bruger til zoom effekt 

vha. kamear polære koordinater udregnes mvp matricen hver frame og sendes til engine


MVP = Model * View * Projection
Model = gør intet da partikler allerede er i 3d og ikke har transformation nødvendig
View = look effekten fra kameraaet, bestemmer hvordan verden roteres og transleres så det ser ud som om kameraet bevæger sig
Projection = perspektiv effekt, fjerner z koordinaten og skalerer x,y for at simulere dybde og afstand

baby baby baby ooooo like baby baby baby nooo liike
though u always be miiiine
shi kl er 03.39 og jeg elsker diiis gpu bull ssssshhhhiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii 

kompelks stuff nu MVP
MVP matricen r  4x4 matrix der bruges til at transformere 3D koordinater til 2D screen space koordinater i vertex shaderen

den består af 3 matrixer. 
Model = [1, 0, 0, 0]
[0, 1, 0, 0]
[0, 0, 1, 0] 
[0, 0, 0, 1]

øverste er en identitets matrix 4x4 der ikke gører noget ved koordinaterne, da vores partikler allerede er i world space og ikke har nogen model transformation nødvendig
så 
[x]   [1, 0, 0, 0]   [x]
[y] * [0, 1, 0, 0] = [y]    altså præcis det samme punkt
[z]   [0, 0, 1, 0]   [z]
[1]   [0, 0, 0, 1]   [1]

det ka dog flyttes med
[1, 0, 0, tx]   [x]   [x + tx]
[0, 1, 0, ty] x [y] = [y + ty]   punktet er flyttet med translation tx,ty,tz
[0, 0, 1, tz]   [z]   [z + tz]
[0, 0, 0,  1]   [1]   [1     ]  1 ska indikere dette er et punkt og ikke vektor 


View matricen bestemmer vertexens position i 2d fra 3d alt efter kameraets position og orientering
kameraetes position og retning benyttes derfor i udregning af view matricen
derfor ændres view matricen når kameraet flyttes

btw kamera bevæger sig ikke men verticesne transformeres så det ser ud som om kameraet bevæger sig fkn hjernedødt matematik g
https://www.opengl-tutorial.org/beginners-tutorials/tutorial-3-matrices/#the-view-matrix


projection matricen tilføjer perspektiv ved at fjerne z koordinaten og skalere x,y for at simulerere dybde og afstand
udfra stackoverflow benyttes denne formel 
[f/aspect,  0,    0,                    0                  ]
[0,         f,    0,                    0                  ]
[0,         0,    (far+near)/(near-far), 2*far*near/(near-far)]
[0,         0,   -1,                    0                  ]
konstanter er i camera.py
  
disse tre matricer produktet af d er mvp matricen

reddit hjalp mig her gg
https://www.reddit.com/r/opengl/comments/x656w/am_i_understanding_the_mvp_matrices_correctly/
"""

import glfw
import numpy as np


class Camera:
    def __init__(self):
        # Polære koordinater for kameraets position
        self.azimuth   = 0.5          # radianer - starter lidt fra
        self.elevation = 1.1          # radianer ca 63°  vertikalt
        self.radius    = 300.0        # picometers estimeretr

        # target point i world space som kameraet altid kigger på, i dette tilfælde origo (kernen)
        self.target = np.zeros(3, dtype=np.float32)

        # mouse drag state for at håndtere kamera rotation
        self._dragging = False
        self._last_x   = 0.0
        self._last_y   = 0.0

        # zoom
        self._orbit_speed = 0.005
        self._zoom_speed  = 15.0

    #fubnc til polære til (x,y,z)
    def position(self) -> np.ndarray:
        """
        Konvertere polære kordinater (azimuth, elevation, radius) til (x, y, z)
        https://en.wikipedia.org/wiki/Spherical_coordinate_system#:~:text=below%20become%20switched.-,Conversely,-%2C%20the%20Cartesian%20coordinates

        fra wiki:  
        x = r * sin(elevation) * cos(azimuth)
        y = r * cos(elevation)          y er 
        z = r * sin(elevation) * sin(azimuth)
        """
        se = np.sin(self.elevation)
        ce = np.cos(self.elevation)
        sa = np.sin(self.azimuth)
        ca = np.cos(self.azimuth)
        return np.array([
            self.radius * se * ca,
            self.radius * ce,
            self.radius * se * sa,
        ], dtype=np.float32)


    #mvp matrix udregning
    def mvp_matrix(self, width: int, height: int) -> np.ndarray:
        """Udregn og returner en 4x4 float32 MVP matrix.
        view:
         tre vinkelrette akser bruges til at beskrive kameraets orientering:
          forward = retning fra kamera til target
          right = vinkelret på forward og world-up
          up = vinkelret på forward og right

        look-at matrixen roterer og translerer hele verden så:
        - kameraet sidder i origo og kigger ned ad -Z
        - "right" er +X, "up" er +Y
        """
        
        #btw M ska ik bruges så laver kun V og P, M er identitysmatrice

        pos     = self.position()
        forward = self.target - pos
        forward /= np.linalg.norm(forward)

        #view
        # Hvis forward og world_up er næsten parallelle, så brug Z aksen som up i stedet for Y aksen for at undgå gimbal lock
        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        if abs(np.dot(forward, world_up)) > 0.999:
            world_up = np.array([0.0, 0.0, 1.0], dtype=np.float32)

        right = np.cross(forward, world_up)
        right /= np.linalg.norm(right)
        up    = np.cross(right, forward)   # up er vinkelret på både forward og right

        view = np.array([
            [ right[0],    right[1],    right[2],   -np.dot(right,   pos)],
            [ up[0],       up[1],       up[2],      -np.dot(up,      pos)],
            [-forward[0], -forward[1], -forward[2],  np.dot(forward, pos)],
            [ 0.0,         0.0,         0.0,          1.0               ],
        ], dtype=np.float32)

        # projection
        # længere væk ska være mindre
        # f = 1 / tan(fov/2) er en skalering faktor der bestemmer hvor kraftigt perspektivet er, jo mindre fov jo stærkere perspektiv
        fov    = np.radians(45.0)
        aspect = width / height
        near   = 0.1
        far    = 10_000.0
        f      = 1.0 / np.tan(fov / 2.0)

        proj = np.zeros((4, 4), dtype=np.float32)
        proj[0, 0] =  f / aspect
        proj[1, 1] =  f
        proj[2, 2] =  (far + near) / (near - far)
        proj[2, 3] =  (2.0 * far * near) / (near - far)
        proj[3, 2] = -1.0

        # Model = identity, så MVP = Projection × View
        return (proj @ view).astype(np.float32)

    # nogle input handler som glfw kalder når der sker input events, disse opdaterer kameraets tilstand så det ser ud som om kameraet bev

    def mouse_button(self, button: int, action: int, x: float, y: float):
        """GLFW kaldet når en museknap trykkes eller slippes."""
        if button == glfw.MOUSE_BUTTON_LEFT:
            self._dragging     = (action == glfw.PRESS)
            self._last_x, self._last_y = x, y

    def mouse_move(self, x: float, y: float):
        """GLFW kaldet når musen bevæger sig.  Opdaterer kameraets azimuth værdi og elevation hvis venstre knap er nede"""
        
        if not self._dragging:
            return
        dx = x - self._last_x
        dy = y - self._last_y
        self._last_x, self._last_y = x, y

        self.azimuth   += dx * self._orbit_speed
        # Elevation er begrænset til (0, π) så kameraet aldrig kommer under jorden eller over hovedet på sig selv
        #  hvilket ville  gimbal lock og forvirre brugerens kontrol
        self.elevation  = np.clip(
            self.elevation + dy * self._orbit_speed,
            0.01, np.pi - 0.01
        )

    def scroll(self, yoffset: float):
        """GLFW kaldet når musen scroller.  Justerer zoom radius."""
        self.radius = max(20.0, self.radius - yoffset * self._zoom_speed)
