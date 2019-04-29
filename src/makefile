
util_dir := ../util
build_env := $(shell grep 'build_env=' $(util_dir)/build_setup | sed 's/.*=//')
python_cmd := $(shell grep 'python_cmd=' $(util_dir)/build_setup | sed 's/.*=//')
ifeq ($(build_env), winmsvc)
    winsdk_root_dir := $(shell grep 'winsdk_root_dir=' $(util_dir)/build_setup | sed 's/.*=//')
    winsdk_version := $(shell grep 'winsdk_version=' $(util_dir)/build_setup | sed 's/.*=//')
    rc_cmd := $(winsdk_root_dir)/bin/$(winsdk_version)/x64/rc.exe
    msvc_root_dir := $(shell grep 'msvc_root_dir=' $(util_dir)/build_setup | sed 's/.*=//')
    msvc_version := $(shell grep 'msvc_version=' $(util_dir)/build_setup | sed 's/.*=//')
    cvtres_cmd := $(msvc_root_dir)/$(msvc_version)/bin/Hostx64/x64/cvtres.exe
    cl_cmd := $(msvc_root_dir)/$(msvc_version)/bin/Hostx64/x64/cl.exe
endif

binname := limload

pyc_files := $(shell find -name '*.py' | sort | sed 's:\.py$$:\.pyc:')

all: \
    subdir-core \
    ../$(binname) \
    bconf.pyc \
    $(pyc_files) \

../$(binname): $(binname).cpp $(binname).ico
ifeq ($(build_env), lingcc)
	g++ -D LINGCC -D PYTHON_CMD='"$(python_cmd)"' $(binname).cpp
	mv a.out ../$(binname)
else ifeq ($(build_env), winmsvc)
	echo '101 ICON "$(binname).ico"' > resource.rc
	$(rc_cmd) -fo resource.res resource.rc
	$(cvtres_cmd) -machine:x64 -out:resource.obj resource.res
	$(cl_cmd) -D WINMSVC -D PYTHON_CMD='"$(python_cmd)"' \
        -I $(msvc_root_dir)/$(msvc_version)/include \
        -I $(winsdk_root_dir)/Include/$(winsdk_version)/shared \
        -I $(winsdk_root_dir)/Include/$(winsdk_version)/ucrt \
        -I $(winsdk_root_dir)/Include/$(winsdk_version)/um \
        $(msvc_root_dir)/$(msvc_version)/lib/x64/libcmt.lib \
        $(msvc_root_dir)/$(msvc_version)/lib/x64/libvcruntime.lib \
        $(msvc_root_dir)/$(msvc_version)/lib/x64/oldnames.lib \
        $(winsdk_root_dir)/Lib/$(winsdk_version)/ucrt/x64/libucrt.lib \
        $(winsdk_root_dir)/Lib/$(winsdk_version)/um/x64/kernel32.lib \
        $(winsdk_root_dir)/Lib/$(winsdk_version)/um/x64/uuid.lib \
        $(binname).cpp resource.obj
	mv $(binname).exe ../
	rm -f $(binname).obj resource.obj resource.res resource.rc
endif

bconf.py: bconf.py.in ../util/build_setup
	cat $< \
	| sed "s/@python_cmd@/$(python_cmd)/g" \
	> $@

%.pyc: %.py
	$(python_cmd) -m py_compile $<

subdir-core:
	@$(MAKE) -C core

clean:
	@$(MAKE) clean -C core
ifeq ($(build_env), lingcc)
	rm -f ../$(binname)
else ifeq ($(build_env), winmsvc)
	rm -f ../$(binname).exe
endif
	find -name \*.pyc | xargs -r rm
