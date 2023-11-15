"""
Little Python script to download the databases
"""

import argparse
from urllib.request import urlretrieve

ROBBINS_URL = "https://pdsimage2.wr.usgs.gov/Individual_Investigations/moon_lro.kaguya_multi_craterdatabase_robbins_2018/data/lunar_crater_database_robbins_2018.csv"
ROBBINS_FILENAME = "lunar_crater_database_robbins_2018.csv"

YANG_URL = "https://figshare.com/ndownloader/files/24160592"
YANG_FILENAME = "yang_aged_database.csv"


def main():
    urlretrieve(YANG_URL, YANG_FILENAME)
    # urlretrieve(ROBBINS_URL, ROBBINS_FILENAME)


if __name__ == "__main__":
    main()
