
util_dir := ../../util
build_env := $(shell grep 'build_env=' $(util_dir)/build_setup | sed 's/.*=//')
build_module := $(util_dir)/build_module.sh

ifeq ($(build_env), lingcc)
    mod_ext := so
else ifeq ($(build_env), winmsvc)
    mod_ext := pyd
else
    $(error Unknown build environment '$(build_env)'.)
endif
mod_suff := _c
mod_sfex := $(mod_suff).$(mod_ext)

all: \
    misc$(mod_sfex) \
    table$(mod_sfex) \
    fire$(mod_sfex) \
    trail$(mod_sfex) \
    terrain$(mod_sfex) \
    clouds$(mod_sfex) \

misc$(mod_sfex): misc.h misc.cpp typeinit.h
	$(build_module) misc$(mod_suff) misc.h MISC \
        misc.cpp

table$(mod_sfex): table.h table.cpp typeinit.h
	$(build_module) table$(mod_suff) table.h TABLE \
        table.cpp

fire$(mod_sfex): fire.h fire.cpp typeinit.h misc.h misc$(mod_sfex)
	$(build_module) fire$(mod_suff) fire.h FIRE \
        fire.cpp misc$(mod_sfex)

trail$(mod_sfex): trail.h trail.cpp typeinit.h misc.h misc$(mod_sfex)
	$(build_module) trail$(mod_suff) trail.h TRAIL \
        trail.cpp misc$(mod_sfex)

terrain$(mod_sfex): terrain.h terrain.cpp typeinit.h table.h table$(mod_sfex) \
                    misc.h misc$(mod_sfex)
	$(build_module) terrain$(mod_suff) terrain.h TERRAIN \
        terrain.cpp table$(mod_sfex) misc$(mod_sfex)

clouds$(mod_sfex): clouds.h clouds.cpp typeinit.h table.h table$(mod_sfex) \
                    misc.h misc$(mod_sfex)
	$(build_module) clouds$(mod_suff) clouds.h CLOUDS \
        clouds.cpp table$(mod_sfex) misc$(mod_sfex)

clean:
	rm -f *-igate.cpp *.in *-module.cpp
ifeq ($(build_env), lingcc)
	rm -f *.$(mod_ext) *.o
else ifeq ($(build_env), winmsvc)
	rm -f *.$(mod_ext) *.obj *.lib *.exp *.manifest
endif

