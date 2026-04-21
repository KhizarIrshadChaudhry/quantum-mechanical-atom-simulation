"""
engine.py står for Engine klasse, som håndtere openGL vindue, shaders og alt gpu arbejde
det inkludere også HUD

elektron skyrene er 3d på flad mens HUD er 2D på overfladen vha. PIL altså pillow

HUD inkl. 

  1. kvantetal vha. PIL texture label
  2. Antal partikler som label count label 
  3. Antal elektroner muligheder sldier

noter:
VBO vertex buffer object benyttes til at gemme vertex data på GPUen fra CPUen til hurtigere brug, programmet indeholder 1 vertex pr elektron (et punkt)
to VBO benyttes self._vbo_pos og self._vbo_color, der hver især gemme info om en liste af verticies (antal verticees = antal elektroner)
f.eks. ligner self._vbo_pos = [x0,y0,z0, x1,y1,z1, x2,y2,z2, ...] hvor 0, 1, 2 er vertex nummer (elektron nummer)

VAO vertex array object fortæller hvordan VBO skal læses og offsett, stride (hvor mange floats er en vertex data), float type og forskellige attributes af verteicies
VAO vil feks. ta VBOen self._vbo_pos = [x0,y0,z0, x1,y1,z1, x2,y2,z2, ...] og oprrette attribute location 0 med 3 floats pr vertex
og de tre vertex attributter vil så være aPos i vertex shaderen med vertex 0 = (x0,y0,z0), vertex 1 = (x1,y1,z1) osv.
det samme gøres for farverne i self._vbo_color der bliver attribute location 1 i shaderen, så aColor i shaderen vil have farve info for hver elektron vertex, 
altså aColor0 = (r0,g0,b0,a0), aColor1 = (r1,g1,b1,a1) osv.

https://medium.com/@deyan.sirakov2006/the-definitive-guide-to-opengl-vbos-vaos-and-ebos-6193ab13ccc5


Shaders er program skrevet i GLSL der kører på GPUen, og er ansvarlig for at transformere vertex data til pixels på skærmen basically
den kører vertex shader først for hver vertex (elektron) og transformere dens position fra 3D world space til clip space vha. MVP matrixen, og bestemme dens størrelse på skærmen vha. gl_PointSize
fragment shaderen kører for hver pixel der skal tegnes og bestemmer dens farve, i dette tilfælde laver den en cirkulær maske for at gøre punkterne runde og bruger farve info fra vertex shaderen (interpoleret over punktet) til at bestemme pixel farven og alpha (gennemsigtighed) for at skabe en glød effekt
shader er instruktioner til gpu om hvordan fk den ska tegne vertex attributer osv på skærmen babyy
ooo baby u should go and love yourself
and if u think that u need someone 
when u tokd me that u hated my friends
ar3q and i didnt wanna write a song
cuz i didnt wanna 
https://medium.com/@yvanscher/an-introduction-to-shaders-in-opengl-c19a1376eda1
https://pyopengl.sourceforge.net/context/tutorials/shader_1.html
https://mcfletch.github.io/pyopengl/documentation/manual/index.html

har skrevet om mvp i camera.py

"""

import ctypes #open gl er lavet i c så ctypes ska bruges for kommunikation mellem python og c

import glfw
import numpy as np
from OpenGL.GL import *
from PIL import Image, ImageDraw, ImageFont #til HUD tekst rendering


# shaders til elektron vertex med position og farve, og en fragment shader der laver en glød effekt ved at justere alpha baseret på afstand fra punktets center lol

#for hvert vertex ta shaderen dens position og farve og beregner pos med MVP og sender farven videre til fragment shader lol
VERT_SHADER = """
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec4 aColor;
uniform mat4 uMVP;
out vec4 vColor;
void main() {
    gl_Position  = uMVP * vec4(aPos, 1.0);
    gl_PointSize = 2.5;
    vColor = aColor;
}
"""


#fragment shader ta så output fra vert shader laver cirkluær punkter med discard og justere alpha for at lave glød effekt i kanten den outputer den endelige farve for hver pixel i punktet
FRAG_SHADER = """
#version 330 core
in  vec4 vColor;
out vec4 FragColor;
void main() {
    vec2  coord = gl_PointCoord - vec2(0.5);
    float dist  = length(coord);
    if (dist > 0.5) discard;
    float alpha = (1.0 - smoothstep(0.2, 0.5, dist)) * vColor.a;
    FragColor   = vec4(vColor.rgb, alpha);
}
"""
#bruger vec 4 til farver fordi (r,g,b,a) og vec3 til pos fordi (x,y,z) men vec4 med w=1 for punkt når MVP funktion bruges

# shader funktioner til HUD 2d til n, l m labels og slideren, de er simple og bruger ortho matrix for at tegne i pixel koordinater direkte på skærmen, og fragment shaderen er enten solid farve til slideren eller tekstur sampling til labels
# ortho matrix er en projektion der konvertere pixel koordinater til clip space koordinater direkte uden perspektiv, så vi kan tegne HUD elementer i 2D på skærmen uden at de påvirkes af kameraets position eller orientering
HUD_VERT_SHADER = """
#version 330 core
layout(location = 0) in vec2 aPos;
layout(location = 1) in vec2 aTexCoord;
uniform mat4 uOrtho;
out vec2 vTexCoord;
void main() {
    gl_Position = uOrtho * vec4(aPos, 0.0, 1.0);
    vTexCoord   = aTexCoord;
}
"""

HUD_FRAG_SHADER = """
#version 330 core
in  vec2      vTexCoord;
uniform sampler2D uTex;
out vec4 FragColor;
void main() {
    FragColor = texture(uTex, vTexCoord);
}
"""


#  Solid color 2D shader til slideren

SOLID_VERT_SHADER = """
#version 330 core
layout(location = 0) in vec2 aPos;
uniform mat4 uOrtho;
void main() {
    gl_Position = uOrtho * vec4(aPos, 0.0, 1.0);
}
"""

SOLID_FRAG_SHADER = """
#version 330 core
uniform vec4 uColor;
out vec4 FragColor;
void main() {
    FragColor = uColor;
}
"""


# konstanter til slider layout (x,y)= (0,0) er øverste venstre hjørne af vinduet
_SL_X    = 12      # x-start for slider track
_SL_W    = 256     # slider track width
_SL_CY   = 30     # y-center for slider track
_TRACK_H = 8      # slider track height
_KNOB_R  = 11     # knob radius
_MIN_P   = 10_000 #min værdien af antal elektroner
_MAX_P   = 1_000_000 #max værdien af antal elektroner


class Engine:
    def __init__(self, width: int, height: int, title: str):
        self.width       = width
        self.height      = height
        self.n_particles = 0

        # hvor knob ska placeres i procent
        self._slider_fraction = 0.5 # DEN RIGTIGE INIT VALUE PERCENTAGE

        # GLFW window 
        if not glfw.init():
            raise RuntimeError("GLFW init failed")

        #indstillinger fra et forum
        # https://discourse.glfw.org/t/creating-a-cross-platform-compatible-window-that-is-maximized-upon-startup/2736
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE) 
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)

        self.window = glfw.create_window(width, height, title, None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError("Failed creating GLFW window")

        glfw.make_context_current(self.window)

        # OpenGL global states fra docs
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)   # Additiv blending for glød effekt
        glEnable(GL_PROGRAM_POINT_SIZE)
        glClearColor(0.0, 0.0, 0.0, 1.0)

        # opsæt 3d shaders og mvp uniform
        self.shader  = self._build_program(VERT_SHADER, FRAG_SHADER)
        self.mvp_loc = glGetUniformLocation(self.shader, "uMVP")

        # indlæs 2x vbo samt vao til elektron punkter
        self.vao     = glGenVertexArrays(1)
        self.vbo_pos = glGenBuffers(1)
        self.vbo_col = glGenBuffers(1)

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_pos)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None) # positioner er 3 floats (x,y,z) per vertex, ingen stride eller offset da data er pakket tæt i vbo
        glEnableVertexAttribArray(0) # aktiver attribute location 0 i shaderen for positioner

        # same for farverne
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_col)
        glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, 0, None) # farver er 4 floats (r,g,b,a) per vertex, ingen stride eller offset
        glEnableVertexAttribArray(1) # aktiver attribute location 1 i shaderen for farver
        glBindVertexArray(0) # unbind vao for at undgå utilsigtede ændringer senere

        # til HUD overlay shaders har jeg lavet interne methods 
        self._init_hud()
        self._init_particle_label()
        self._init_slider_ui()



    # Shader helper metoder til at kompile og linke shaders, og håndtere fejl

    def _compile_shader(self, source: str, shader_type) -> int:
        handle = glCreateShader(shader_type)
        glShaderSource(handle, source)
        glCompileShader(handle)
        if not glGetShaderiv(handle, GL_COMPILE_STATUS):
            raise RuntimeError(f"Shader compile error:\n{glGetShaderInfoLog(handle).decode()}")
        return handle

    def _build_program(self, vert_src: str, frag_src: str) -> int:
        vert = self._compile_shader(vert_src, GL_VERTEX_SHADER)
        frag = self._compile_shader(frag_src, GL_FRAGMENT_SHADER)
        prog = glCreateProgram()
        glAttachShader(prog, vert)
        glAttachShader(prog, frag)
        glLinkProgram(prog)
        if not glGetProgramiv(prog, GL_LINK_STATUS):
            raise RuntimeError(f"Shader link error:\n{glGetProgramInfoLog(prog).decode()}")
        glDeleteShader(vert)
        glDeleteShader(frag)
        return prog

    # Particle upload + draw til VBO og shader, kaldt fra main loopet hver frame efter evt. opdatering af elektron data

    def upload_particles(self, positions: np.ndarray, colors: np.ndarray):
        self.n_particles = len(positions)
        pos_flat = positions.astype(np.float32).ravel()
        col_flat = colors.astype(np.float32).ravel()
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_pos)
        glBufferData(GL_ARRAY_BUFFER, pos_flat.nbytes, pos_flat, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_col)
        glBufferData(GL_ARRAY_BUFFER, col_flat.nbytes, col_flat, GL_DYNAMIC_DRAW)

    def draw(self, camera):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(self.shader)
        mvp = camera.mvp_matrix(self.width, self.height)
        glUniformMatrix4fv(self.mvp_loc, 1, GL_FALSE, mvp)
        glBindVertexArray(self.vao)
        glDrawArrays(GL_POINTS, 0, self.n_particles)
        glBindVertexArray(0)

        self._draw_all_hud()
        glfw.swap_buffers(self.window)

    # Shaders helper metoder til HUD oprettelse, tekst rendering og ortho matrix

    def _ortho_matrix(self, w: int, h: int) -> np.ndarray:
        """
        definere orthographic mmatric  for screen pixel koordinater, hvor (0,0) er øverste venstre hjørne og (w,h) er nederste højre hjørne.

        Convention: numpy a[i,j] is read by OpenGL as column j, row i
        numper a[i,j] læses af openGL som kolonne j, række i, så a[0,3]
        matricen ifølge chatgpt blir
            [2/w,  0,   0,  -1]
            [0,   2/h,  0,  -1]    = clip_x = 2x/w - 1,  clip_y = 2y/h - 1
            [0,    0,  -1,   0]
            [0,    0,   0,   1]

        gemmer og retunere numpy array i float 32 for at bruge i shaders uden konverting
        """
        return np.array([
            [2.0/w,  0.0,    0.0,  0.0],
            [0.0,    2.0/h,  0.0,  0.0],
            [0.0,    0.0,   -1.0,  0.0],
            [-1.0,  -1.0,    0.0,  1.0],
        ], dtype=np.float32)

    #steps til HUD oprreteelse
    #1. func til at måle teksten i pixels og oprette sort billed og tegner hvidt skrift, og sende færdig som texture til gpu
    #2. func til at oprette VAO og VBO til 

    def _make_text_texture(self, lines: list[str], font) -> tuple[int, int, int]:
        """
        fk endenlig shit done
        i stedet for at lave tekst vertices laver jeg texture der indeholder billeder i GPU
        i texture sætter jeg billeder af text til billede med PIL med
        https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html#ImageDraw.ImageDraw.textbbox
        https://stackoverflow.com/questions/42703816
        https://wikis.khronos.org/opengl/Texture

        """
        pad     = 12
        spacing = 6
        probe   = Image.new("RGBA", (1, 1))
        pd      = ImageDraw.Draw(probe)
        boxes   = [pd.textbbox((0, 0), ln, font=font) for ln in lines]
        lw      = max(b[2] - b[0] for b in boxes)
        lh      = max(b[3] - b[1] for b in boxes)
        img_w   = lw + 2 * pad
        img_h   = len(lines) * lh + (len(lines) - 1) * spacing + 2 * pad

        img  = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 180)) 
        draw = ImageDraw.Draw(img)
        for i, line in enumerate(lines):
            draw.text((pad, pad + i * (lh + spacing)), line, font=font,
                      fill=(255, 255, 255, 255))
        

        #upload til gpu som texture og returnere texture id og dimensioner til senere brug i shaderen
        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img_w, img_h, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, img.tobytes("raw", "RGBA"))
        glBindTexture(GL_TEXTURE_2D, 0)
        return tex, img_w, img_h

    def _alloc_tex_quad_vao(self) -> tuple[int, int]:
        """til allocering af 6 verticies for en quad, som ramme for billidet/texture sendt til gpu"""
        vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        glBindVertexArray(vao)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, 6 * 4 * 4, None, GL_DYNAMIC_DRAW)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * 4, None)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * 4,
                              ctypes.c_void_p(2 * 4))
        glEnableVertexAttribArray(1)
        glBindVertexArray(0)
        return vao, vbo

    def _upload_tex_quad(self, vbo: int,
                         x0: float, y0: float,
                         x1: float, y1: float):
        """
        lortetet her oploader en quad (to trekanter som er 6 verticies) 
        denne quad benyttes til at sætte texture/billed fra tidligere func 
        til at tegne tekstur på, og positionere den i pixel koordinater baseret på input (x0,y0) for øverste venstre hjørne og (x1,y1) for nederste højre hjørne
        """
        verts = np.array([
            x0, y0,  0.0, 1.0,
            x1, y0,  1.0, 1.0,
            x1, y1,  1.0, 0.0,
            x0, y0,  0.0, 1.0,
            x1, y1,  1.0, 0.0,
            x0, y1,  0.0, 0.0,
        ], dtype=np.float32)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, verts.nbytes, verts)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    # HUD til kvantetal højere top 

    def _init_hud(self):
        self._hud_shader  = self._build_program(HUD_VERT_SHADER, HUD_FRAG_SHADER)
        self._hud_ortho   = glGetUniformLocation(self._hud_shader, "uOrtho")
        self._hud_tex_loc = glGetUniformLocation(self._hud_shader, "uTex")
        self._hud_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self._hud_texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)
        self._hud_vao, self._hud_vbo = self._alloc_tex_quad_vao()
        self._hud_tex_w = 1
        self._hud_tex_h = 1

    def update_hud(self, n: int, l: int, m: int):
        # til opdatering af kvantetal label, samme process som particle count label
        font   = ImageFont.load_default(22)  
        lines  = [f"n = {n}", f"l = {l}", f"m = {m}"]
        pad    = 12
        sp     = 6
        probe  = Image.new("RGBA", (1, 1))
        pd     = ImageDraw.Draw(probe)
        boxes  = [pd.textbbox((0, 0), ln, font=font) for ln in lines]
        lw     = max(b[2] - b[0] for b in boxes)
        lh     = max(b[3] - b[1] for b in boxes)
        img_w  = lw + 2 * pad
        img_h  = len(lines) * lh + (len(lines) - 1) * sp + 2 * pad

        img  = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 180))
        draw = ImageDraw.Draw(img)
        for i, line in enumerate(lines):
            draw.text((pad, pad + i * (lh + sp)), line, font=font,
                      fill=(255, 255, 255, 255))

        glBindTexture(GL_TEXTURE_2D, self._hud_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img_w, img_h, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, img.tobytes("raw", "RGBA"))
        glBindTexture(GL_TEXTURE_2D, 0)
        self._hud_tex_w = img_w
        self._hud_tex_h = img_h

        margin = 12
        x1 = self.width  - margin
        x0 = x1 - img_w
        y1 = self.height - margin
        y0 = y1 - img_h
        self._upload_tex_quad(self._hud_vbo, x0, y0, x1, y1)

    # Particle count label nederest venstr

    def _init_particle_label(self):
        self._plabel_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self._plabel_texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)
        self._plabel_vao, self._plabel_vbo = self._alloc_tex_quad_vao()

    def update_particle_hud(self, n: int):
       #opdatere partikel count label, samme process som kvantetal label 
        font  = ImageFont.load_default(22) #str
        text  = f"Elektroner: {n:,}"
        pad   = 10
        probe = Image.new("RGBA", (1, 1))
        pd    = ImageDraw.Draw(probe)
        bbox  = pd.textbbox((0, 0), text, font=font)
        tw    = bbox[2] - bbox[0]
        th    = bbox[3] - bbox[1]
        img_w = tw + 2 * pad
        img_h = th + 2 * pad

        img  = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 180))
        draw = ImageDraw.Draw(img)
        draw.text((pad, pad), text, font=font, fill=(255, 255, 255, 255))

        glBindTexture(GL_TEXTURE_2D, self._plabel_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img_w, img_h, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, img.tobytes("raw", "RGBA"))
        glBindTexture(GL_TEXTURE_2D, 0)

        # Ska side lige ovenpå lider (slider top = _SL_CY + _KNOB_R)
        y_bottom = _SL_CY + _KNOB_R + 8
        self._upload_tex_quad(self._plabel_vbo,
                              _SL_X, y_bottom,
                              _SL_X + img_w, y_bottom + img_h)

    # Slider nederst venstre
    def _init_slider_ui(self):
        """opretter shader og vbo til slideren og bygger tre quads til track, fill og knob baseret på initial slider fraction"""
        self._solid_shader  = self._build_program(SOLID_VERT_SHADER, SOLID_FRAG_SHADER)
        self._solid_ortho_l = glGetUniformLocation(self._solid_shader, "uOrtho")
        self._solid_color_l = glGetUniformLocation(self._solid_shader, "uColor")

        # VBO: 3 quads * 6 vertices * 2 floats = 36 floats
        # trackbackground, fill og knob er de tre quads til slideren
        self._slider_vao = glGenVertexArrays(1)
        self._slider_vbo = glGenBuffers(1)
        glBindVertexArray(self._slider_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self._slider_vbo)
        glBufferData(GL_ARRAY_BUFFER, 36 * 4, None, GL_DYNAMIC_DRAW)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(0)
        glBindVertexArray(0)

        self._update_slider_geometry()

    def _update_slider_geometry(self):
        """opdatere tre quads (track, fill, knob) i slider VBO baseret på den nuværende slider fraction så de tegnes korrekt i HUD"""
        frac = self._slider_fraction
        hy   = _TRACK_H // 2

        # background af slider
        tx0, ty0, tx1, ty1 = _SL_X, _SL_CY - hy, _SL_X + _SL_W, _SL_CY + hy
        # Filled del af slider
        fx1 = _SL_X + frac * _SL_W
        # knob centreret på den nuværende slider fraction
        kx  = _SL_X + frac * _SL_W
        kx0, ky0 = kx - _KNOB_R, _SL_CY - _KNOB_R
        kx1, ky1 = kx + _KNOB_R, _SL_CY + _KNOB_R

        def quad(x0, y0, x1, y1):
            return [x0, y0,  x1, y0,  x1, y1,
                    x0, y0,  x1, y1,  x0, y1]

        verts = np.array(
            quad(tx0, ty0, tx1, ty1) +   # [0:12]  track bg
            quad(tx0, ty0, fx1, ty1) +   # [12:24] fill
            quad(kx0, ky0, kx1, ky1),    # [24:36] knob
            dtype=np.float32,
        )
        glBindBuffer(GL_ARRAY_BUFFER, self._slider_vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, verts.nbytes, verts)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    @property #for at tilgå den som attribut i stedet for metode så particle_count istedet for particle_count() for at få den nuværende slider værdi som antal partikler
    def particle_count(self) -> int:
        """Returner nuværende slider value mappet til [_MIN_P, _MAX_P], afrundet til nærmeste 10.000 for pænere tal i HUD"""
        n = self._slider_fraction * (_MAX_P - _MIN_P) + _MIN_P
        return int(round(n / 10_000) * 10_000)

    def slider_hit_test(self, glfw_x: float, glfw_y: float) -> bool:
        """True hvis GLFW cursor position (glfw_x, glfw_y) er inden for sliderens område, inklusive knob radius for lettere klik"""
        gl_y = self.height - glfw_y          # flip y: GLFW top left er  OpenGL bottom left
        return (
            _SL_X - _KNOB_R <= glfw_x <= _SL_X + _SL_W + _KNOB_R and
            _SL_CY - _KNOB_R <= gl_y  <= _SL_CY + _KNOB_R
        )

    def slider_set_from_x(self, glfw_x: float):
        """opdatere slider fraction baseret på den nuværende GLFW cursor x position, klippet til [0.0, 1.0] og opdatere slider geometri for at reflektere ændringen i HUD"""
        frac = (glfw_x - _SL_X) / _SL_W
        self._slider_fraction = float(np.clip(frac, 0.0, 1.0))
        self._update_slider_geometry()

    # kombineret HUD draw func der blir kaldt i draw()

    def _draw_all_hud(self):
        """
        Tegn alle 2D overlay elementer ovenpå 3d electron skyen.
        """
        glDisable(GL_DEPTH_TEST) #depth ska ikke bruges til 2d
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        ortho = self._ortho_matrix(self.width, self.height)

        #  Texture baseret elementer (billeder) kvantetal og antal partikel label
        glUseProgram(self._hud_shader)
        glUniformMatrix4fv(self._hud_ortho, 1, GL_FALSE, ortho)
        glUniform1i(self._hud_tex_loc, 0)
        glActiveTexture(GL_TEXTURE0)

        # Kvantetal overlay (øverst højre)
        glBindTexture(GL_TEXTURE_2D, self._hud_texture)
        glBindVertexArray(self._hud_vao)
        glDrawArrays(GL_TRIANGLES, 0, 6)

        # Elektron count overlay (nederst venstre)
        glBindTexture(GL_TEXTURE_2D, self._plabel_texture)
        glBindVertexArray(self._plabel_vao)
        glDrawArrays(GL_TRIANGLES, 0, 6)

        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)

        # linje til slideren, solid farve elementer til track, fill og knob udgør 3 quads i slider VBOen, og farven set i shaderen for hver del tegner dem korrekt i HUD
        glUseProgram(self._solid_shader)
        glUniformMatrix4fv(self._solid_ortho_l, 1, GL_FALSE, ortho)
        glBindVertexArray(self._slider_vao)

        glUniform4f(self._solid_color_l, 0.15, 0.15, 0.15, 0.90)  # den mørke unfilled track
        glDrawArrays(GL_TRIANGLES, 0, 6)

        glUniform4f(self._solid_color_l, 0.27, 0.51, 0.90, 1.00)  # blue filled track
        glDrawArrays(GL_TRIANGLES, 6, 6)

        glUniform4f(self._solid_color_l, 0.90, 0.90, 0.90, 1.00)  #  knob
        glDrawArrays(GL_TRIANGLES, 12, 6)

        glBindVertexArray(0)

        # tilbage til 3d baby
        glEnable(GL_DEPTH_TEST)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)


    
    def cleanup(self):
        """funktion til at rydde op i GPU ressourcer så min fkn laptop ikke eksploderer efter at have kørt programmet i et stykke tid
            sletter shaders, vbos, vaos og textures"""
        glDeleteVertexArrays(1, [self.vao])
        glDeleteBuffers(1, [self.vbo_pos])
        glDeleteBuffers(1, [self.vbo_col])
        glDeleteProgram(self.shader)

        glDeleteVertexArrays(1, [self._hud_vao])
        glDeleteBuffers(1, [self._hud_vbo])
        glDeleteTextures(1, [self._hud_texture])

        glDeleteVertexArrays(1, [self._plabel_vao])
        glDeleteBuffers(1, [self._plabel_vbo])
        glDeleteTextures(1, [self._plabel_texture])

        glDeleteVertexArrays(1, [self._slider_vao])
        glDeleteBuffers(1, [self._slider_vbo])
        glDeleteProgram(self._hud_shader)
        glDeleteProgram(self._solid_shader)
