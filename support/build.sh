#!/bin/bash 
# build eggs used by the plugins

PLATFORM=`uname`

CDIR=$(pwd)
V=2.0.9
set -ex
OBJDIR=$CDIR/obj
mkdir -p $OBJDIR

OIMAP_REPO=http://github.com/avsm/perscon-imap.git
if [ ! -d perscon-imap ]; then
  git clone ${OIMAP_REPO}
fi
cd perscon-imap
/usr/bin/python setup.py clean
/usr/bin/python setup.py bdist_egg
mv dist/offlineimap-6.2.0-py2.6.egg $CDIR/
cd $CDIR

if [[ $PLATFORM == 'Darwin' ]]; then
  SJEGG=simplejson-$V-py2.6-macosx-10.6-universal.egg
elif [[ $PLATFORM == "Linux" ]]; then
  SJEGG=simplejson-$V-py2.6.egg
fi
if [ ! -f "$CDIR/$SJEGG" ]; then
  cd $OBJDIR
  wget http://pypi.python.org/packages/source/s/simplejson/simplejson-$V.tar.gz
  tar -zxvf simplejson-$V.tar.gz
  cd simplejson-$V
  /usr/bin/python setup.py bdist_egg
  mv dist/$SJEGG $CDIR
  cd ..
fi

SV=0.16.0
if [[ $PLATFORM == 'Darwin' ]]; then
  STORM=storm-$SV-py2.6-macosx-10.6-universal.egg
elif [[ $PLATFORM == 'Linux' ]]; then
  STORM=storm-$SV-py2.6-linux-`uname -m`.egg
fi
if [ ! -f "$CDIR/$STORM" ]; then
  cd $OBJDIR
  wget http://launchpad.net/storm/trunk/0.16/+download/storm-$SV.tar.bz2
  tar -jxvf storm-$SV.tar.bz2
  cd storm-$SV
  /usr/bin/python setup.py bdist_egg
  mv dist/$STORM $CDIR
  cd ..
fi

LXMLV=2.2.4
if [[ $PLATFORM == 'Darwin' ]]; then
  LXML=lxml-$LXMLV-py2.6-macosx-10.6-universal.egg
elif [[ $PLATFORM == 'Linux' ]]; then
  LXML=lxml-$LXMLV-py2.6-linux-`uname -a`.egg
fi

if [ ! -f "$CDIR/$LXML" ]; then
  cd $OBJDIR
  wget http://pypi.python.org/packages/source/l/lxml/lxml-$LXMLV.tar.gz
  tar -jxvf lxml-$LXMLV.tar.gz
  cd lxml-2.2.4
  /usr/bin/python setup.py bdist_egg
  mv dist/$LXML $CDIR
  cd ..
fi

cd ..
rm -rf $OBJDIR
