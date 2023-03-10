#
# Routines for setting up scan header arrays involving channels.
# 
# History:
#   2014-Dec-30  DG
#     Started this history log.  Added the function get_chanmask(),
#     to implement RFI flagging--uses new rfi*.txt files on ACC in /parm
#     directory
#   2015-Feb-28  DG
#     Fix some bugs with reading rfi*.txt files on ACC
#   2015-May-29  DG
#      Converted from using datime() to using Time() based on astropy.
#   2015-Jun-16  DG
#      FTP to ACC now requires a username and password
#   2015-Jun-18  DG
#      Rather major change to eliminate "bad" channels in overlap region
#   2016-May-20  DG
#      Adjusted the "good IF bandwith" gifb to 370 MHz, and adjusted the
#      flagging for overlapped IF in get_chanmask() to 2064 in order to better
#      optimize our 5 science channels in each science band.
#   2016-May-21  DG
#      Looks like dppxmp does not like going past the end of the nominal
#      500 MHz band, so set gifb back to 350 MHz and 2148 in get_chanmask().
#      This results in only four good frequencies per band at higher freqs.
#   2017-Mar-05  DG
#      Changed to work with 300 MHz design.  Changes marked.  To convert
#      back to 200 MHz, comment out lines with "300 MHz design" and uncomment
#      lines starting with ##.  Since the frequency order is swapped,
#      I added a swap of chan_asmt() output if ifbw = 600.
#   2017-Mar-06  DG
#      Changed the code so that the SOLE change between 200 MHz and 300 MHz
#      design is the value of ifbw.  Also, see if the order of channels
#      can be accounted for simply by returning a negative bandwidth
#   2017-Mar-07  DG
#      Something is not kosher with chanmask, so for now I am setting no mask.
#      See bottom of this file for relevant line.
#   2017-May-14  BC
#      Added a function freq2bdname() to figure out the band name (1-34) from a
#      given frequency value in ghz.
#   2019-Jun-26  DG
#      Fix bug in freq2bdnames() when unknown frequency was given.

import pdb
import matplotlib.pyplot as plt
import numpy as np
global nschan, ifbw, gifbw, nschanx, nsavg
# global parameters
# nschan: number of spectral channels
# ifbw: IF bandwidth in MHz
# gifbw: usable IF bandwidth in MHz, now excluding 50 MHz at the IF edge on one side (the other side is folded over for now) 
# nschanx: channels to skip at the beginning of each IF
# nsavg: number of spectral channels to average for each science channel

# ---------- SOLE CHANGE FOR DESIGN SPEED, SWAP THIS ONE COMMENT --------------
ifbw = 400.    # 200 MHz design
##ifbw = 600.   # 300 MHz design
if ifbw == 400.:
    # 200 MHz design
    gifbw = 350.
    nschanx = 0
elif ifbw == 600.:
    # 300 MHz design
    gifbw = 500.
    nschanx = 341
nschan = 4096
nsavg = [64,97,131,162,200,227,262]+[284]*27
#nsavg = [64,97,131,162,200,227,262]+[284]*3+[160]+[284]+[160]+[284]+[160]+[284]*19 #double # of channels in 11, 13, 15
#nsavg = [64,97,131,162,200,50,262]+[400]*28 #temporarily increase the number of science channels on band 6, channel width reduced from 25 MHz to 5 MHz
#nsavg = [64,97,131,162,40,227,262]+[568]*27 #temporarily increase the number of science channels on band 5
#nsavg = [64,97,131,162,200,227,262]+[400]*15+[50]+[400]*21 #temporarily increase the number of science channels on band 23 

def update_nsavg():
    #update each value in nsavg in order to cover all the good if bandwidth
    new_nsavg=[]
    for i in range(34):
        n=nsavg[i]
        df=ifbw/nschan
        nscichan=int(gifbw/(n*df))
        new_nscichan=[]
        for j in range(3):
            new_nscichan.append(nscichan-j)
        new_ns=[]
        new_fgaps=[]
        for nn in new_nscichan:
            new_n=int(gifbw/nn/df)
            new_ns.append(new_n)
            new_scibw=new_n*df
            new_fgap=gifbw-new_scibw*nn
            new_fgaps.append(new_fgap)
        new_ns=np.array(new_ns)
        new_fgaps=np.array(new_fgaps)
        ind=np.argmin(new_fgaps)
        new_nsavg.append(new_ns[ind])
    return new_nsavg

nsavg=update_nsavg()

def tot_scichan():
    nscichan=[]
    for n in nsavg:
        df=ifbw/nschan
        nscichan.append(int(gifbw/(n*df)))
    print(nscichan)
    return sum(nscichan)

def chan_asmt(bnd):
    # Input band (bnd) ranges from 1-34, but the code below uses band,
    # which ranges from 0-33.
    band = bnd - 1
    if bnd < 1 or bnd > 34:
        # Error in band number provided
        return -1

    global nschan, ifbw, gifbw, nschanx, nsavg
    df = ifbw/nschan

    chasmt = [0]*nschanx

    # Create list of science channels for each band up to this one
    nscichan = []
    for n in nsavg[0:band+1]:
        nscichan.append(int(gifbw/(n*df)))
    # Sum number of science channels for all bands up to but
    # not including this one.
    nsci = 0
    if band == 0:
        pass
    else:
        for n in nscichan[0:band]:
            nsci += n
    for i in range(nscichan[band]):
        chasmt += [i+nsci+1]*nsavg[band]
    nrest = 4096 - len(chasmt)
    chasmt += [0]*nrest
    if ifbw == 400:
        return chasmt
    else:
        # Reverse order of channel assignment for 300 MHz design
        return chasmt[::-1]

def start_freq(band):
    # Input band (bnd) ranges from 1-34
    if band < 1 or band > 34:
        # Error in band number provided
        return -1

    global nschan, ifbw, gifbw, nschanx, nsavg
    # Frequency assigned to the first spectral channel, in GHz
    fsx = 0.95+(600.-ifbw)/1000.
    df = ifbw/nschan

    sf = []

    # Create list of frequencies for each science channel in this band
    nscichan = int(gifbw/(nsavg[band-1]*df))
    for n in range(nscichan):
        sf.append(fsx + (band-1)*0.5 + (nschanx + nsavg[band-1]*n)*df/1000.)

    return sf

def sci_bw(band):
    # Input band (bnd) ranges from 1-34
    if band < 1 or band > 34:
        # Error in band number provided
        return -1

    global nschan, ifbw, gifbw, nschanx, nsavg
    df = ifbw/nschan

    nscichan = int(gifbw/(nsavg[band-1]*df))
    scibw = [nsavg[band-1]*df/1000.]*nscichan

    return scibw
    #if ifbw == 400:
    #    return scibw
    #else:
    #    # Reverse sign of bandwidth for 300 MHz design
    #    scibw = [-x for x in scibw]
    #    return scibw

def plt_chan():
    bands=np.arange(34)+1
    plt.figure(figsize=(10,6),dpi=100)
    plt.axis((1,18,0,1))
    plt.xlabel('RF Frequency (GHz)')
    plt.ylabel('Normalization')
    plt.xlim(1,18)
    for band in bands:
        chasmt=chan_asmt(band)
        sf=np.array(start_freq(band))
        bw=np.array(sci_bw(band))
        ef=sf+bw
        for i in range(len(sf)):
            plt.axvspan(sf[i],ef[i],ymin=0,ymax=1,alpha=0.5,color='b')
    plt.show()

def get_chanmask(fsequence,t=None):
    ''' 
        Returns a 204800-byte array (50*4096) with 1's where channels are kept,
        and 0's were channels are to be flagged.  In this version, 
        no channels are flagged.
    '''
    chanmask = np.ones(204800,'byte')
    return chanmask

def freq2bdname(fghz):
    '''figure out the band name (1-34) from a given frequency in GHz (such as uv['sfreq'] values from Miriad 
       UV data, which are frequency values at the CENTER of the frequency channel). Return -1 if not found 
    '''
    bfreqs=[] #start frequency of a band
    efreqs=[] #end frequency of a band
    for b in range(34):
        bfreqs.append(start_freq(b+1)[0])
        efreqs.append(start_freq(b+1)[-1]+sci_bw(b+1)[-1])
    if isinstance(fghz,list) or isinstance(fghz,np.ndarray):
        bds = []
        for fg in fghz:
            bd, = np.where((np.array(bfreqs) < fg) & (np.array(efreqs) > fg))
            if len(bd) == 1:
                bds.append(bd[0]+1)
            else:
                if fg > 0.0:  # Suppress warning if the frequency is zero
                    print('{0:f} GHz is not found in any band'.format(fghz))
                bds.append(-1)
        return np.array(bds)
    else:
        bd, = np.where((np.array(bfreqs) < fghz) & (np.array(efreqs) > fghz))
        if len(bd) == 1:
            return bd[0]+1
        else:
            if fg > 0.0:  # Suppress warning if the frequency is zero
                print('{0:f} GHz is not found in any band'.format(fghz))
            return -1
