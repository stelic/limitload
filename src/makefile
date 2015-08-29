
util_dir := ../util
build_env := $(shell grep 'build_env=' $(util_dir)/build_setup | sed 's/.*=//')
python_cmd := $(shell grep 'python_cmd=' $(util_dir)/build_setup | sed 's/.*=//')

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
	rc -fo resource.res resource.rc
	cvtres -machine:x64 -out:resource.obj resource.res
	cl -D WINMSVC -D PYTHON_CMD='"$(python_cmd)"' $(binname).cpp resource.obj
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
