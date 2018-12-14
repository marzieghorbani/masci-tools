#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 11 21:17:10 2018

@author: christianpartmann
"""

from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from matplotlib import pyplot as plt
import h5py
import time

bohr_constant = 0.52
hartree_in_ev = 27.2114

times = []
times += [time.time()]

filename = 'banddos_4x4'
#filename = 'banddos'
#filename = 'banddos_Co'

f = h5py.File("Data/"+filename+str('.hdf'), 'r')

evs = np.array(f["/eigenvalues/eigenvalues"])
llc =  np.array(f["/eigenvalues/lLikeCharge"])
#unfold_weight = np.array(f["/bandUnfolding/weights"])

special_points = f["/kpts/specialPointIndices"]
special_points_label = f["/kpts/specialPointLabels"]
band_unfolding = f["/general"].attrs['bandUnfolding'][0]
fermi_energy = f["/general"].attrs['lastFermiEnergy'][0]
atom_group = f["/atoms/equivAtomsGroup"]

(NUM_SPIN, NUM_K, NUM_E, NUM_GROUPS, NUM_CHAR) = llc.shape

# ugly, but doesn't matter for total runtime
# check if rec_cell or rec_cell.T is correct!!!!!!!!!!!
def k_phys(f):
    kpts_int = f["/kpts/coordinates"]
    rec_cell = f["/cell/reciprocalCell"][:]
    phys_k = np.dot(kpts_int, rec_cell.T)

    kx = phys_k[:].T[0]
    ky = phys_k[:].T[1]
    kz = phys_k[:].T[2]
    k_dist = np.zeros(len(kx))
    k_dist[0] = 0
    for i in range(1, len(kx)):
        k_dist[i] = k_dist[i-1] + np.sqrt((kx[i]-kx[i-1])**2 +(ky[i]-ky[i-1])**2 +(kz[i]-kz[i-1])**2)
    return k_dist

def create_spin_filter(which_spin, NUM_SPIN = NUM_SPIN):
    SPIN_FILTER = np.zeros(NUM_SPIN).astype(bool)
    SPIN_FILTER[which_spin] = True
    return SPIN_FILTER

def create_character_filter(which_characters):
    CHARACTER_FILTER = np.zeros(4).astype(bool)
    CHARACTER_FILTER[which_characters] = True
    return CHARACTER_FILTER

def create_group_filter(which_groups = range(NUM_GROUPS)):
    GROUP_FILTER = np.zeros(NUM_GROUPS).astype(bool)
    GROUP_FILTER[which_groups] = True
    return GROUP_FILTER

def create_band_filter(which_bands = range(NUM_E)):
    BAND_FILTER = np.zeros(NUM_E).astype(bool)
    BAND_FILTER[which_bands] = True
    return BAND_FILTER

k = k_phys(f)


times += [time.time()]

def get_k_special_pt(ind_special_points, k):
    k_special_pt = np.zeros(len(special_points[:]))
    for i in range(len(special_points[:])):
        k_special_pt[i] = k[special_points[i]-1]
    return k_special_pt

k_special_pt = get_k_special_pt(special_points, k)

# this is the expensive funkction!
# reads all data, selects relevant parts and reduces along groups and characters
# generic form: pass lists of booleans...
def get_data(f, llc, SPIN_FILTER, CHARACTER_FILTER, GROUP_FILTER, BAND_FILTER, UNFOLD_WEIGHT=band_unfolding, unfoldong_weight_exponent = 1):
    ATOMS_PER_GROUP = np.zeros(NUM_GROUPS)
    for i in range(NUM_GROUPS):
        ATOMS_PER_GROUP[i] = np.count_nonzero(np.array(atom_group)==i)
    
    # filter arrays in bands and spin:
    llc = llc[SPIN_FILTER, :, :, :, :]
    llc = llc[:, :, BAND_FILTER, :, :]
    # reduce the arrays in Character, Spin, Group
    #llc_red = llc[SPIN_FILTER, :, :, :, :]
    llc_red = llc[:, :, :, GROUP_FILTER, :]
    llc_red = llc_red[:, :, :, :, CHARACTER_FILTER]
    #llc_red = llc_red[:, :, BAND_FILTER, :, :]
    ATOMS_PER_GROUP_red = ATOMS_PER_GROUP[GROUP_FILTER]
    
    # compute normalized weights with tensor product
    llc_redG = np.tensordot(llc_red, ATOMS_PER_GROUP_red, axes=([3],[0]))
    llc_redGC = np.sum(llc_redG, axis = 3)
    llc_norm_temp = np.tensordot(llc, ATOMS_PER_GROUP, axes=([3],[0]))
    llc_norm = np.sum(llc_norm_temp, axis = 3)
    llc_normalized = llc_redGC/llc_norm
    
    # consider unfolding weight
    if(UNFOLD_WEIGHT == True):
        unfold_weight = np.array(f["/bandUnfolding/weights"])
        unfold_weight = unfold_weight[SPIN_FILTER, :, :]
        unfold_weight = unfold_weight[:, :, BAND_FILTER]
        unfold_weight = unfold_weight**unfoldong_weight_exponent
        llc_normalized = llc_normalized * unfold_weight
    
    return llc_normalized

def reshape_data(f, llc, evs, k, spin, CHARACTER_FILTER, GROUP_FILTER, BAND_FILTER, UNFOLD_WEIGHT=band_unfolding, unfoldong_weight_exponent = 1):
    SPIN_FILTER = create_spin_filter(spin)
    total_weight = get_data(f, llc, SPIN_FILTER, CHARACTER_FILTER, GROUP_FILTER, BAND_FILTER, UNFOLD_WEIGHT, unfoldong_weight_exponent)
    # only select the requested spin and bands
    evs = evs[spin, :, BAND_FILTER]

    # to speed up scatter plot, unfold data in one dimension
    (Nk, Ne) = evs.T.shape

    evs_resh = np.reshape(evs, Nk*Ne)
    weight_resh = np.reshape(total_weight[0].T, Nk*Ne)
    k_resh = np.tile(k, Ne)
    return (k_resh, evs_resh, weight_resh)

label = []
for i in range(len(special_points_label)):
    label += str(special_points_label[i])[2]

times += [time.time()]

spin = 0
unfoldong_weight_exponent = 1.0
SPIN_FILTER = create_spin_filter(spin)
CHARACTER_FILTER = create_character_filter([0,1,2,3])
GROUP_FILTER = create_group_filter()
UNFOLD_WEIGHT = band_unfolding
BAND_FILTER = create_band_filter()

"""
(k_r, E_r, W_r) = reshape_data(f, llc, evs, k, spin, CHARACTER_FILTER, GROUP_FILTER, BAND_FILTER, UNFOLD_WEIGHT, unfoldong_weight_exponent)
times += [time.time()]

fig = plt.figure()
ax1 = fig.add_subplot(111)

#just plot points with minimal size of t
speed_up = True
if(speed_up == True):
    t = 1e-4
    k_r = k_r[W_r>t]
    E_r = E_r[W_r>t]
    W_r = W_r[W_r>t]

ax1.scatter(k_r, (E_r-fermi_energy)*hartree_in_ev, marker='o', c='b', s = 4 * W_r, lw=0)
"""

def plot(color, ax1, f, llc, evs, k, spin, CHARACTER_FILTER, GROUP_FILTER, BAND_FILTER, UNFOLD_WEIGHT, unfoldong_weight_exponent, alpha = 1):
    (k_r, E_r, W_r) = reshape_data(f, llc, evs, k, spin, CHARACTER_FILTER, GROUP_FILTER, BAND_FILTER, UNFOLD_WEIGHT, unfoldong_weight_exponent)
    #just plot points with minimal size of t
    speed_up = True
    if(speed_up == True):
        t = 1e-4
        k_r = k_r[W_r>t]
        E_r = E_r[W_r>t]
        W_r = W_r[W_r>t]
    ax1.scatter(k_r, (E_r-fermi_energy)*hartree_in_ev, marker='o', c=color, s = 5 * W_r, lw=0, alpha = alpha)
    #print(max(W_r))
    return 0

"""
fig = plt.figure()
ax1 = fig.add_subplot(111)
alpha = 0.5
plot("red", ax1, f, llc, evs, k, 0, create_character_filter([0]), create_group_filter(), create_band_filter(),
     band_unfolding, 1, alpha)
plot("blue", ax1, f, llc, evs, k, 0, create_character_filter([1]), create_group_filter(), create_band_filter(),
     band_unfolding, 1, alpha)
plot("green", ax1, f, llc, evs, k, 0, create_character_filter([2]), create_group_filter(), create_band_filter(),
     band_unfolding, 1, alpha)
plot("yellow", ax1, f, llc, evs, k, 0, create_character_filter([3]), create_group_filter(), create_band_filter(),
     band_unfolding, 1, alpha)

plt.xticks(k_special_pt, label)
plt.ylabel("E(k) [eV]")
plt.xlim(0, max(k))
plt.hlines(0, 0, max(k), lw = 0.1)
#plt.savefig("dos_characters.png", dpi=2000)
"""


"""
# for dos_file
fig = plt.figure()
ax2 = fig.add_subplot(111)
plot("blue", ax2, f, llc, evs, k, 0, create_character_filter([0,1,2,3]), create_group_filter([0,1,2]), create_band_filter(),
     band_unfolding, 1, alpha)
plot("red", ax2, f, llc, evs, k, 0, create_character_filter([0,1,2,3]), create_group_filter([4]), create_band_filter(),
     band_unfolding, 1, alpha)
plot("green", ax2, f, llc, evs, k, 0, create_character_filter([0,1,2,3]), create_group_filter([3]), create_band_filter(),
     band_unfolding, 1, alpha)
plt.xticks(k_special_pt, label)
plt.ylabel("E(k) [eV]")
plt.xlim(0, max(k))
plt.hlines(0, 0, max(k), lw = 0.1)
plt.savefig("dos_groups_012_4_3.png", dpi=2000)
"""

def plot_two_characters(color, ax1, f, llc, evs, k, spin, CHARACTER_FILTER, GROUP_FILTER, BAND_FILTER, UNFOLD_WEIGHT, 
                        unfoldong_weight_exponent, alpha = 1):
    
    characters = np.array(range(4))[CHARACTER_FILTER]
    if(len(characters) != 2):
        print("error")
        
    (k_resh, evs_resh, weight_resh) = reshape_data(f, llc, evs, k, spin, create_character_filter([characters[0]]), GROUP_FILTER, BAND_FILTER, UNFOLD_WEIGHT=band_unfolding, unfoldong_weight_exponent = 1)
    (k_resh2, evs_resh2, weight_resh2) = reshape_data(f, llc, evs, k, spin, create_character_filter([characters[1]]), GROUP_FILTER, BAND_FILTER, UNFOLD_WEIGHT=band_unfolding, unfoldong_weight_exponent = 1)
    #print(k_resh-k_resh2)
    #print(evs_resh-evs_resh2)
    rel = weight_resh/(weight_resh+weight_resh2)*20
    #ax1.scatter(k_resh, (evs_resh-fermi_energy)*hartree_in_ev, marker='o', c="g", s = 5 * weight_resh, lw=0, alpha = alpha)
    #ax1.scatter(k_resh2, (evs_resh-fermi_energy)*hartree_in_ev, marker='o', c="r", s = 5 * weight_resh2, lw=0, alpha = alpha)
    cm = plt.cm.RdBu #get_cmap('RdYlBu')
    ax1.scatter(k_resh2, (evs_resh-fermi_energy)*hartree_in_ev, marker='o', c=rel, s = 5 * weight_resh2, lw=0, alpha = alpha,cmap=cm)

fig = plt.figure()
alpha = 1
ax4 = fig.add_subplot(111)
plot_two_characters("blue", ax4, f, llc, evs, k, 0, create_character_filter([0,1]), create_group_filter(), create_band_filter(),
     band_unfolding, 1., alpha)

plt.savefig("2characters.png", dpi=2000)

fig = plt.figure()
ax3 = fig.add_subplot(111)
alpha = 0.2
plot("blue", ax3, f, llc, evs, k, 0, create_character_filter([0,1,2,3]), create_group_filter(), create_band_filter(),
     band_unfolding, 1., alpha)
plot("red", ax3, f, llc, evs, k, 0, create_character_filter([0,1,2,3]), create_group_filter(), create_band_filter(range(256, 258)),
     False, 1., alpha)

"""
#for Co file
plot("red", ax3, f, llc, evs, k, 1, create_character_filter([0,1,2,3]), create_group_filter(), create_band_filter(),
     band_unfolding, 1, alpha)

"""

times += [time.time()]
plt.xticks(k_special_pt, label)
plt.ylabel("E(k) [eV]")
plt.xlim(0, max(k))
plt.hlines(0, 0, max(k), lw = 0.1)
#plt.savefig("sphjjhjhin.png", dpi=2000)


#plt.xlabel("k")



#plt.ylim(-10, 5)
plt.xticks(k_special_pt, label)
plt.ylabel("E(k) [eV]")
plt.xlim(0, max(k))
plt.hlines(0, 0, max(k), lw = 0.1)
#plt.savefig("testfigure.png", dpi=2000)

times += [time.time()]
times = np.array(times)-times[0]
print(times)

#%%
"""

aaa = time.time()
kk = k_phys(f)
bbb = time.time()
kpts_int = f["/kpts/coordinates"]
rec_cell = f["/cell/reciprocalCell"][:]
phys_k = np.dot(kpts_int, rec_cell)

shiftp = phys_k[1:, :]
shiftm = phys_k[:-1, :]
k_dist = np.append(np.array([0]), np.sum((phys_k[1:, :]-phys_k[:-1, :])**2, axis = 1))
#for i in range(1, len(k_dist)):
#    k_dist[i] = k_dist[i-1] + k_dist[i]

ccc = time.time()

print(bbb-aaa)
print(ccc-bbb)
"""

"""
fig2 = plt.figure()
ax2 = fig2.add_subplot(111)
for n in range(NUM_E):
        ax2.scatter(k, evs[0, :, n], marker='o', c='b', s = 2 * llc_redGC[0, :, n], lw=0)
"""  

"""
SPIN_FILTER = np.array([True])
CHARACTER_FILTER = np.array([True, False, False, False])
GROUP_FILTER = np.ones(NUM_GROUPS).astype(bool) #np.array([])
GROUP_FILTER[1] = False
"""