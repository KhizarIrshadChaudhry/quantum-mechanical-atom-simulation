"""
main.py står for følgende flow
1. opret en openGL window igennem glfw
glfw er library der håndterer vinduet, inputs og openGL kontekst, openGL er blot tegne biblioteket, der tegner på vinduet.
note: glfw er bro mellem openGL og OS så openGL kan bruges m. python
2. opret camera objekt fra klasse Camera fra camera.py
3. opret electron objekt fra klasse Electron fra electron.py
4. opsæt glfw input callbacks og opdatere elekctronens quantumnumber og antal (som dermed vil sample nye positioner og smide dem på GPU engine)
5. kører loopet igennem hvor hvert frame tegnes igennem engine.draw(camera) og input events håndteres igennem glfw.poll_events()
altså  poll input -> tegn frames -> gentage indtil vindue lukkes altså 
main.py — Entry point for the Quantum Orbital Visualizer not glfw.window_should_close(engine.window)

Følgende controls benyttes

W & S: kvantetal n (længde og energi) - principal
E & D: kvantetal l (orbital form) - azimuthal
R & F: kvantetal m (orienteation) - magnetic
Mus drag på slider: ændre antal af elektroner (release for at sample nye positioner)
Mus drag andetsteds: orbit camera
Mus scroll: zoom in / out
"""

import glfw
from engine import Engine
from camera import Camera
from electron import Electron


def main():
    # intialisere engine & camera
    engine = Engine(width=900, height=700, title="Kvantemekanisk Simulering af Atomet")
    camera = Camera()


    # Create the electron using the slider's initial particle count as the source
    # of truth — so the HUD and Electron always agree.

    # Elektronen starter i 1s orbitalet (n=1, l=0, m=0) med det antal partikler, der er sliderens init value
    electron = Electron(n=1, l=0, m=0, n_particles=engine.particle_count)
    # init positioner og farver oploades til gpu gennem engine, hud opdateres 
    engine.upload_particles(electron.positions, electron.colors)
    engine.update_hud(electron.n, electron.l, electron.m) #HUD for kvantetal (øverst højere)
    engine.update_particle_hud(electron.n_particles) #HUD for antal partikler (nederest venstre)


    slider_dragging = True #boolean slider dragger starter med False, og sættes ti True når slideren klikkes påååååååååå

    # ALLE INPUT CALLBACKS FUNKTIONER TIL GLFW! ----------------------------------------------------------------------
    def key_cb(window, key, scancode, action, mods):
        if action not in (glfw.PRESS, glfw.REPEAT):
            return # ignorer key releases for at undgå dobbelt triggering orale

        n, l, m = electron.n, electron.l, electron.m
        changed = True
        if   key == glfw.KEY_W: n += 1
        elif key == glfw.KEY_S: n -= 1
        elif key == glfw.KEY_E: l += 1
        elif key == glfw.KEY_D: l -= 1
        elif key == glfw.KEY_R: m += 1
        elif key == glfw.KEY_F: m -= 1
        else:
            changed = False

        if changed: #opdatere lortet ved skift af kvantetal
            electron.set_kvantumtal(n, l, m)
            engine.upload_particles(electron.positions, electron.colors)
            engine.update_hud(electron.n, electron.l, electron.m)

    def mouse_btn_cb(window, button, action, mods):
        nonlocal slider_dragging #permission til at ændre parent variabel slider_dragging defineret i main() lol
        x, y = glfw.get_cursor_pos(window)

        if button == glfw.MOUSE_BUTTON_LEFT:
            if action == glfw.PRESS:
                if engine.slider_hit_test(x, y):
                    # slider drag sættes til 1, og derfor opdareteres sliders positieren samt partikel hud hehe
                    slider_dragging = True
                    engine.slider_set_from_x(x)
                    engine.update_particle_hud(engine.particle_count)
                    return
            elif action == glfw.RELEASE and slider_dragging:
                # omvendte sker når slider slippes og elektronen beregnes og opdateres med det nye antal partiikler
                slider_dragging = False
                electron.n_particles = engine.particle_count
                electron.sample()
                engine.upload_particles(electron.positions, electron.colors)
                return

        camera.mouse_button(button, action, x, y) #hvis ik d slider så d kamera kontrol til det her jeg et andet func mouse_button fra camera.py

    def cursor_cb(window, x, y):
        if slider_dragging:
            # ligesom den forrige func men nu opdatere sliderens position og partikel hud mens der drraagges 
            engine.slider_set_from_x(x)
            engine.update_particle_hud(engine.particle_count)
        else:
            camera.mouse_move(x, y)

    def scroll_cb(window, xoff, yoff):
        camera.scroll(yoff) #til kamera selfølgelig 

    #Opsæt GLFW callbacks
    glfw.set_key_callback(engine.window,           key_cb)
    glfw.set_mouse_button_callback(engine.window,  mouse_btn_cb)
    glfw.set_cursor_pos_callback(engine.window,    cursor_cb)
    glfw.set_scroll_callback(engine.window,        scroll_cb)


    # det her er hele fuckkiiiingg render loopet brormandd
    while not glfw.window_should_close(engine.window):
        glfw.poll_events() # glfw tjekker om der har været events, hvis ja så kalder den relevente callbacks som defienret ovenover
        engine.draw(camera) 
        #this nigga kørere gpuet med min draw func, som i øvrigt er inspiret af P5.js draw function anders roland introduceret i 2g haha

    #noget ligegyldigt shit jeg har fra en yt totorial til at clean lortet når programmet lukkes, men gør ik så meget da OS alligvel håndtere det
    #engine.cleanup()
    #glfw.terminate()


if __name__ == "__main__":
    main()
