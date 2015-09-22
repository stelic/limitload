Гранично оптерећење — градња из извора
======================================

Све бинарне архиве игре такође садрже потпун изворни код, који се може
изградити. Најновија верзија извора може да се добави са Гитхаба, помоћу::

    git clone https://github.com/stelic/limitload.git

Захтеви градње су следећи:

* виндоуз:
  - Microsoft Visual C++ 10 (нпр. из пакета Windows SDK 7.1)
  - Python 2.7
  - Pygame 1.9
  - Panda3D 1.9 (са посебним закрпама, мора да се изгради)
  - GNU Make, Bash, Gettext (нпр. из пакета MinGW)

* линукс:
  - GCC (послужиће било које разложно ново издање)
  - Python 2.7
  - Pygame 1.9
  - Panda3D 1.9 (са посебним закрпама, мора да се изгради)
  - GNU Make, Bash, Gettext

Пре градње Панде 3Д, погледајте белешке о томе испод.

Ако се користе извори из бинарне архиве, треба почистити предизграђене
елементе у архиви пре отпочињања сопствене градње игре. За чишћење треба
извршити ``make clean``, и ручно избрисати директоријуме
``panda3d`` и ``python`` на виндоузу, или ``binroot`` на линуксу.

Градња се конфигурише тако што се један од фајлова
``util/build_setup.<platform>``, који одговара платформи, копира у
``util/build_setup``, и путање у њему задају тако да одговарају систему.
Такође, на неким системима се извршни фајл интерпретатора питона 2 зове
``python`` а на другим ``python2``, и то се може задати у овом фајлу.

Коначно, једноставним извршењем ``make`` требало би да се изгради све
што је потребно, укључујући и извршни фајл ``limload.exe`` (под виндоузом)
или ``limload`` (линукс). Ако се ``make`` уместо тога оконча уз грешке,
то је вероватно услед недостајућих захтева, лоше подешених захтева,
или лоше задатих путања.

Изворни код се састоји углавном од питонских фајлова, уз нешто Ц++ фајлова.
Када се измени неки питонски фајл, игра потом може да се покрене без
поновне градње. Ако се измени Ц++ фајл, мора поново да се изврши ``make``.


Градња Панде 3Д из извора
-------------------------

Изворни код Панде 3Д треба узети из њене ризнице, грана ``release/1.9.x``.

Пре градње, треба применити све закрпе из директоријума ``util`` игре.
Ово се ради тако што се у директоријуму ризнице Панде 3Д изврши,
за сваки фајл закрпе::

    patch -p1 <direktorijum_igre>/util/patch-panda3d/<name>.patch

Многе од зависности Панде 3Д нису неопходне за извршавање игре,
те се могу изоставити при градњи. Ево једне могуће командне линије
за градњу, на 4-језгарном процесору::

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

Под виндоузом, пошто се изграђени пакет Панде 3Д инсталира, треба копирати
фајл ``core.lib`` из директоријума градње ``built_x64\panda3d\`` у
директоријум инсталације ``panda3d\``. Ово је потребно да би се омогућила
градња Ц++ модула игре.


