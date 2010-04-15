#!/bin/bash
EMAIL=${EMAIL:-anil@recoil.org}
env PYTHONPATH=. appcfg.py download_data --email ${EMAIL} --config_file=location_loader.py --filename=location_archive.csv --kind=Location .
