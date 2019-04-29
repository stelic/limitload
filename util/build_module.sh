#!/bin/bash

set -e

mod_name=$1
shift
mod_header=$1
shift
mod_incd=$1
shift
mod_srcs=$(echo $@ | sed 's/[^ ]*\.h *//g')

script_dir=$(dirname $0)
source $script_dir/build_setup

if test $build_env = lingcc; then

    intgr_extra_defines=

elif test $build_env = winmsvc; then

    intgr_extra_defines="-DWIN32_VC"

else
    echo "*** Unknown build environment '$build_env'."
    exit 1
fi

interrogate \
    -string -fnames -refcount -assert -python-native \
    -D CPPPARSER -D __cplusplus -D volatile \
    $intgr_extra_defines \
    -S $panda_inc_dir -S $panda_inc_dir/parser-inc -S . \
    -module $mod_name -library $mod_name \
    -oc $mod_name-igate.cpp -od $mod_name.in \
    $mod_header
$python_cmd $script_dir/uncamel_igate.py $mod_name-igate.cpp

interrogate_module \
    -python-native \
    -module $mod_name -library $mod_name \
    -oc $mod_name-module.cpp \
    $mod_name.in

if test $build_env = lingcc; then

    optrtti=$(test $panda_rtti == false && echo -fno-rtti || echo)
    #libpipe=$(test $panda_pipelining == false && echo -lpthread || echo)
    libpipe=-lpthread
    g++ -O3 -shared -fPIC -fno-exceptions $optrtti -Wl,-z,defs \
        -I $python_inc_dir -I $panda_inc_dir -I . \
        -L $python_lib_dir -L $panda_lib_dir \
        -D LINGCC \
        $mod_name-igate.cpp $mod_name-module.cpp $mod_srcs \
        $libpipe \
        -lpython2.7 \
        -lpanda \
        -lpandaexpress \
        -lp3dtool \
        -lp3dtoolconfig \
        -lp3interrogatedb \
        -o $mod_name.so

    rm -f $mod_name.o

elif test $build_env = winmsvc; then

    mod_srcs=$(echo "$mod_srcs" | sed 's/\.pyd\b/.lib/g')
    cl_cmd="$msvc_root_dir/$msvc_version/bin/Hostx64/x64/cl.exe"
    "$cl_cmd" -O2 -EHsc -wd4275 -LD -MD \
        -I "$msvc_root_dir/$msvc_version/include" \
        -I "$winsdk_root_dir/Include/$winsdk_version/shared" \
        -I "$winsdk_root_dir/Include/$winsdk_version/ucrt" \
        -I "$winsdk_root_dir/Include/$winsdk_version/um" \
        -I "$python_inc_dir" -I "$panda_inc_dir" -I . \
        -D WINMSVC \
        $mod_name-module.cpp $mod_name-igate.cpp $mod_srcs \
        "$msvc_root_dir/$msvc_version/lib/x64"/msvcprt.lib \
        "$msvc_root_dir/$msvc_version/lib/x64"/msvcrt.lib \
        "$msvc_root_dir/$msvc_version/lib/x64"/oldnames.lib \
        "$msvc_root_dir/$msvc_version/lib/x64"/vcruntime.lib \
        "$winsdk_root_dir/Lib/$winsdk_version/um/x64"/kernel32.lib \
        "$winsdk_root_dir/Lib/$winsdk_version/ucrt/x64"/ucrt.lib \
        "$python_lib_dir"/python27.lib \
        "$panda_lib_dir"/libpanda.lib \
        "$panda_lib_dir"/libpandaexpress.lib \
        "$panda_lib_dir"/libp3dtool.lib \
        "$panda_lib_dir"/libp3dtoolconfig.lib \
        "$panda_lib_dir"/libp3interrogatedb.lib \
        -D BUILDING_$mod_incd \
        -Fe$mod_name.pyd

    rm -f $mod_name.obj $mod_name.exp $mod_name.*.manifest

fi

rm -f $mod_name-igate.* $mod_name.in $mod_name-module.*

