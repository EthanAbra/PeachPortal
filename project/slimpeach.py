
#!/usr/bin/env python


__all__ = ["SlimPeach"]

import numpy as np
from dateutil import parser


class SlimPeach():
    def __init__(self, df):
        try:
            # read times for start of each stroke from "Aperiodic" section of file
            athletes_start = np.flatnonzero((df[1]=='Name') & (df[2]=='Abbr'))[0]
            self.athlete_map = df.iloc[athletes_start+1: athletes_start+9, 1].dropna().to_numpy(copy=True)

            self.date = parser.parse(df.iloc[2, 3])

            misc_start = np.flatnonzero((df[0]=='SessionComments') & (df[1]=='SessionName'))[0]
            misc_end = np.flatnonzero((df[0]=='=====') & (df[1]=='Boat Info'))[0]

            self.misc_info = df.iloc[misc_start+1:misc_end, 0].dropna().to_numpy(copy=True)


            aper_start = np.flatnonzero((df[1] == "Aperiodic") & (df[2] == "0x800A"))[0]
            aper_stop = np.flatnonzero((df[1] == "Aperiodic") & (df[2] == "0x8001"))[0]
            self.start_times = df.iloc[aper_start+5:aper_stop,0].to_numpy(dtype=int, copy=True)
            self.aper_headers = df.iloc[aper_start + 1].dropna().to_numpy(copy=True)
            self.aper_data = df.iloc[aper_start+5:aper_stop].dropna(axis=1, how='all').to_numpy(dtype=float, copy=True)
            
        except Exception as e:
            print(e)
            return e


    @property
    def numstrokes(self):
        return len(self.start_times) - 1

    def get_boat_power(self):
        return self.aper_data[:,133][:-1]



    

def main():
    fname = "./test_sheets/Uni M8+ 2015Apr18 2km race.xlsx"


if __name__ == "__main__":
    main()
