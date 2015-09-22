Limit Load -- Building from Source
==================================

All game binary archives also contain the full source, that can be built.
The latest version of the sources can be fetched from Github, using::

    git clone https://github.com/stelic/limitload.git

The build requirements are as follows:

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

If the sources from a binary archive are used, the prebuilt elements from
the archive should be cleaned up before starting an own build of the game.
To clean up, execute ``make clean``, and manually delete directories
``panda3d`` and ``python`` on Windows, or ``binroot`` on Linux.

The build is configured by copying one of ``util/build_setup.<platform>``
files, as appropriate for the platform, to ``util/build_setup`` and modifying
the paths in it to match the system. Also, on some systems the name of
Python 2 interpreter executable is ``python`` and on others ``python2``,
and that can be set in this file.

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


