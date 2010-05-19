#!/bin/sh
EMAIL=anil@recoil.org
env PYTHONPATH=. appcfg.py upload_data --email ${EMAIL} --config_file=location_loader.py --filename=location_archive.csv --kind=Location --url=https://avsm-03.appspot.com/remote_api .
