Limit Load
==========

An arcade cockpit flight game with story-driven campaigns.

Visit http://www.limitload.org for more information.


Installation
------------

To run the game under Windows, just unpack the archive and run
the limload.exe file. A 64-bit version of Windows is required.

To run under Linux, the game must be built from source.


Configuration
-------------

The default configuration files are located as ``config/<name>.ini.default``.
These files are not read, and the game has these defaults set internally.
To activate a configuration file, so that you can change some
configuration fields, copy it to ``config/<name>.ini`` on Windows,
or to ``~/.config/limload/<name>.ini`` on Linux.

The ``config.ini`` file contains sections of the general game configuration.
This includes language selection, and English can be set with
``language = en_US`` in the ``[misc]`` section (if not automatically
detected as system language).

The ``input.ini`` file contains command bindings for keyboard and
other input devices.


Instead of a manual
-------------------

Since the game manual is not yet written, a few words follow on
how to complete the only currently playable mission, skirmish "Incoming",
which deals with close maneuvering aerial combat.

The first start of the skirmish will take several minutes, to generate
various data (memory representation of models and textures, terrain,
aircraft tables, etc.) that were not included into the archive in order
to limit its size. Subsequent starts will be much quicker, since
the generated data will be cached on the disk.

A joystick is practically necessary to play the game, but even the simplest
one will do. The list of all commands, with joystick and keyboard bindings,
can be checked during the game, in the pause menu (with ``Esc`` key).
For close maneuvering combat, it is particularly important to remember
the commands for throttle, weapon selection (guns, missiles), acquiring
and tracking targets, and switching the view between target tracking and
instrument panel.

Before they reach the gun range, enemy aircraft attack the player with
missiles. This phase of combat happens during the initial closure, as well
as later if a larger separation occurs. When an enemy radar switches to
narrow beam mode, the master warning light in the cockpit starts to flash,
and an intermittent high-pitch tone is heard. When a missile launch is
detected, the light becomes continuously lit, and the audio switches
to continuous tone. From that moment on, the player has a few seconds
to perform the missile evasion maneuver. The missile approach can be seen
on the circular screen next to the HUD. There are two bars between
the center of the screen and the missile, where the outer bar denotes
four seconds to impact, and the inner bar two seconds. To evade the missile
with the highest probability, first it should be put approximately to left
or right flank, then a sharp break into the missile should be performed
when it passes the outer bar, and decoys should be launched once it passes
the inner bar. It helps additionally if this maneuver is executed in
a dive, instead of in the horizontal plane.

In the gun attack phase, enemy aircraft maneuver strictly in-plane, trying
to turn the nose towards the player and get him into the aim sight.
If the player employs the same tactic, the "scissors" regime is quickly
established, where in general the plane with smaller turn radius wins.
The turn radius depends on the aircraft characteristics, but also on
the current airspeed. The smaller the speed, the smaller the turn radius.
However, if the player slows down too much, that provides the chance for
the enemy to increase separation and start another scissors, for other
nearby enemies to reach and attack the player, and it decreases chances
for possible missile evasion. Therefore it is best to keep the airspeed
in the zone of best maneuvering speed (600 km/h indicated for MiG-29),
at full afterburner. During the scissors, when the enemy is driven
sufficiently in front, one may shortly use the airbrake to gain a few
seconds more for aiming the gun. A moving reticle will appear on the HUD
(in gun mode), and it should be put over the enemy aircraft before
pulling the trigger. The line that moves along the edge of the reticle
shows the distance to the target, where the full line denotes 1600 meters.
It is not likely that a maneuvering can be hit beyond 400-600 meters.
To keep the situational awareness during this kind of maneuvering, it is
important to visually track the target, but also to look back at the HUD
and the instrument panel from time to time, to check flight parameters.

Aside from the cannon, the player has several types of missiles at his
disposal. A missile is fired by switching the HUD to the appropriate
missile mode, locking the target, and keeping it for a short time within
the missile's homing head angle until the fire permission is obtained.
If the target is within the needed angle, an intermittent tone is heard,
and it switches to continuous tone when the missile can be fired. Best
suited for the close combat are the short-range agile missiles (R-60/Р-60,
R-73/Р-73). Although they can be fired at the enemy from any aspect,
the highest hit probability is achieved when they are fired in the target's
tail cone, and significantly below their maximum range. The missile range
depends on the altitude in which the combat takes place and the speed
of the target, and it is given by the scale on the left side of the HUD
(in missile mode). There are three bars on the scale, where the upper bar
denotes the maximum range if the target is no maneuvering, the middle bar
the maximum range in case the target is trying to escape, and the lower
bar the minimum range below which the missile will be unable to properly
establish tracking. The medium range missiles (R-27/Р-27) are not very
useful in close combat, because they take more time and space to deploy,
and they are easier to evade. Nevertheless, during the closure phase
the player can fire one of these missiles in order to force the enemy
into a defensive maneuver, instead of letting him comfortably enter
the attack phase.

If the player experiences a morale drop in the middle of the battle,
he can eject from the aircraft. Note, however, that ejecting from
a functioning aircraft is considered as desertion.


Building from source
--------------------

This archive also contains the full source code of the game, which can be
built under Windows and Linux. The build requirements are as follows:

* Windows:
  - Microsoft Visual C++ 10 (e.g. from the Windows SDK 7.1 package)
  - Python 2.7
  - Pygame 1.9
  - Panda3D 1.9 (with custom patches, must be built)
  - GNU Make, Bash, Gettext (e.g. from the MinGW package)

* Linux:
  - GCC (any reasonably new release should do)
  - Python 2.7
  - Pygame 1.9
  - Panda3D 1.9 (with custom patches, must be built)
  - GNU Make, Bash, Gettext

Before building Panda3D, see notes about that below.

The prebuilt elements from the archive should be cleaned up before
starting an own build of the game. To clean up, execute ``make clean``,
and manually delete directories ``panda3d`` and ``python``.

Then, an ``util/build_setup.<platform>`` file appropriate for the platform
should be copied to ``util/build_setup`` and the paths in it modified
to correspond to the system.

Finally, simply executing ``make`` in the game's root directory should
build everything needed, and produce the ``limload.exe`` (on Windows)
or ``limload`` (Linux) file that can be run. If ``make`` ends with errors
instead, these errors will likely be related to missing requirements,
improperly configured requirements, or improperly set paths.

The source code is composed mostly of Python files, with some C++ files.
When a Python file is modified, the game can be run afterward without
rebuilding. When a C++ file is modified, ``make`` must be run again.


Building Panda3D from source
----------------------------

Panda3D source code should be taken from its repository
``release/1.9.x`` branch.

Before building, apply all patches from the game's ``util`` directory.
This is done by executing in the Panda3D repository directory for
each patch file::

    patch -p1 <game_directory>/util/patch-panda3d/<name>.patch

Many of Panda3D's dependencies are not needed to run the game, and can
be disabled when building it. A possible build command line, on a 4-core
processor, is::

    python makepanda/makepanda.py --installer --optimize 3 --threads 4 \
        --lzma --use-python --use-direct --use-gl --no-gles --no-gles2 \
        --no-dx9 --no-tinydisplay --no-nvidiacg --no-egl --use-eigen \
        --use-openal --use-fmodex --use-vorbis --no-ffmpeg \
        --no-ode --no-physx --no-bullet \
        --use-pandaphysics --use-speedtree --use-zlib \
        --use-png --use-jpeg --use-tiff --use-squish --use-freetype \
        --no-maya6 --no-maya65 --no-maya7 --no-maya8 --no-maya85 \
        --no-maya2008 --no-maya2009 --no-maya2010 --no-maya2011 \
        --no-maya2012 --no-maya2013 --no-maya20135 --no-maya2014 \
        --no-maya2015 --no-max6 --no-max7 --no-max8 --no-max9 --no-max2009 \
        --no-max2010 --no-max2011 --no-max2012 --no-max2013 --no-max2014 \
        --no-fcollada --no-vrpn --no-openssl --no-fftw  --no-artoolkit \
        --no-opencv --no-directcam --no-vision \
        --no-mfc --no-gtk2 --no-wx --no-fltk --no-rocket --no-awesomium \
        --no-carbon --no-cocoa \
        --use-x11 --use-xf86dga --use-xrandr --use-xcursor \
        --use-pandatool --use-pview --use-deploytools --use-skel \
        --use-pandafx --use-pandaparticlesystem --use-contrib \
        --use-sse2 --no-neon --no-touchinput

On Windows, after the Panda3D package is installed, the file ``core.lib``
from the ``built_x64\panda3d\`` build directory should be copied to
``panda3d\`` directory of the installation. This is needed to enable
bulding the game's C++ modules.


Licensing
---------

The game source code is distributed under the GNU General Public License (GPL),
version 3. The full text of the license can be read at
http://www.gnu.org/copyleft/gpl.html .

All game resources that were purpose-made for the game are distributed
under CC-by-SA 4.0. The full text of the license can be read at
https://creativecommons.org/licenses/by-sa/4.0/legalcode .
However, many of the resources were taken from open repositories
on the Internet and adapted for the game, and for some of them
the licensing situation is unclear.

