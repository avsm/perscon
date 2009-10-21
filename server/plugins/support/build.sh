#!/bin/bash 
# build eggs used by the plugins

CDIR=$(pwd)
V=2.0.9
set -ex
OBJDIR=$CDIR/obj
mkdir -p $OBJDIR

OIMAP=~/src/oss/lifedb/offlineimap
cd $OIMAP
/usr/bin/python setup.py clean
/usr/bin/python setup.py bdist_egg
mv dist/offlineimap-6.2.0-py2.6.egg $CDIR/
cd $CDIR

SJEGG=simplejson-$V-py2.6-macosx-10.6-universal.egg
if [ ! -f "$CDIR/$SJEGG" ]; then
  cd $OBJDIR
  ftp http://pypi.python.org/packages/source/s/simplejson/simplejson-$V.tar.gz
  tar -zxvf simplejson-$V.tar.gz
  cd simplejson-$V
  /usr/bin/python setup.py bdist_egg
  mv dist/$SJEGG $CDIR
  cd ..
fi

cd ..
rm -rf $OBJDIR