#!/bin/bash 
# build eggs used by the plugins

PLATFORM=`uname`
WGET="wget -c"
PYTHON=/usr/bin/python

CDIR=$(pwd)
V=2.0.9
set -ex
OBJDIR=$CDIR/obj
mkdir -p $OBJDIR

OIMAP_REPO=http://github.com/avsm/perscon-imap.git
if [ ! -d perscon-imap ]; then
  git clone ${OIMAP_REPO}
else
  git pull origin master
fi
cd perscon-imap
$PYTHON setup.py clean
$PYTHON setup.py bdist_egg
mv dist/offlineimap-6.2.0-py2.6.egg $CDIR/
cd $CDIR

KC_REPO=http://github.com/avsm/py-keyring-lib.git
if [[ $PLATFORM == 'Darwin' ]]; then
  KCEGG=keyring-0.3-py2.6-macosx-10.6-universal.egg
elif [[ $PLATFORM == "Linux" ]]; then
  KCEGG=keyring-0.3-py2.6.egg
fi
if [ ! -d py-keyring-lib ]; then
  git clone ${KC_REPO}
else
  git pull origin master
fi
cd py-keyring-lib
$PYTHON setup.py clean
$PYTHON setup.py bdist_egg
mv dist/$KCEGG $CDIR
cd $CDIR

if [[ $PLATFORM == 'Darwin' ]]; then
  SJEGG=simplejson-$V-py2.6-macosx-10.6-universal.egg
elif [[ $PLATFORM == "Linux" ]]; then
  SJEGG=simplejson-$V-py2.6.egg
fi
if [ ! -f "$CDIR/$SJEGG" ]; then
  cd $OBJDIR
  $WGET http://pypi.python.org/packages/source/s/simplejson/simplejson-$V.tar.gz
  tar -zxvf simplejson-$V.tar.gz
  cd simplejson-$V
  $PYTHON setup.py bdist_egg
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
  $WGET http://launchpad.net/storm/trunk/0.16/+download/storm-$SV.tar.bz2
  tar -jxvf storm-$SV.tar.bz2
  cd storm-$SV
  $PYTHON setup.py bdist_egg
  mv dist/$STORM $CDIR
  cd ..
fi

LXMLV=2.2.4
if [[ $PLATFORM == 'Darwin' ]]; then
  LXML=lxml-$LXMLV-py2.6-macosx-10.6-universal.egg
elif [[ $PLATFORM == 'Linux' ]]; then
  LXML=lxml-$LXMLV-py2.6-linux-`uname -m`.egg
fi

if [ ! -f "$CDIR/$LXML" ]; then
  cd $OBJDIR
  $WGET http://pypi.python.org/packages/source/l/lxml/lxml-$LXMLV.tar.gz
  tar -xvzf lxml-$LXMLV.tar.gz
  cd lxml-2.2.4
  $PYTHON setup.py bdist_egg
  mv dist/$LXML $CDIR
  cd ..
fi

SFPYV=1.0.32.0
SFPY=Skype4Py-$SFPYV-py2.6.egg

if [ ! -f "$CDIR/$SFPY" ]; then
  cd $OBJDIR
  $WGET http://sourceforge.net/projects/skype4py/files/skype4py/$SFPYV/Skype4Py-$SFPYV.tar.gz/download
  tar -xvzf Skype4Py-$SFPYV.tar.gz
  # utterly, utterly ridiculous.  perms wrong in tgz.  recurse.
  find . -type d | xargs chmod +x
  find . -type d | xargs chmod +x
  find . -type d | xargs chmod +x
  find . -type d | xargs chmod +x
  find . -type d | xargs chmod +x
  cd Skype4Py-$SFPYV
  # need to use setuptools rather than distutils
  mv setup.py setup.py.in
  sed -e 's/from distutils\.core import setup/from setuptools import setup/g' setup.py.in > setup.py
  $PYTHON setup.py bdist_egg
  mv dist/$SFPY $CDIR
  cd ..
fi

cd ..
rm -rf $OBJDIR
