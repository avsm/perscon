#!/bin/sh
EMAIL=foo@example.com
env PYTHONPATH=. appcfg.py upload_data --email ${EMAIL} --config_file=location_loader.py --filename=location_archive.csv --kind=Location --url=http://localhost:8081/remote_api .
