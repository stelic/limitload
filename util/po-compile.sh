#!/bin/bash

set -e

procspec="$1"

if test -d "$procspec/po"; then
    pofiles=`echo $procspec/po/*/*.po`
    modir="$procspec/mo"
elif test -d "$procspec"; then
    pofiles=`echo $procspec/*.po`
    modir="$procspec/../../mo"
elif test -n "$procspec"; then
    pofiles="$procspec"
    podir=`dirname "$procspec"`
    modir="$podir/../../mo"
else
    echo "*** Missing argument."
    exit 1
fi

for pofile in $pofiles; do
    echo -n "$pofile  "
    domain=`dirname $pofile | xargs basename`
    pobase=`basename $pofile`
    lang=${pobase/.po/}
    mosubdir=$modir/$lang/LC_MESSAGES
    mkdir -p $mosubdir
    lmofile=${pofile/.po/.mo}
    msgfmt -c --statistics $pofile -o $lmofile
    mofile=$mosubdir/$domain.mo
    if test -f $mofile && cmp -s $lmofile $mofile; then
        true
    else
        cp $lmofile $mofile
    fi
done
