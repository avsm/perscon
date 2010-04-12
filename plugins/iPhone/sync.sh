#!/bin/sh 

MANIFEST=manifest.py
PARSE_DB=parse_db.py
PYTHON=/usr/bin/python
BASE="$HOME/Library/Application Support/MobileSync/Backup/"
IPHONE_LIST=`ls -1 "${BASE}"`
TMPDIR=`mktemp -d -t sms.XXXXXXXXXX`
VERBOSE=-v

trap "rm -rf $TMPDIR; exit" INT TERM EXIT

for i in "${IPHONE_LIST}"; do
    fdir="${BASE}/${i}"
    if [ ! -d "${fdir}" ]; then
        echo skipping non-directory "${fdir}"
    fi
    tmpout="${TMPDIR}/${i}"
    echo $
    ${PYTHON} ${MANIFEST} ${VERBOSE} -x Library -o ${tmpout} "${fdir}"
    echo cd ${tmpout}
    echo ${PYTHON} ${PARSE_DB} -m call -u ${i} ${tmpout}/Library/CallHistory/call_history.db
    echo ${PYTHON} ${PARSE_DB} -m sms -u ${i} ${tmpout}/Library/SMS/sms.db
    bash 
done
