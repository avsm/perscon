#!/bin/sh

if [ "$1" = "" ]; then
  echo Usage: $0 password
  exit 1
fi

/usr/bin/security add-generic-password -s Perscon -a root -p $1
