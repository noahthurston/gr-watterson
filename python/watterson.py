#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2021 <+YOU OR YOUR COMPANY+>.
# 
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 
# Author: Noah Thurston, 2021


import numpy as np
from gnuradio import gr

class watterson(gr.sync_block):
    """
    Watterson Channel Model
    """
    def __init__(self, doppler_spread=1, n_paths=2, path_gains_dB="[0, 0]", path_delays_s="[0, 0.0020]"):
        gr.sync_block.__init__(self,
            name="watterson",
            in_sig=[np.complex64],
            out_sig=[np.complex64])

        self.Doppler_spread_Hz = doppler_spread
        print("Saving doppler spread: {}".format(self.Doppler_spread_Hz))

        self.n_paths = n_paths
        print("Saving n_paths: {}".format(self.n_paths))


        self.path_gains_dB = np.array(eval(path_gains_dB))
        self.path_delays_s = np.array(eval(path_delays_s))
        print("Saving path_gains_dB: {}".format(self.path_gains_dB))
        print("Saving path_delays_s: {}".format(self.path_delays_s))


        # checking to make sure the parameters are consistent with each other
        assert (len(self.path_delays_s) == len(self.path_gains_dB)), "len(self.path_delays_s) != len(self.path_gains_dB)"
        assert (len(self.path_delays_s) == self.n_paths), "len(self.path_delays_s) != self.n_paths"
        assert (len(self.path_gains_dB) == self.n_paths), "len(self.path_gains_dB) != self.n_paths"




        self.random_matrix_index = 0

        # save chan_path_up and y0 for verification later
        self.save_verification_samples = False
        self.saved_chan_path_up = None
        self.saved_y0 = None
        
        # if we want to test IO using a seeded "random matrix"
        self.seeded_random = False
        if self.seeded_random:
            from os.path import dirname, join as pjoin
            import scipy.io as sio

            random_matrices_file = sio.loadmat(pjoin("/home/episci/workarea-gnuradio/hf-cross-sdr-testbed/gr-dsss/python", 'random_matrices.mat'))
            print(random_matrices_file['random_matrix_a'][-10:])
            self.random_matrix_a = np.array(random_matrices_file['random_matrix_a'], dtype=np.complex128)

            print(random_matrices_file['random_matrix_b'][-10:])
            self.random_matrix_b = np.array(random_matrices_file['random_matrix_b'], dtype=np.complex128)

            self.random_matrix_a = np.concatenate((self.random_matrix_a, self.random_matrix_a))
            self.random_matrix_b = np.concatenate((self.random_matrix_b, self.random_matrix_b))



    def work(self, input_items, output_items):
        in0 = input_items[0]
        out = output_items[0]
        # <+signal processing here+>
        out[:] = self.channel(in0)
        return len(output_items[0])





    def channel(self, frame_symbols):
        print("Loading doppler spread: {}".format(self.Doppler_spread_Hz))

        # sys_cfg struct
        N_D = 48.
        N_T = 48.
        n_frames = 256.
        # ipos: [1x12288 double]
        # dipos: [1x12288 double]
        K_code = 7.
        rpt_code = 4.
        punct_mask = 1.
        bits_per_sym = 1.
        n_bits = 1536.
        constel = np.array([-1, 1])
        baud_rate = 2400.
        max_chan_delay_samples = 6.
        N_pre = 100.
        # known_symbols: [1x1 struct]


        # chan_cfg struct
        chan_type = 1.
        # Doppler_spread_Hz = 1.
        # n_paths = 2.
        # path_gains_dB = np.array([0, 0])
        # path_delays_s = np.array([0, 0.0020])
        force_const_modulus = 0.
        ntaps_Doppler_filter = 40.


        delay = np.round(self.path_delays_s*baud_rate)


        # this is not a system parameters, is a simulation config parameter
        n_Doppler_fil= ntaps_Doppler_filter

        # path_gains_dB = chan_cfg.path_gains_dB;
        path_gains_lin = np.power(10, (self.path_gains_dB/20))
        path_gains_lin = path_gains_lin/np.linalg.norm(path_gains_lin)

        sam_interval_approx = (1/n_Doppler_fil)/self.Doppler_spread_Hz


        chan_unders_factor = np.round(baud_rate*sam_interval_approx)
        sam_interval = chan_unders_factor/baud_rate
        d_Nieto = self.Doppler_spread_Hz * sam_interval # % Doppler spread of each path in Hz* sampling interval

        x = frame_symbols

        len_x = len(x)
        len_chan = np.ceil(len_x/chan_unders_factor)+1
        len_chan = np.max((len_chan, 10))
        chan_path = np.zeros((int(len_chan), int(self.n_paths)), dtype=np.complex128)


        seeded_random_arrays = None
        if self.seeded_random:
            r = np.arange(-n_Doppler_fil, n_Doppler_fil+1)
            filter_prop = np.exp(-np.power(np.pi, 2) * np.power(r, 2) * np.power(d_Nieto, 2))
            arr_len = int(len_chan + len(filter_prop)-1)
            seeded_random_arrays = np.random.normal(size=(int(self.n_paths), 2, arr_len))


        # [-n_Doppler_fil : n_Doppler_fil]
        r = np.arange(-n_Doppler_fil, n_Doppler_fil+1)

        filter_prop = np.exp(-np.power(np.pi, 2) * np.power(r, 2) * np.power(d_Nieto, 2))



        for ind_path in range(0, int(self.n_paths)):

            arr_len = int(len_chan + len(filter_prop)-1)
            print("arr_len: {}".format(arr_len))

            noise_for_D_chan = np.empty(arr_len, dtype=np.complex128)


            if self.seeded_random:
                # if weve used all random_matrix samples, we start over from beginning
                if self.random_matrix_index+arr_len>len(self.random_matrix_a):
                    print("-----------------------------RESETTING RANDOM MATRIX-----------------------------")
                    self.random_matrix_index=0

                start_index = self.random_matrix_index
                end_index = self.random_matrix_index + arr_len

                # get the most current random values that have not yet been used
                noise_for_D_chan.real = self.random_matrix_a.flatten()[start_index:end_index]
                noise_for_D_chan.imag = self.random_matrix_b.flatten()[start_index:end_index]

            else:
                noise_for_D_chan.real = np.random.normal(size=arr_len)
                noise_for_D_chan.imag = np.random.normal(size=arr_len)


            # chan_path(:,ind_path) = conv( noise_for_D_chan, filter_prop,'valid');
            chan_path[:,ind_path] = np.convolve( noise_for_D_chan, filter_prop,mode='valid')

            n_factor = path_gains_lin[ind_path] / np.sqrt(np.mean(np.abs(np.power(chan_path[:,ind_path], 2))))

            chan_path[:,ind_path] = chan_path[:,ind_path] * n_factor
            

        def interp_upscale(x, r):
            length = len(x)
            length_upscaled = len(x)*r + 1

            time = np.arange(0, length_upscaled)
            inferred_end_val = x[-1] + (x[-1]-x[-2])

            x = np.append(x, inferred_end_val)

            # create bitmasks to separate the measured time vals and inferred time vals
            before_mask = np.zeros(int(length_upscaled), dtype=np.bool)
            for i in range(length+1):
                before_mask[int(i*r)] = 1
            after_mask = np.invert(before_mask)

            time_given = time[before_mask]
            time_inferred = time[after_mask]


            # do interpolation with np.interp
            interped_x = np.interp(time_inferred, time_given, x)

            # x_combined is what is returned, contains both given and inferred values
            x_combined = np.zeros(int(length*r), dtype=np.complex128)

            old_vals_index = 0
            new_vals_index = 0
            for i in range(len(x_combined)):
                if i%r==0:
                    x_combined[i] = x[old_vals_index]
                    old_vals_index+=1
                else:
                    x_combined[i] = interped_x[new_vals_index]
                    new_vals_index +=1

            return x_combined


        chan_path_up = np.zeros((len(chan_path)*int(chan_unders_factor), int(self.n_paths)), dtype=np.complex128)
        for ind_path in range(0, int(self.n_paths)):

            chan_path_up[:,ind_path] = interp_upscale(chan_path[:,ind_path],chan_unders_factor);


        L_cpat = len(chan_path_up);

        del_start = 0

        if L_cpat > len_x:
            del_start = np.floor( (L_cpat - len_x)/2)

        chan_path_up = chan_path_up[range(int(del_start),int(len_x+del_start)),:]

        print("chan_path_up: {}".format(chan_path_up))
        print("chan_path_up.shape: {}".format(chan_path_up.shape))



        if force_const_modulus == 1:
            print("\n\n'if chan_cfg.force_const_modulus == 1' functionality not implemented yet")
            raise SystemExit


        y0 = np.zeros(len_x, dtype=np.complex128);

        for ind_path in range(0, int(self.n_paths)):
            ind_path_delay = delay[ind_path]

            if ind_path_delay > 0:
                # x1 = np.concatenate((frame_symbols; np.zeros((ind_path_delay, 1))))
                # print("(frame_symbols[-10:]: {}".format(frame_symbols[-10:]))
                # print("(x1[-10:]: {}".format(x1[-10:]))
                # xc = [circshift(x1, ind_path_delay)];

                xc = np.concatenate((np.zeros(int(ind_path_delay)), frame_symbols))
                xc2 = xc[0:len(x)];

                # print("xc2: {}".format(xc2))
                print("xc2.shape: {}".format(xc2.shape))
            else:
                xc2 = frame_symbols;


            # % ytest(:,ind_path) = chan_path_up(:, ind_path).* xc2;
            y0 = y0 + chan_path_up[:, ind_path]* xc2;


        print("y0: {}".format(y0[-10:]))
        print("y0.shape: {}".format(y0.shape))

        # print("len(self.random_matrix_a): {}".format(len(self.random_matrix_a)))
        print("\n\n\n")

        if self.save_verification_samples:
            if self.saved_chan_path_up is None:
                self.saved_chan_path_up = chan_path_up
            else:
                self.saved_chan_path_up = np.concatenate((self.saved_chan_path_up, chan_path_up))
            

            if self.saved_y0 is None:
                self.saved_y0 = y0
            else:
                self.saved_y0 = np.concatenate((self.saved_y0, y0))

            if len(self.saved_chan_path_up)>100000:
                import pickle as pkl
                
                file_chan_path_up = open('saved_chan_path_up.pkl', 'w')
                pkl.dump(self.saved_chan_path_up, file_chan_path_up)

                file_y0 = open('saved_y0.pkl', 'w')
                pkl.dump(self.saved_y0, file_y0)

                print("SAVED PICKLES, EXITING")
                raise SystemExit

        return y0

