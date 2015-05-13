# -*- coding: UTF-8 -*-

from pandac.PandaModules import *

from src.core import *
from src.blocks import *
#from __init__ import *


FONT_RUS = "fonts/Russo.ttf"

@itertask
def intro_gameintro(world, task):

    font = FONT_RUS; size1 = 18; size2 = 42

    #p1t = _(u"""
#He was tightening the turn,
#refusing to yield to the inertia.
#With the tensed structure shaking
#and the afterburner howling,
#he was approaching...
#""").strip()
    #p2t = _(u"""LIMIT LOAD""")

    #p1t = _(u"""
#Појачавао је заокрет,
#одбијајући да попусти инерцији.
#Уз подрхтавање напрегнуте конструкције
#и хук допунског сагоревања,
#ближило се...
#""").strip()
    #p2t = _(u"""ГРАНИЧНО ОПТЕРЕЋЕЊЕ""")

    p1t = _(u"""
The stick shook, the view faded into darkness.
There was no yielding to the inertia.
Engines howled with the afterburner,
pressing towards...
""").strip()
    p2t = _(u"""LIMIT LOAD""")

    #p1t = _(u"""
#Палица се тресла, поглед урањао у таму.
#Није било попуштања инерцији.
#Кроз хук допунског сагоревања,
#ближило се...
#""").strip()
    #p2t = _(u"""ГРАНИЧНО ОПТЕРЕЋЕЊЕ""")

    topnd = world.node2d.attachNewNode("gameintro")

    yield 1.0
    
    sound1 = Sound2D("audio/sounds/engine-mig29.ogg", volume=0.0, loop=True)
    sound1.play()
    sound1.set_volume(0.5, fadetime=24.0)

    yield 6.0

    sound2 = Sound2D("audio/sounds/flight-breathing.ogg", volume=0.0, loop=True)
    sound2.play()
    sound2.set_volume(1.0, fadetime=16.0)

    yield 2.0

    text = make_text(p1t, width=2.0, pos=Point3(0.0, 0.0, 0.0),
                     size=size1, font=font, color=rgba(255,0,0,1.0),
                     align="l", anchor="tl",
                     parent=topnd)
    bmin, bmax = text.getTightBounds()
    text.setPos(-(bmin + bmax) * 0.5)
    node_unfold_text(text, time=10.0, wpmspeed=None)

    yield 14.0

    text.removeNode()
    # sound1.set_volume(0.0, fadetime=12.0)
    # sound2.set_volume(0.0, fadetime=8.0)
    title = make_text(p2t, width=2.0, pos=Point3(0.0, 0.0, 0.0),
                      size=size2, font=font, color=rgba(255,0,0,1.0),
                      align="c", anchor="mc",
                      parent=topnd)

    yield 1.0

    repeat_num = 3
    repeat_wait = 0.5
    for i in range(repeat_num):
        sound3 = Sound2D("audio/voices/cockpit-voice-maximumg2-intro.ogg", volume=1.0)
        sound3.play()
        yield
        sound3.set_volume(0.0, fadetime=sound3.length())
        yield sound3.length()
        if i < repeat_num - 1:
            yield repeat_wait
    sound1.set_volume(0.0, fadetime=repeat_wait)
    sound2.set_volume(0.0, fadetime=repeat_wait)

    yield 4.0

    title.removeNode()

    topnd.removeNode()

    yield 1.0

def gameintro (gc):

    mission = Mission(gc)

    mission.add_zone("action", clat=0, clon=0, loopf=gi_action_loop)

    mission.switch_zone_pause = 1.0

    mission.switch_zone("action")

    return mission


def gi_action_loop (zc, mc, gc):

    world = World()
    #world.show_state_info(pos=Vec3(1.2, 0, 0.95), anchor="tr")

    subtask = base.taskMgr.add(intro_gameintro, "intro-gameintro", extraArgs=[world], appendTask=True)
    while subtask.isAlive():
        yield

    world.destroy()
    mc.mission.destroy()

# ========================================
# Background.

gameintro_skipmenu = True


# ========================================
# Stage dialogs.

