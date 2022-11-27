#!/usr/bin/env python

"""
peach - load Excel files produced from Peach rowing data

Clancy Rowley
1 Nov 2021
Princeton University
"""

__all__ = ["PeachData"]

import pandas as pd
import numpy as np
from datetime import date
from dateutil import parser

class PeachData():
    def __init__(self, fname):
        df = pd.read_excel(fname, header=None)
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
        
        # read the rest of the data from the "Periodic" section
        per_start = np.flatnonzero(df[1] == "Periodic")[0]
        self.headers = df.iloc[per_start + 1].dropna().to_numpy(copy=True)
        self.data = df.iloc[per_start+3:].dropna(axis=1, how='all').to_numpy(dtype=float, copy=True)
        self.t0 = int(self.data[0,0])  # initial time
        self.dt = 20  # timestep, in milliseconds

    @property
    def numstrokes(self):
        return len(self.start_times) - 1

    def __ind(self, time):
        return (time - self.t0) // self.dt

    def stroke(self, i, cols, debug=False):
        if i < 0 or i >= self.numstrokes:
            raise ValueError("Number of strokes %d out of bounds (%d)"
                             % (i, self.numstrokes))
        if debug:
            print("  times %d to %d" % (self.start_times[i], self.start_times[i+1]))
        istart = self.__ind(self.start_times[i])
        istop = self.__ind(self.start_times[i+1])
        if debug:
            print("  indices %d to %d" % (istart, istop))
        return self.data[istart:istop,np.array(cols)]
    
    def stroke_aperiodic(self, i, cols, debug=False):
        return self.aper_data[i,np.array(cols)]
    
        
    def resample_stroke(self, i, cols, npts):
        if i < 0 or i >= self.numstrokes:
            raise ValueError("Number of strokes %d out of bounds (%d)"
                             % (i, self.numstrokes))
        tstart = self.start_times[i]
        tstop = self.start_times[i+1]
        # print("times %d to %d" % (tstart, tstop))
        istart = self.__ind(tstart)
        istop = self.__ind(tstop)
        t = range(tstart, tstop, self.dt)
        tsample = np.linspace(tstart, tstop, npts+1)[:-1]
        resampled = np.zeros((npts, len(cols)))
        for j, col in enumerate(cols):
            resampled[:,j] = np.interp(tsample, t, self.data[istart:istop,col])
        return resampled


    def resampled_boat_stroke(self, i, cols, npts):
        if i < 0 or i >= self.numstrokes:
            raise ValueError("Number of strokes %d out of bounds (%d)"
                             % (i, self.numstrokes))
        resampeds  = [np.zeros((npts, 3))]*8
        for seat in range(8):
            if cols[0]==0:
                new_cols = [col+seat for col in cols[1:]]
                new_cols.insert(0,0)
            else:
                new_cols = [col+seat for col in cols]
            resampeds[seat] = self.resample_stroke(i, new_cols, npts)
        return np.mean(resampeds, axis=0)

    def get_date(self):
        return self.date

    def get_notes(self):
        return self.misc_info

    def get_athletes(self):
        return self.athlete_map





    

def main():
    fname = "./test_sheets/Uni M8+ 2015Apr18 2km race.xlsx"
    elite = PeachData(fname)
    print("%d strokes" % elite.numstrokes)
    # print(elite.aper_headers)
    print(elite.athlete_map)
    print("DATE")
    print(elite.date)
    print(elite.misc_info)
    # print(elite.resampled_boat_stroke(75, [1,9,17], 100))
    # print(elite.start_times)
    # print(elite.data[:5])

if __name__ == "__main__":
    main()
