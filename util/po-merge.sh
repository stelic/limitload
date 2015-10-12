#!/bin/bash

procspec="$1"

if test -d "$procspec/po"; then
    pofiles=`echo $procspec/po/*/*.po`
elif test -d "$procspec"; then
    pofiles=`echo $procspec/*.po`
elif test -n "$procspec"; then
    pofiles="$procspec"
else
    echo "*** Missing argument."
    exit 1
fi

for pofile in $pofiles; do
    domdir=`dirname $pofile`
    domain=`basename $domdir`
    potfile="$domdir/$domain.pot"
    echo -n "$pofile  "
    msgmerge -U --backup=none --no-wrap --previous $pofile $potfile
done
