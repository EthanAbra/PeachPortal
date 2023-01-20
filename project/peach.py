
#!/usr/bin/env python

"""
peach - load Excel files produced from Peach rowing data

Clancy Rowley, modified by ea10
1 Nov 2021
Princeton University
"""

__all__ = ["PeachData"]

import numpy as np
from dateutil import parser
from itertools import groupby


class PeachData():
    def __init__(self, df):
        try:
            # read times for start of each stroke from "Aperiodic" section of file
            athletes_start = np.flatnonzero((df[1]=='Name') & (df[2]=='Abbr'))[0]
            df1 = df.head(20)
            if (df1[0]=='Cox').any():
                athletes_stop = np.flatnonzero(df[0]=='Cox')[0]
            else:
                athletes_stop = np.flatnonzero(df[0]=='Coach')[0]
            self.athlete_map = df.iloc[athletes_start+1: athletes_stop, 1].dropna().to_numpy(copy=True)
            

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
            
        except Exception as e:
            print(e)
            return e


    @classmethod
    def from_unsplit(cls, unsplitdata):
        obj = cls.__new__(cls)  # Does not call __init__
        super(PeachData, obj).__init__()  # Don't forget to call any polymorphic base class initializers
        obj.athlete_map = unsplitdata['athlete_map']
        obj.date = unsplitdata['date']
        obj.misc_info = unsplitdata['notes']
        obj.start_times = unsplitdata['start_times']
        obj.aper_headers = unsplitdata['aper_headers']
        obj.aper_data = unsplitdata['aper_data']
        obj.headers = unsplitdata['headers']
        obj.data = unsplitdata['data']
        obj.t0 = unsplitdata['t0']
        obj.dt = unsplitdata['dt']
        return obj


    @property
    def numstrokes(self):
        return len(self.start_times) - 1

    @property
    def numseats(self):
        return len(self.athlete_map)
    
    @property
    def swivel_power_idx(self):
        return np.where(self.aper_headers == 'SwivelPower')[0][0]
    
    @property
    def min_angle_idx(self):
        return np.where(self.aper_headers == 'MinAngle')[0][0]
    
    @property
    def catch_slip_idx(self):
        return np.where(self.aper_headers == 'CatchSlip')[0][0]
    
    @property
    def max_angle_idx(self):
        return np.where(self.aper_headers == 'MaxAngle')[0][0]
    
    @property
    def finish_slip_idx(self):
        return np.where(self.aper_headers == 'FinishSlip')[0][0]
    
    @property
    def drive_start_time_idx(self):
        return np.where(self.aper_headers == 'Drive Start T')[0][0]
    
    @property
    def max_force_percentage_idx(self):
        return np.where(self.aper_headers == 'Max Force PC')[0][0]
    
    @property
    def rating_idx(self):
        return np.where(self.aper_headers == 'Rating')[0][0]
    
    @property 
    def boat_power_idx(self):
        return np.where(self.aper_headers == 'Average Power')[0][0]
    
    @property
    def gate_angle_idx(self):
        return np.where(self.headers == 'GateAngle')[0][0]
    
    @property 
    def gate_force_x_idx(self):
        return np.where(self.headers == 'GateForceX')[0][0]
    
    @property
    def gate_angle_vel_idx(self):
        return np.where(self.headers == 'GateAngleVel')[0][0]
            

    def __ind(self, time):
        return (time - self.t0) // self.dt
    
    
    def open_ind(self, time):
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
        resampeds  = [np.zeros((npts, 3))]*self.numseats
        for seat in range(self.numseats):
            if cols[0]==0:
                new_cols = [col+seat for col in cols[1:]]
                new_cols.insert(0,0)
            else:
                new_cols = [col+seat for col in cols]
            resampeds[seat] = self.resample_stroke(i, new_cols, npts)
        return np.mean(resampeds, axis=0)

    def get_boat_power(self):
        return self.aper_data[:,self.boat_power_idx][:-1]

    def get_date(self):
        return self.date

    def get_notes(self):
        return self.misc_info

    def get_athletes(self):
        return self.athlete_map
    
    def set_athletes(self, athlete_list):
        self.athlete_map = athlete_list
    
    def get_start_times(self):
        return self.start_times

    def get_average_aper_data(self, stroke_rng = None):
        if stroke_rng:
            start, end = stroke_rng
            return np.mean(self.aper_data[start:end+1], axis=0)
        else:
            return np.mean(self.aper_data, axis=0)

    def get_rating_chunks(self):
        event = self.aper_data[:,self.rating_idx][:-1]
        event = list(zip(event, list(range(len(event)))))
        event.sort(key = lambda y: y[0])
        delta_t = 2

        # rating filter
        r = [list(v) for (k, v) in groupby(event, lambda v: v[0] // delta_t)]

        def solve(r):
            for e in r:
                yield min(e, key = lambda y: y[1])
                yield max(e, key = lambda y: y[1])


        tup_r = list(solve(r))
        r = sorted(tup_r, key = lambda y: y[1])

        # remove all sequential strokes
        useSet = set()
        r_small = []
        for elem in r:
            if elem[1]-1 not in useSet:
                r_small.append(elem)
            useSet.add(elem[1])
        


        pairs = [(r_small[i][1], r_small[i+1][1]) for i in range(len(r_small)-1)]

        return pairs
