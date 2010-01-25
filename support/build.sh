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

FORME=FormEncode-1.2.2-py2.6.egg
if [ ! -f "$CDIR/$FORME" ]; then
  cd $OBJDIR
  ftp http://pypi.python.org/packages/source/F/FormEncode/FormEncode-1.2.2.tar.gz
  tar -zxvf FormEncode-1.2.2.tar.gz
  cd FormEncode-1.2.2
  /usr/bin/python setup.py bdist_egg
  mv dist/$FORME $CDIR
  cd ..
fi

SQLO=SQLObject-0.12.1-py2.6.egg
if [ ! -f "$CDIR/$SQLO" ]; then
  cd $OBJDIR
  ftp http://pypi.python.org/packages/source/S/SQLObject/SQLObject-0.12.1.tar.gz
  tar -zxvf SQLObject-0.12.1.tar.gz
  cd SQLObject-0.12.1
  ftp http://pypi.python.org/packages/2.6/s/setuptools/setuptools-0.6c11-py2.6.egg
  /usr/bin/python setup.py bdist_egg
  mv dist/$SQLO $CDIR
  cd ..
fi

cd ..
rm -rf $OBJDIR
