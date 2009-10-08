#!/bin/sh 
# build eggs used by the plugins

V=2.0.9
set -ex
OBJDIR=./obj
mkdir -p $OBJDIR

cd $OBJDIR
ftp http://pypi.python.org/packages/source/s/simplejson/simplejson-$V.tar.gz
tar -zxvf simplejson-$V.tar.gz
cd simplejson-$V
/usr/bin/python setup.py bdist_egg
mv dist/simplejson-$V-py2.6-macosx-10.6-universal.egg ../..
cd ..

V=2.2b2
ftp http://pypi.python.org/packages/source/p/pyobjc-framework-SyncServices/pyobjc-framework-SyncServices-$V.tar.gz
tar -zxvf pyobjc-framework-SyncServices-$V.tar.gz
cd pyobjc-framework-SyncServices-$V
/usr/bin/python setup.py bdist_egg
mv dist/pyobjc_framework_SyncServices-$V-py2.6.egg ../..
cd ..

cd ..
rm -rf $OBJDIR


