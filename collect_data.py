
import math
from multiprocessing import Pool
from types import FunctionType
import numpy as np
import argparse
from csv import writer
import matplotlib.pyplot as plt
from matplotlib import rc
import os


#*************************** INPUT PARSING ****************************


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description='''
    A script designed to make it easier to extract data from output files

            Currently the output formats supported are
            ------------------------------------------
                -  ORCA
                -  DALTON
                -  GAUSSIAN
                -  LSDALTON

            This script can currently extract the data
            ------------------------------------------
                -  Total energies
                -  Zero-Point Vibrational energies
                -  Enthalpies
                -  Entropies
                -  Gibbs Free energies
                -  Dipole moments
                -  Polarizability
                -  Excitation energies
                -  Oscillator strengths
                -  Frequencies
                -  Partition functions at a given temperature

    Though not all data types have been implemented for all of the output formats

    All values are extracted as Atomic Units where applicable'''
    ,epilog='''
    The following is not implemented for ORCA
    -  Entropies

    The following is not implemented for DALTON
    -  Non DFT total energies
    -  Zero-Point Vibrational energies
    -  Enthalpies
    -  Entropies
    -  Gibbs Free energies
    -  Frequencies
    -  Partition functions with symmetry

    The following is not implemented for GAUSSIAN
    -  Entropies
    -  Excitation energies
    -  Oscillator strengths

    The following is not implemented for LSDALTON
    -  Probably some total energies
    -  Zero-Point Vibrational energies
    -  Enthalpies
    -  Gibbs Free energies
    -  Entropies
    -  Dipole moments
    -  Polarizabilities
    -  Excitation energies
    -  Oscillator strengths
    -  Frequencies
    -  Partition functions

    For help contact
    Theo Juncker von Buchwald
    fnc970@alumni.ku.dk

    Magnus Bukhave Johansen
    qhw298@alumni.ku.dk''')

    parser.add_argument('infile', type=str, nargs='+', help='The file(s) to extract data from', metavar='File')

    parser.add_argument('-q', '--quiet', action='store_true', help='Include for the script to stay silent - This will not remove error messages or the printing of data')
    parser.add_argument('-s', '--suppress', action='store_true', help='Include to suppress all print statements (including errors) except the data output')
    parser.add_argument('-csv', action='store_true', help='Include to write the found values in csv file(s)')
    parser.add_argument('-E', '--energy', action='store_true', help='Include to extract the Total Energy')
    parser.add_argument('-Z', '--zpv', action='store_true', help='Include to extract the Zero-Point Vibrational Energy')
    parser.add_argument('-H', '--enthalpy', action='store_true', help='Include to calculate molar enthalpies (kJ/mol)')
    parser.add_argument('-S', '--entropy', action='store_true', help='Include to calculate molar entropes (kJ/(mol*K)')
    parser.add_argument('-G', '--gibbs', action='store_true', help='Include to extract the Gibbs Free Energy')
    parser.add_argument('-D', '--dipole', action='store_true', help='Include to extract the Dipole Moment')
    parser.add_argument('-P', '--polar', action='store_true', help='Include to extract the Polarizability')
    parser.add_argument('-X', '--exc', const=-1, type=int, help='Include to extract the Excitation Energies. Add a number to extract that amount of Excitation Energies. It will extract all Excitation energies as default',nargs='?')
    parser.add_argument('-O', '--osc', action='store_true', help='Include to extract the Oscillator Strengths')
    parser.add_argument('-F', '--freq', const=-1, type=int, help='Include to extract the Frequencies. Add a number to extract that amount of Frequencies. It will extract all Frequencies as default', nargs='?')
    parser.add_argument('-Q', '--partfunc', action='store_true', help='Include to calculate molar partition functions.')
    parser.add_argument('-T', '--temp', const=298.15, default=298.15, type=float, help='Include to calculate at a different temperature. Default is 298.15 K', nargs='?')
    parser.add_argument('--uvvis', const='png', type=str, help='Include to calculate a UV-VIS spectrum. Tou can give the picture format as an optional argument. Will use png as default', nargs='?', choices=['png', 'eps', 'pdf', 'svg', 'ps'])


#******************************* SETUP ********************************


    args = parser.parse_args()
    input_file = args.infile
    CSV = args.csv
    UVVIS = args.uvvis
    T = args.temp

    RequestedArguments = {   #These are all the possible arguments that extract data
        '_Energy' : args.energy,
        '_ZPV' : args.zpv,
        '_Dipole_moments' : args.dipole,
        '_Polarizabilities' : args.polar,
        '_Excitation_energies' : args.exc,
        '_Oscillator_strengths' : args.osc,
        '_Frequencies' : args.freq,
        '_Enthalpy' : args.enthalpy,
        '_Entropy' : args.entropy,
        '_Gibbs' : args.gibbs,
        '_PartitionFunctions' : args.partfunc,
    }

    Outputs = {     #These are the datapoints that will be extracted per argument
        '_Energy' : ['tot_energy'],
        '_ZPV' : ['zpv'],
        '_Enthalpy' : ['enthalpy'],
        '_Entropy' : ['entropy'],
        '_Gibbs' : ['gibbs'],
        '_Dipole_moments' : ['dipolex', 'dipoley', 'dipolez', 'total_dipole'],
        '_Polarizabilities' : ['polx', 'poly', 'polz', 'iso_polar'],
        '_Excitation_energies' : ['exc_energies'],
        '_Oscillator_strengths' : ['osc_strengths'],
        '_Frequencies' : ['freq'],
        '_PartitionFunctions' : ['qTotal'],
    }

    Header_text = { #These are what will be written in the header for each datapoint
        'tot_energy' : 'Energy',
        'zpv' : 'ZPV Energy',
        'enthalpy' : 'Enthalpy',
        'entropy' : 'Entropy (kJ/(mol*K)',
        'gibbs' : 'Gibbs Free Energy',
        'dipolex' : 'Dipole x',
        'dipoley' : 'Dipole y',
        'dipolez' : 'Dipole z',
        'total_dipole' : 'Total Dipole',
        'polx' : 'Polarizability xx',
        'poly' : 'Polarizability yy',
        'polz' : 'Polarizability zz',
        'iso_polar' : 'Isotropic Polarizability',
        'exc_energies' : 'Exc. energy',
        'osc_strengths' : 'Osc. strength',
        'freq' : 'Frequency',
        'qTotal' : 'Total molar partition function',
    }

    quiet = args.quiet
    suppressed = args.suppress

    NeededArguments = RequestedArguments.copy()

    if UVVIS:
        NeededArguments['_Oscillator_strengths'] = NeededArguments['_Excitation_energies'] = -1

    if NeededArguments['_Oscillator_strengths'] and NeededArguments['_Excitation_energies'] == None:   #Ensuring that excitation energies are calculated when oscillator strengths are
        NeededArguments['_Oscillator_strengths'] = NeededArguments['_Excitation_energies'] = -1
    elif NeededArguments['_Oscillator_strengths']:
        NeededArguments['_Oscillator_strengths'] = NeededArguments['_Excitation_energies']

    if NeededArguments['_Gibbs']:
        NeededArguments['_Enthalpy'] = True
        NeededArguments['_Entropy'] = True

    if NeededArguments['_PartitionFunctions']:  #Ensuring that frequencies are calculated as these are needed to calculate the Partition Functions
        NeededArguments['_Frequencies'] = -1

    if NeededArguments['_Enthalpy']:  #Ensuring that frequencies are calculated as these are needed to calculate the Partition Functions
        NeededArguments['_Frequencies'] = -1

    if NeededArguments['_Entropy']:  #Ensuring that frequencies are calculated as these are needed to calculate the Partition Functions
        NeededArguments['_Frequencies'] = -1

    Variable_arrays = dict([item for item in NeededArguments.items() if type(item[1]) == int])    #Dictionary of data where the amount of values printed can be changed


#******************************* CLASSES ******************************


class gaus:
    def __init__(self,input):
        with open(input, "r") as file:
            self.lines = file.readlines()

        self.file = input
        self.end = len(self.lines)

    def _Energy(self):
        linenumber = Forward_search_last(self.file, 'Sum of electronic and zero-point Energies=', 'final energy', err=False)
        if type(linenumber) == int:
            self.tot_energy = float(self.lines[linenumber].split()[-1]) - float(self.lines[linenumber-4].split()[-2])
            return
        linenumber = Forward_search_last(self.file, 'SCF Done:', 'final energy')
        if type(linenumber) == int:
            self.tot_energy = float(self.lines[linenumber].split()[4])
            return
        self.tot_energy = 'NaN'

    def _ZPV(self):
        linenumber = Forward_search_last(self.file, 'Sum of electronic and zero-point Energies=', 'ZPV energy')
        if type(linenumber) == int:
            self.zpv = float(self.lines[linenumber].split()[-1])
            return
        self.zpv = 'NaN'

    def _Dipole_moments(self):
        linenumber = Forward_search_last(self.file, 'Electric dipole moment (input orientation):', 'dipole moments')
        if type(linenumber) == int:
            self.dipolex, self.dipoley, self.dipolez, self.total_dipole = float(self.lines[linenumber+4].split()[1].replace('D','E')), float(self.lines[linenumber+5].split()[1].replace('D','E')), float(self.lines[linenumber+6].split()[1].replace('D','E')), float(self.lines[linenumber+3].split()[1].replace('D','E'))
            return
        self.dipolex = self.dipoley = self.dipolez = self.total_dipole = 'NaN'

    def _Polarizabilities(self):
        linenumber = ['NaN', 'NaN', 'NaN', 'NaN']
        searchwords = [' xx ', ' yy ', ' zz ', ' iso ']
        for i in range(len(searchwords)):
            linenumber[i] = Forward_search_after_last(self.file, 'Dipole polarizability, Alpha (input orientation).', searchwords[i], 15, 'polarizabilities')
        if linenumber != ['NaN', 'NaN', 'NaN', 'NaN']:
            self.polx, self.poly, self.polz, self.iso_polar = float(self.lines[linenumber[0]].split()[1].replace('D','E')), float(self.lines[linenumber[1]].split()[1].replace('D','E')), float(self.lines[linenumber[2]].split()[1].replace('D','E')), float(self.lines[linenumber[3]].split()[1].replace('D','E'))
            return
        self.polx = self.poly = self.polz = self.iso_polar = 'NaN'

    def _Frequencies(self):
        self.freq = []
        linenumbers = Forward_search_all(self.file, 'Frequencies --', 'frequencies')
        if type(linenumbers) == list:
            for i in linenumbers:
                for j in self.lines[i].split()[2:]:
                    self.freq.append(float(j)*inv_cm_to_au)
        if len(self.freq) == 0:
            self.freq = ['NaN'] * abs(NeededArguments['_Frequencies'])
        if len(self.freq) < NeededArguments['_Frequencies']:
            self.freq += ['NaN'] * (NeededArguments['_Frequencies'] - len(self.freq))

    def _Excitation_energies(self):
        self.exc_energies = []
        linenumber = Forward_search_last(self.file, 'Excitation energies and oscillator strengths:', 'excitation energies', err=False)
        linenumbers = Forward_search_all(self.file, 'Excited State', 'excitation energies')
        if type(linenumber) == int:
            linenumbers = [i for i in linenumbers if i > linenumber]
            for i in linenumbers:
                self.exc_energies.append(float(self.lines[i].split()[4])*ev_to_au)
        if len(self.exc_energies) == 0:
            self.exc_energies = ['NaN'] * abs(NeededArguments['_Excitation_energies'])
        if len(self.exc_energies) < NeededArguments['_Excitation_energies']:
            self.exc_energies += ['NaN'] * (NeededArguments['_Excitation_energies'] - len(self.exc_energies))

    def _Oscillator_strengths(self):
        self.osc_strengths = []
        linenumber = Forward_search_last(self.file, 'Excitation energies and oscillator strengths:', 'oscillator strengths', err=False)
        linenumbers = Forward_search_all(self.file, 'Excited State', 'oscillator strengths')
        if type(linenumber) == int:
            linenumbers = [i for i in linenumbers if i > linenumber]
            for i in linenumbers:
                self.osc_strengths.append(float(self.lines[i].split()[-1].replace('f=','')))
        if len(self.osc_strengths) == 0:
            self.osc_strengths = ['NaN'] * abs(NeededArguments['_Excitation_energies'])
        if len(self.osc_strengths) < NeededArguments['_Excitation_energies']:
            self.osc_strengths += ['NaN'] * (NeededArguments['_Excitation_energies'] - len(self.osc_strengths))

    def _RotationalConsts(self):
        self.rots = []
        linenumbers = Forward_search_all(self.file, 'Rotational constants (GHZ):', 'rotational constants')
        for i in self.lines[linenumbers[-2]].split()[3:]:
            self.rots.append(float(i))
        self.rots = np.array(self.rots)
        self.rots = self.rots[self.rots != 0.0]

    def _Mass(self):
        self.mass = 0.0
        linenumber = Forward_search_last(self.file, 'Molecular mass', 'molecular mass')
        if type(linenumber) == int:
            self.mass = float(self.lines[linenumber].split()[2])

    def _SymmetryNumber(self):
        self.symnum = 0
        linenumber = Forward_search_last(self.file, 'Rotational symmetry number', 'rotational symmetry number')
        if type(linenumber) == int:
            self.symnum = int(self.lines[linenumber].split()[-1].replace('.',''))

    def _Multiplicity(self):
        self.multi = 0
        linenumber = Forward_search_first(self.file, 'Multiplicity', 'multiplicity')
        if type(linenumber) == int:
            self.multi = int(self.lines[linenumber].split()[-1])

    def _PartitionFunctions(self):
        if CheckForOnlyNans(np.array(self.freq)):
            if not(suppressed):
                print(f"No frequencies found in {self.file}, skipping partition function calculation")
            self.qTotal = 'NaN'
            return
        self._RotationalConsts()
        self._Mass()
        self._SymmetryNumber()
        self._Multiplicity()
        self.qT = trans_const_fac * self.mass ** (1.5) * T ** (2.5)
        if len(self.rots) == 1:
            self.qR = rot_lin_const * T / (self.symnum * self.rots[0])
        else:
            self.qR = rot_poly_const * T ** (1.5) / ( self.symnum * np.prod(np.array(self.rots)) ** (0.5))
        realfreq = np.array([x for x in self.freq if x != 'NaN'])
        realfreq = realfreq[realfreq > 0.0]
        self.qV = np.prod(1 / (1 - np.exp( - vib_const * realfreq / T)))
        self.qE = self.multi #Good approximation for most closed-shell molecules
        self.qTotal = self.qT*self.qR*self.qV*self.qE

    def _Enthalpy(self):
        if CheckForOnlyNans(np.array(self.freq)):
            if not(suppressed):
                print(f"No frequencies found in {self.file}, skipping enthalpy calculation")
            self.enthalpy = 'NaN'
            return
        self._RotationalConsts()
        self._Energy()
        self.E_T = 3/2 * T * gas_constant
        if len(self.rots) == 1:
            self.E_R = T * gas_constant
        else:
            self.E_R = 3/2 * T * gas_constant
        realfreq = np.array([x for x in self.freq if x != 'NaN'])
        realfreq = realfreq[realfreq > 0.0]
        self.E_V = gas_constant * np.sum(vib_const * realfreq * (1/2 + 1 / (np.exp(vib_const * realfreq / T) - 1)))
        self.E_e = 0 #Good approximation for most closed-shell molecules
        self.enthalpy = (self.E_T+self.E_R+self.E_V+gas_constant * T) / au_to_kJmol + self.tot_energy

    def _Entropy(self):
        if CheckForOnlyNans(np.array(self.freq)):
            if not(suppressed):
                print(f"No frequencies found in {self.file}, skipping enthalpy calculation")
            self.entropy = 'NaN'
            return
        self._RotationalConsts()
        self._Mass()
        self._SymmetryNumber()
        self._Multiplicity()
        self.S_T = gas_constant * np.log(s_trans_const * self.mass ** 1.5 * T ** 2.5)
        if len(self.rots) == 1:
            self.S_R = gas_constant * np.log(rot_lin_const * T / (self.symnum * self.rots[0]))
        else:
            self.S_R = gas_constant * (3/2 + np.log(rot_poly_const * T ** (1.5) / ( self.symnum * np.prod(np.array(self.rots)) ** (0.5))))
        realfreq = np.array([x for x in self.freq if x != 'NaN'])
        realfreq = realfreq[realfreq > 0.0]
        self.S_V = gas_constant * np.sum(vib_const * realfreq / T / (np.exp(vib_const * realfreq / T) - 1) - np.log(1-np.exp(-vib_const * realfreq / T)))
        self.S_E = gas_constant * np.log(self.multi) #Good approximation for most closed-shell molecules
        self.entropy = self.S_T+self.S_R+self.S_V+self.S_E

    def _Gibbs(self):
        if CheckForOnlyNans(np.array(self.freq)):
            if not(suppressed):
                print(f"No frequencies found in {self.file}, skipping free energy calculation")
            self.gibbs = 'NaN'
            return
        self.gibbs = self.enthalpy - T*self.entropy / au_to_kJmol


class orca:
    def __init__(self,input):
        with open(input, "r") as file:
            self.lines = file.readlines()

        self.file = input
        self.end = len(self.lines)

    def _Energy(self):
        linenumber = Forward_search_last(self.file, 'Electronic energy', 'Final energy', err = False)
        if type(linenumber) == int:
            self.tot_energy = float(self.lines[linenumber].split()[-2])
            return
        linenumber = Forward_search_last(self.file, 'FINAL SINGLE POINT ENERGY', 'Final energy')
        if type(linenumber) == int:
            self.tot_energy = float(self.lines[linenumber].split()[-1])
            return
        self.tot_energy = 'NaN'

    def _ZPV(self):
        linenumber = Forward_search_last(self.file, 'Electronic energy', 'ZPV energy')
        if type(linenumber) == int:
            self.zpv = float(self.lines[linenumber].split()[-2]) + float(self.lines[linenumber+1].split()[-4])
            return
        self.zpv = 'NaN'

    def _Enthalpy(self):
        if CheckForOnlyNans(np.array(self.freq)):
            if not(suppressed):
                print(f"No frequencies found in {self.file}, skipping enthalpy calculation")
            self.enthalpy = 'NaN'
            return
        self._RotationalConsts()
        self._Energy()
        self.E_T = 3/2 * T * gas_constant
        if len(self.rots) == 1:
            self.E_R = T * gas_constant
        else:
            self.E_R = 3/2 * T * gas_constant
        realfreq = np.array([x for x in self.freq if x != 'NaN'])
        realfreq = realfreq[realfreq > 0.0]
        self.E_V = gas_constant * np.sum(vib_const * realfreq * (1/2 + 1 / (np.exp(vib_const * realfreq / T) - 1)))
        self.E_e = 0 #Good approximation for most closed-shell molecules
        self.enthalpy = (self.E_T+self.E_R+self.E_V+gas_constant * T) / au_to_kJmol + self.tot_energy

    def _Gibbs(self):
        if CheckForOnlyNans(np.array(self.freq)):
            if not(suppressed):
                print(f"No frequencies found in {self.file}, skipping free energy calculation")
            self.gibbs = 'NaN'
            return
        self.gibbs = self.enthalpy - T*self.entropy / au_to_kJmol

    def _Dipole_moments(self):
        linenumber = Forward_search_last(self.file, 'Total Dipole Moment', 'dipole moment')
        if type(linenumber) == int:
            self.dipolex, self.dipoley, self.dipolez, self.total_dipole = float(self.lines[linenumber].split()[-3]), float(self.lines[linenumber].split()[-2]), float(self.lines[linenumber].split()[-1]), float(self.lines[linenumber+2].split()[-1])
            return
        self.dipolex, self.dipoley, self.dipolez, self.total_dipole = 'NaN'

    def _Polarizabilities(self):
        linenumber = Forward_search_after_last(self.file, 'THE POLARIZABILITY TENSOR', "'diagonalized tensor:'", 10, 'polarizability')
        if type(linenumber) == int:
            self.polx, self.poly, self.polz, self.iso_polar = float(self.lines[linenumber+1].split()[0]), float(self.lines[linenumber+1].split()[1]), float(self.lines[linenumber+1].split()[2]), float(self.lines[linenumber+7].split()[-1])
            return
        self.polx = self.poly = self.polz = self.iso_polar = 'NaN'

    def _Excitation_energies(self):
        self.exc_energies = []
        linenumbers = Forward_search_all(self.file, 'STATE ', 'excitation energies')
        if type(linenumbers) == list:
            for i in linenumbers:
                self.exc_energies.append(float(self.lines[i].split()[3]))
        if len(self.exc_energies) == 0:
            self.exc_energies = ['NaN'] * abs(NeededArguments['_Excitation_energies']  )
        if len(self.exc_energies) < NeededArguments['_Excitation_energies']:
            self.exc_energies += ['NaN'] * (NeededArguments['_Excitation_energies'] - len(self.exc_energies))

    def _Oscillator_strengths(self):
        self.osc_strengths = []
        linenumber = Forward_search_last(self.file, 'ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS', 'oscillator strengths')
        if type(linenumber) == int:
            for i in range(len(self.exc_energies)):
                if len(self.lines[linenumber+5+i].split()) > 6:
                    self.osc_strengths.append(float(self.lines[linenumber+5+i].split()[3]))
                else:
                    self.osc_strengths.append('NaN')
        if len(self.osc_strengths) == 0:
            self.osc_strengths = ['NaN'] * abs(NeededArguments['_Excitation_energies'])
        if len(self.osc_strengths) < NeededArguments['_Excitation_energies']:
            self.osc_strengths += ['NaN'] * (NeededArguments['_Excitation_energies'] - len(self.osc_strengths))

    def _Frequencies(self):
        self.freq = []
        linenumber = Forward_search_last(self.file, "VIBRATIONAL FREQUENCIES", 'frequencies')
        if type(linenumber) == int:
            for j in self.lines[linenumber+7: self.end]:
                if ": " and " 0.00 " in j:
                    pass
                elif ": " in j and not " 0.00 " in j:
                    self.freq.append(float(j.split()[1])*inv_cm_to_au)
                else:
                    break
        if len(self.freq) == 0:
            self.freq = ['NaN'] * abs(NeededArguments['_Frequencies'])
        if len(self.freq) < NeededArguments['_Frequencies']:
            self.freq += ['NaN'] * (NeededArguments['_Frequencies'] - len(self.freq))

    def _RotationalConsts(self):
        self.rots = []
        linenumbers = Forward_search_first(self.file, 'Rotational constants in MHz', 'rotational constants')
        for i in self.lines[linenumbers].split()[-3:]:
            self.rots.append(float(i))
        self.rots = np.array(self.rots) * 1E-3
        self.rots = self.rots[self.rots != 0.0]

    def _Mass(self):
        self.mass = 0.0
        linenumber = Forward_search_last(self.file, 'Total Mass', 'molecular mass')
        if type(linenumber) == int:
            self.mass = float(self.lines[linenumber].split()[-2])

    def _SymmetryNumber(self):
        self.symnum = 0
        linenumber = Forward_search_last(self.file, 'Symmetry Number', 'rotational symmetry number')
        if type(linenumber) == int:
            self.symnum = int(self.lines[linenumber].split()[-1])

    def _Multiplicity(self):
        self.multi = 0
        linenumber = Forward_search_first(self.file, 'Multiplicity', 'multiplicity')
        if type(linenumber) == int:
            self.multi = int(self.lines[linenumber].split()[-1])

    def _PartitionFunctions(self):
        if CheckForOnlyNans(np.array(self.freq)):
            if not(suppressed):
                print(f"No frequencies found in {self.file}, skipping partition function calculation")
            self.qTotal = 'NaN'
            return
        self._RotationalConsts()
        self._Mass()
        self._Multiplicity()
        self._SymmetryNumber()
        self.qT = trans_const_fac * self.mass ** (1.5) * T ** (2.5)
        if len(self.rots) == 1:
            self.qR = rot_lin_const * T / (self.symnum * self.rots[0])
        else:
            self.qR = rot_poly_const * T ** (1.5) / ( self.symnum * np.prod(np.array(self.rots)) ** (0.5))
        realfreq = np.array([x for x in self.freq if x != 'NaN'])
        realfreq = realfreq[realfreq > 0.0]
        self.qV = np.prod(1 / (1 - np.exp( - vib_const * realfreq / T)))
        self.qE = self.multi #Good approximation for most closed-shell molecules
        self.qTotal = self.qT*self.qR*self.qV*self.qE

    def _Entropy(self):
        if CheckForOnlyNans(np.array(self.freq)):
            if not(suppressed):
                print(f"No frequencies found in {self.file}, skipping enthalpy calculation")
            self.entropy = 'NaN'
            return
        self._RotationalConsts()
        self._Mass()
        self._Multiplicity()
        self._SymmetryNumber()
        self.S_T = gas_constant * np.log(s_trans_const * self.mass ** 1.5 * T ** 2.5)
        if len(self.rots) == 1:
            self.S_R = gas_constant * np.log(rot_lin_const * T / (self.symnum * self.rots[0]))
        else:
            self.S_R = gas_constant * (3/2 + np.log(rot_poly_const * T ** (1.5) / ( self.symnum * np.prod(np.array(self.rots)) ** (0.5))))
        realfreq = np.array([x for x in self.freq if x != 'NaN'])
        realfreq = realfreq[realfreq > 0.0]
        self.S_V = gas_constant * np.sum(vib_const * realfreq / T / (np.exp(vib_const * realfreq / T) - 1) - np.log(1-np.exp(-vib_const * realfreq / T)))
        self.S_E = gas_constant * np.log(self.multi) #Good approximation for most closed-shell molecules
        self.entropy = self.S_T+self.S_R+self.S_V+self.S_E


class dal:
    def __init__(self,input):
        with open(input, "r") as file:
            self.lines = file.readlines()

        self.file = input
        self.end = len(self.lines)

    def _Energy(self):
        linenumber = Forward_search_last(self.file, '@    Final .* energy:', 'final energy', err=False)
        if type(linenumber) == int:
            self.tot_energy = float(self.lines[linenumber].split()[-1])
            return
        linenumber = Forward_search_last(self.file, '@ Energy at final geometry is', 'final energy')
        if type(linenumber) == int:
            self.tot_energy = float(self.lines[linenumber].split()[-2])
            return
        self.tot_energy = 'NaN'

    def _ZPV(self):
        linenumber = Forward_search_last(self.file, 'Total Molecular Energy', 'zero-point energy')
        if type(linenumber) == int:
            self.zpv = float(self.lines[linenumber+5].split()[1])
            return
        self.zpv = 'NaN'

    def _Dipole_moments(self):
        linenumber = Forward_search_last(self.file, 'Dipole moment components', 'dipole moment')
        if type(linenumber) == int:
            self.dipolex, self.dipoley, self.dipolez, self.total_dipole = float(self.lines[linenumber+5].split()[1]), float(self.lines[linenumber+6].split()[1]), float(self.lines[linenumber+7].split()[1]), float(self.lines[linenumber-3].split()[0])
            return
        self.dipolex = self.dipoley = self.dipolez = self.total_dipole = 'NaN'

    def _Polarizabilities(self):
        linenumber = Forward_search_last(self.file, 'SECOND ORDER PROPERTIES', 'polarizabilities')
        if type(linenumber) == int:
            self.polx, self.poly, self.polz = float(self.lines[linenumber+2].split()[-1]), float(self.lines[linenumber+5].split()[-1]), float(self.lines[linenumber+7].split()[-1])
            self.iso_polar = (self.polx + self.poly + self.polz)/3.
            return
        self.polx = self.poly = self.polz = self.iso_polar = 'NaN'

    def _Excitation_energies(self):
        self.exc_energies = []
        linenumber = Forward_search_last(self.file, '@  Oscillator strengths are dimensionless.', 'excitation energies', err=False)
        if type(linenumber) == int:
            self.exc_type = '.EXCITA'
            for i in self.lines[linenumber+5: self.end]:
                if "@ "in i:
                    self.exc_energies.append(float(i.split()[3])*ev_to_au)
                else:
                    break
        linenumbers = Forward_search_all(self.file, '@ Excitation energy', 'excitation energies')
        if type(linenumbers) == list:
            self.exc_type = 'MCTDHF'
            for i in linenumbers:
                self.exc_energies.append(float(self.lines[i].split()[-2]))
        if len(self.exc_energies) == 0:
            self.exc_energies = ['NaN'] * abs(NeededArguments['_Excitation_energies'])
        if len(self.exc_energies) < NeededArguments['_Excitation_energies']:
            self.exc_energies += ['NaN'] * (NeededArguments['_Excitation_energies'] - len(self.exc_energies))

    def _Oscillator_strengths(self):
        self.osc_strengths = []
        if self.exc_type == '.EXCITA':
            linenumber = Forward_search_last(self.file, '@  Oscillator strengths are dimensionless.', 'oscillator strengths')
            if type(linenumber) == int:
                for i in self.lines[linenumber+5: self.end]:
                    if "@ " in i:
                        self.osc_strengths.append(float(i.split()[-1]))
                    else:
                        break
        if self.exc_type == 'MCTDHF':
            linenumbers = Forward_search_all(self.file, '@ Excitation energy', 'oscillator strengths')
            if type(linenumbers) == list:
                for i in linenumbers:
                    osc = 0
                    for j in self.lines[i:i+15]:
                        if '@ Oscillator strength' in j:
                            osc += float(j.split()[5])**2
                    self.osc_strengths.append(osc**0.5)
        if len(self.osc_strengths) == 0:
            self.osc_strengths = ['NaN'] * len(self.exc_energies)
            return
        if len(self.osc_strengths) < NeededArguments['_Excitation_energies']:
            self.osc_strengths += ['NaN'] * (NeededArguments['_Excitation_energies'] - len(self.osc_strengths))

    def _Frequencies(self):
        self.freq = []
        linenumber = Forward_search_last(self.file, 'Vibrational Frequencies and IR Intensities', 'frequencies')
        if type(linenumber) == int:
            for i in self.lines[linenumber+7: self.end]:
                if len(i.split()) < 1:
                    break
                self.freq.append(float(i.split()[3]))
        if len(self.freq) == 0:
            self.freq = ['NaN'] * abs(NeededArguments['_Frequencies'])
        if len(self.freq) < NeededArguments['_Frequencies']:
            self.freq += ['NaN'] * (NeededArguments['_Frequencies'] - len(self.freq))

    def _RotationalConsts(self):
        self.rots = []
        linenumbers = Forward_search_last(self.file, 'Rotational constants', 'rotational constants')
        for i in self.lines[linenumbers+7].split()[:-1]:
            self.rots.append(float(i))
        self.rots = np.array(self.rots) * 1E-3
        self.rots = self.rots[self.rots != 0.0]

    def _Mass(self):
        self.mass = 0.0
        linenumber = Forward_search_last(self.file, 'Total mass:', 'molecular mass')
        if type(linenumber) == int:
            self.mass = float(self.lines[linenumber].split()[-2])

    #Symmetry checking not implemented by default in Dalton
    #def _SymmetryNumber(self):
    #
    #    self.symnum = 0
    #    linenumber = Forward_search_last(self.file, 'Symmetry Number', 'rotational symmetry number')
    #    if type(linenumber) == int:
    #        self.symnum = int(self.lines[linenumber].split()[-1])

    def _Multiplicity(self):
        self.multi = 0
        linenumber = Forward_search_last(self.file, 'Spatial symmetry', 'multiplicity')
        if type(linenumber) == int:
            self.multi = int(self.lines[linenumber].split()[2])

    def _PartitionFunctions(self):
        if CheckForOnlyNans(np.array(self.freq)):
            if not(suppressed):
                print(f"No frequencies found in {self.file}, skipping partition function calculation")
            self.qTotal = 'NaN'
            return
        self._RotationalConsts()
        self._Mass()
        self._Multiplicity()
        self.qT = trans_const_fac * self.mass ** (1.5) * T ** (2.5)
        #Rotational does not give the same as Dalton, due to a correction from the assymmetric top being applied: 10.1063/1.1748490
        if len(self.rots) == 1:
            self.qR = rot_lin_const * T / (self.rots[0])
        else:
            self.qR = rot_poly_const * T ** (1.5) / (np.prod(self.rots) ** (0.5))
        realfreq = np.array([x for x in self.freq if x != 'NaN'])
        realfreq = realfreq[realfreq > 0.0]
        self.qV = np.prod(1 / (1 - np.exp( - vib_const * realfreq / T)))
        self.qE = self.multi #Good approximation for most closed-shell molecules
        self.qTotal = self.qT*self.qR*self.qV*self.qE

    def _Entropy(self):
        if CheckForOnlyNans(np.array(self.freq)):
            if not(suppressed):
                print(f"No frequencies found in {self.file}, skipping enthalpy calculation")
            self.entropy = 'NaN'
            return
        self._RotationalConsts()
        self._Mass()
        self._Multiplicity()
        self.S_T = gas_constant * np.log(s_trans_const * self.mass ** 1.5 * T ** 2.5)
        if len(self.rots) == 1:
            self.S_R = gas_constant * np.log(rot_lin_const * T / (self.rots[0]))
        else:
            self.S_R = gas_constant * (3/2 + np.log(rot_poly_const * T ** (1.5) / ( np.prod(self.rots) ** (0.5))))
        realfreq = np.array([x for x in self.freq if x != 'NaN'])
        realfreq = realfreq[realfreq > 0.0]
        self.S_V = gas_constant * np.sum(vib_const * realfreq / T / (np.exp(vib_const * realfreq / T) - 1) - np.log(1-np.exp(-vib_const * realfreq / T)))
        self.S_E = gas_constant * np.log(self.multi) #Good approximation for most closed-shell molecules
        self.entropy = self.S_T+self.S_R+self.S_V+self.S_E

    def _Enthalpy(self):
        if CheckForOnlyNans(np.array(self.freq)):
            if not(suppressed):
                print(f"No frequencies found in {self.file}, skipping enthalpy calculation")
            self.enthalpy = 'NaN'
            return
        self._RotationalConsts()
        self._Energy()
        self.E_T = 3/2 * T * gas_constant
        if len(self.rots) == 1:
            self.E_R = T * gas_constant
        else:
            self.E_R = 3/2 * T * gas_constant
        realfreq = np.array([x for x in self.freq if x != 'NaN'])
        realfreq = realfreq[realfreq > 0.0]
        self.E_V = gas_constant * np.sum(vib_const * realfreq * (1/2 + 1 / (np.exp(vib_const * realfreq / T) - 1)))
        self.E_e = 0 #Good approximation for most closed-shell molecules
        self.enthalpy = (self.E_T+self.E_R+self.E_V+gas_constant * T) / au_to_kJmol + self.tot_energy

    def _Gibbs(self):
        if CheckForOnlyNans(np.array(self.freq)):
            if not(suppressed):
                print(f"No frequencies found in {self.file}, skipping free energy calculation")
            self.gibbs = 'NaN'
            return
        self.gibbs = self.enthalpy - T*self.entropy / au_to_kJmol


class lsdal:
    def __init__(self,input):
        with open(input, "r") as file:
            self.lines = file.readlines()

        self.file = input
        self.end = len(self.lines)

    def _Energy(self):
        linenumber = Forward_search_last(self.file, 'Final .* energy:', 'final energy', err=False)
        if type(linenumber) == int:
            self.tot_energy = float(self.lines[linenumber].split()[-1])
            return
        linenumber = Forward_search_last(self.file, 'ENERGY SUMMARY', 'final energy')
        if type(linenumber) == int:
            for i in self.lines[linenumber+3:self.end]:
                if 'E: ' in i:
                    self.tot_energy = float(i.split()[-1])
                else:
                    return
        self.tot_energy = 'NaN'

    def _Dipole_moments(self):
        linenumber = Forward_search_last(self.file, 'Permanent dipole moment', 'dipole moment')
        if type(linenumber) == int:
            self.dipolex, self.dipoley, self.dipolez, self.total_dipole = self.lines[linenumber+9].split()[1], self.lines[linenumber+10].split()[1], self.lines[linenumber+11].split()[1], self.lines[linenumber+3].split()[0]
            return
        self.dipolex = self.dipoley = self.dipolez = self.total_dipole = 'NaN'

    def _Polarizabilities(self):
        linenumber = Forward_search_last(self.file, '*          POLARIZABILITY TENSOR RESULTS (in a.u.)          *', 'polarizability')
        if type(linenumber) == int:
            self.polx, self.poly, self.polz, self.iso_polar = self.lines[linenumber+10].split()[-3], self.lines[linenumber+11].split()[-2], self.lines[linenumber+12].split()[-1], self.lines[linenumber+14].split()[-1]
            return
        self.polx = self.poly = self.polz = self.iso_polar = 'NaN'

    def _Excitation_energies(self):
        self.exc_energies = []
        linenumber = Forward_search_last(self.file, '*                   ONE-PHOTON ABSORPTION RESULTS (in a.u.)                  *', 'excitation energies')
        if type(linenumber) == int:
            for i in range(linenumber+8,self.end):
                if len(self.lines[i].split()) < 1:
                    break
                self.exc_energies.append(self.lines[i].split()[0])
        if len(self.exc_energies) == 0:
            self.exc_energies = ['NaN'] * abs(NeededArguments['_Excitation_energies']  )
        if len(self.exc_energies) < NeededArguments['_Excitation_energies']:
            self.exc_energies += ['NaN'] * (NeededArguments['_Excitation_energies'] - len(self.exc_energies))

    def _Oscillator_strengths(self):
        self.osc_strengths = []
        linenumber = Forward_search_last(self.file, '*                   ONE-PHOTON ABSORPTION RESULTS (in a.u.)                  *', 'oscillator strengths')
        if type(linenumber) == int:
            for i in range(len(self.exc_energies)):
                self.osc_strengths.append(self.lines[linenumber+8+i].split()[-1])
        if len(self.osc_strengths) == 0:
            self.osc_strengths = ['NaN'] * abs(NeededArguments['_Excitation_energies'])
        if len(self.osc_strengths) < NeededArguments['_Excitation_energies']:
            self.osc_strengths += ['NaN'] * (NeededArguments['_Excitation_energies'] - len(self.osc_strengths))


#**************************** FUNCTIONS *******************************


def Forward_search_last(file: str, text: str, error: str, err: bool =True):
    """Searches from the beggining of the file given to the end where it returns the linenumber of the last occurence

    Args:
        file (str): The file to search in
        text (str): The text string to search for
        error (str): If no occurences were found it will print 'No [error] could be found in [file]
        err (bool, optional): Whether or not to print error message if no occurences are found. Defaults to True.

    Returns:
        (int): Linenumber of last occurence
    """
    res = os.popen(f"grep -nT '{text}' {file} | tail -n 1 | awk '{{print $1}}'").readlines()
    if len(res) == 0:
        if not(suppressed):
            if err:
                print(f'No {error} could be found in {file}')
        return 'NaN'
    return int(res[0].replace(':\n','')) - 1

def Forward_search_after_last(file: str, text1: str, text2: str, lines: int, error: str, err: bool=True):
    """Searches from beggining of file for last occurence of [text1] and in the following [lines] after for [text2]

    Args:
        file (str): File to search in
        text1 (str): From the last occurence of this this function will search
        text2 (str): This is what will be found in the lines following [text1]
        lines (int): How many lines after [text1] should the function search for [text2]
        error (str): If no occurences were found it will print 'No [error] could be found in [file]
        err (bool, optional): Whether or not to print error message if no occurences are found. Defaults to True.. Defaults to True.

    Returns:
        (int): Linenumber of [text2] occurence
    """
    res = os.popen(f"grep -nTA{lines} '{text1}' {file} | tail -n {lines + 1} | grep {text2} | awk '{{print $1}}'").readlines()
    if len(res) == 0:
        if not(suppressed):
            if err:
                print(f'No {error} could be found in {file}')
        return 'NaN'
    return int(res[0].replace('-\n','')) - 1

def Forward_search_first(file: str, text: str, error: str, err: bool=True):
    """Searches from beginning of file and finds the first occurence of [text]

    Args:
        file (str): File to search in
        text (str): Text to look for
        error (str): If no occurences were found it will print 'No [error] could be found in [file]
        err (bool, optional): Whether or not to print error message if no occurences are found. Defaults to True.. Defaults to True.

    Returns:
        (int): Linenumber of first occurence
    """
    res = os.popen(f"grep -nTm1 '{text}' {file} | awk '{{print $1}}'").readlines()
    if len(res) == 0:
        if not(suppressed):
            if err:
                print(f'No {error} could be found in {file}')
        return 'NaN'
    return int(res[0].replace(':\n','')) - 1

def Forward_search_all(file: str, text: str, error: str, err: bool=True):
    """Searches from beggining of file to end of file finding all occurences of [text]

    Args:
        file (str): File to search in
        text (str): Text to look for
        error (str): If no occurences were found it will print 'No [error] could be found in [file]
        err (bool, optional): Whether or not to print error message if no occurences are found. Defaults to True.. Defaults to True.

    Returns:
        (list): List of the linenumbers of all occurences
    """
    res  = os.popen(f"grep -nT '{text}' {file} | awk '{{print $1}}'").readlines()
    if len(res) == 0:
        if not(suppressed):
            if err:
                print(f'No {error} could be found in {file}')
        return 'NaN'
    return [int(val.replace(':\n','')) - 1 for val in res]

def Resize(array: list):
    """Takes an array of arrays with varying sizes and resizes them to the same size.
    This is done by appending 'NaN' to the smaller lists.
    If the first value says 'Not implemented' the remainder of the array will be filled with 'Not implemented

    Args:
        array (list): Array of arrays with varying sizes
    """
    max_size = 0
    for arr in array:
        if len(arr) > max_size:
            max_size = len(arr)

    for i, arr in enumerate(array):
        if arr == ['Not implemented']:
            array[i] *= max_size
        else:
            array[i] += ['NaN'] * (max_size - len(arr))

def CheckForOnlyNans(array: list):
    """Function for checking if an array is fille only with the value 'NaN'

    Args:
        array (list): Array that should be looked through

    Returns:
        (bool): Returns a False/True based on whether or not the array the array only consists of 'NaN'
    """
    for i in array:
        if i != 'NaN':
           return False
    return True

def Find_output_type(infile: str):
    """This function finds the type of programme used to generate the output file.
    Currently it can recognize Orca, Dalton, Gaussian, and LSDalton

    Args:
        infile (str): Output file

    Returns:
        file_text (object): An object of the class that belongs to the singular output type
        input_type (str): The name of the programme
    """
    with open(infile,'r') as read:
        lines = read.readlines()[:10]
    if '* O   R   C   A *' in lines[4]: #File type = ORCA
        file_text = orca(infile)
        input_type = 'ORCA'

    if '*************** Dalton - An Electronic Structure Program ***************' in lines[3]:  #File type = DALTON
        file_text = dal(infile)
        input_type = 'DALTON'

    if 'Gaussian, Inc.  All Rights Reserved.' in lines[6]:  #File type = GAUSSIAN
        file_text = gaus(infile)
        input_type = 'GAUSSIAN'

    if '**********  LSDalton - An electronic structure program  **********' in lines[2]:    #File type = LSDALTON
        file_text = lsdal(infile)
        input_type = 'LSDALTON'

    del lines
    return file_text, input_type

def Data_Extraction(infile):
    Extracted_values = dict()

    # if not(quiet or suppressed):
    #     print(Barrier)
    #     print(f'Collecting data from {infile}')

    file_text, input_type = Find_output_type(infile)    #Determining data output type

    Extract_data(suppressed, Needed_Values, infile, file_text, input_type)  #Extracting data

    dict_keys = [*file_text.__dict__.keys()]
    collection_dict = dict()

    for i in dict_keys[1:]: #Collecting the data in dictionaries
        collection_dict[i] = file_text.__dict__[i]

    Extracted_values[infile] = collection_dict

    del file_text #Removing the file text from memory

    return Extracted_values

def Extract_data(suppressed: bool, Wanted_Values: dict, infile: str, file_text: dict, input_type: str):
    for i in Wanted_Values:
        try:
            method = getattr(type(file_text),i)
            method(file_text)
        except AttributeError:
            if not(suppressed):
                print(f'{infile}: {i} has not been implemented for {input_type}')

def Check_if_Implemented(input_file: str, Set_of_values: dict, Extracted_values: dict):
    for infile in input_file:
        for key in Set_of_values:
            for val in Set_of_values[key]:
                try:
                    Extracted_values[infile][val]
                except KeyError:
                    Extracted_values[infile][val] = ['Not implemented']

def Collect_and_sort_data(input_file: str, Set_of_values: dict, Extracted_values: dict):
    Final_arrays = dict()

    for key in Set_of_values:
        for val in Set_of_values[key]:
            Final_arrays[val] = []
            for infile in input_file:
                Final_arrays[val].append(Extracted_values[infile][val])
    return Final_arrays

def Downsizing_variable_arrays(Outputs: dict, Variable_arrays: dict, count: int, Final_arrays: dict):
    for item in Variable_arrays.items():
        if item[1] > 0:
            for val in Outputs[item[0]]:
                for file in range(0,count):
                    Final_arrays[val][file] = Final_arrays[val][file][0:item[1]]

def Create_Header(Header_text: dict, Set_of_values: dict, Final_arrays: dict):
    header = ['File']
    for key in Set_of_values.keys():
        for val in Set_of_values[key]:
            if len(Final_arrays[val][0]) > 1:
                for i in range(len(Final_arrays[val][0])):
                    header.append(f'{Header_text[val]} {i+1}')
            else:
                header.append(Header_text[val])
    return header

def Fill_output_array(Set_of_values: dict, array_input: dict, count: int, Final_arrays: dict, output_array: list):
    if count == 1:
        output_array[1,0] = array_input[0][0]
    else:
        output_array[1:,0] = np.array(np.concatenate(array_input))

    col = 1
    for key in Set_of_values.keys():
        for val in Set_of_values[key]:
            output_array[1:,col:col+len(np.array(Final_arrays[val][0]))] = np.array(Final_arrays[val])
            col += len(np.array(Final_arrays[val][0]))

def UVVIS_Spectrum(t: list, l: list, f: list, k: float, sigmacm: float):
    lambda_tot = np.zeros(len(t))
    for x in range(1,len(t)):
        lambda_tot[x] = sum((k/sigmacm)*f*np.exp(-4*np.log(2)*((1/t[x]-1/l)/(1E-7*sigmacm))**2))
    return lambda_tot

def Make_uvvis_spectrum(input_file: list, suppressed: bool, UVVIS_Spectrum: FunctionType, inv_cm_to_au: float, count: int, Final_arrays: dict):
    # A LOT OF PLOT SETUP
    rc('text', usetex=True)
    xlabel_font = ylabel_font = title_font = 16
    plt.rc('font', size=12) # x/y axis font size
    N=1000 # number of calculated points in curve
    NA=6.02214199*10**23 #avogadros number
    c=299792458 #speed of light
    e=1.60217662*10**(-19) #electron charge
    me=9.10938*10**(-31) #electron mass
    pi=math.pi
    epsvac=8.8541878176*10**(-12)
    sigmacm=0.4*8065.544
    k=(NA*e**2)/(np.log(10)*2*me*c**2*epsvac)*np.sqrt(np.log(2)/pi)*10**(-1)
        # PLOT SETUP DONE
    for file in input_file:
        filename = file.replace('.out','')
        plotname = f'{filename}-uvvis.{UVVIS}'
        title = filename.replace("_"," ")

        excitations = np.array([x for x in Extracted_Values[file]['exc_energies'] if x != 'NaN' and x != 'Not implemented'])
        oscillations = np.array([x for x in Extracted_Values[file]['osc_strengths'] if x != 'NaN' and x != 'Not implemented'])

        if len(excitations) == 0 and len(oscillations) == 0:
            if not(suppressed):
                print(f'Excitation energies and oscillator strengths have either not been implemented for this output type, or none were found in the file {filename}')
            continue
        if len(excitations) == 0:
            if not(suppressed):
                print(f'Excitation energies have either not been implemented for this output type, or none were found in the file {filename}')
            continue
        if len(oscillations) == 0:
            if not(suppressed):
                print(f'Oscillator strengths have either not been implemented for this output type, or none were found in the file {filename}')
            continue

        excitations = 1E7/(excitations/inv_cm_to_au)   #From cm^-1 to nm
        span = np.linspace(min(excitations)-20, max(excitations)+20, N, endpoint=True) # exctinction coefficient (wavelength range)

        graph = UVVIS_Spectrum(span, excitations, oscillations, k, sigmacm)
        plt.title(title)
        plt.plot(span, graph)
        plt.ylim((0,max(graph)*1.2))
        plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
        plt.xlabel('Wavelength $(nm)$', fontsize=xlabel_font)
        plt.ylabel('Extinction coefficient', fontsize=ylabel_font)
        plt.xticks(fontsize=16)
        plt.yticks(fontsize=16)
        plt.savefig(plotname, format=f'{UVVIS}', dpi=600)


#******************************* CODE *********************************


if __name__ == "__main__":
    Wanted_Values = [item[0] for item in RequestedArguments.items() if not(item[1] == None or item[1] == False)]
    Needed_Values = [item[0] for item in NeededArguments.items() if not(item[1] == None or item[1] == False)]
    Set_of_Values = dict(item for item in Outputs.items() if item[0] in Wanted_Values)

    ev_to_au = 0.036749405469679
    inv_cm_to_au = 1/219474.63068
    trans_const_fac = 1.5625517342018425307E+22 #Molar value assuming 1 bar standard pressure
    rot_lin_const = 20.83661793 #Assuming rigid, linear rotor and T>>Rotational temperature and rotational constant in GHz
    rot_poly_const = 168.5837766 #Assuming rigid, polyatomic rotor and T>>Rotational temperature and rotational constant in GHz
    vib_const = 3.157750419E+05 #Assuming harmonic oscillator and frequency in au
    gas_constant = 8.31446261815324E-03 # In kJ/(mol*K)
    s_trans_const = 0.3160965065 #Assuming 1 bar standard pressure and molar
    au_to_kJmol = 2625.4996394799
    Barrier = '\n**********************************************\n'

    # if quiet:
    #     print('')

    count = len(input_file)

    with Pool() as pool:
        Extracted_Values = pool.map(Data_Extraction, input_file)

    Extracted_Values = {key: value for dictionary in Extracted_Values for key, value in dictionary.items()} # Reformatting Extracted_values

    Input_Array = [[i] for i in Extracted_Values] # Creating array_input

    # if not(quiet or suppressed):
    #     print(Barrier)

    Check_if_Implemented(input_file, Set_of_Values, Extracted_Values)   #Finding functions not implemented

    for key_outer in Extracted_Values.keys():   # Turn everything into lists
        for key_inner in Extracted_Values[key_outer].keys():
            if type(Extracted_Values[key_outer][key_inner]) != list:
                Extracted_Values[key_outer][key_inner] = [Extracted_Values[key_outer][key_inner]]

    Final_arrays = Collect_and_sort_data(input_file, Set_of_Values, Extracted_Values)   #Collecting all values in arrays in a dictionary

    for key in Final_arrays.keys(): #Resizing arrays
        if type(Final_arrays[key]) == list:
            Resize(Final_arrays[key])

    if UVVIS:
        Make_uvvis_spectrum(input_file, suppressed, UVVIS_Spectrum, inv_cm_to_au, count, Final_arrays)

    Downsizing_variable_arrays(Outputs, Variable_arrays, count, Final_arrays)   #Fixing the size of variable size arrays

    Header = Create_Header(Header_text, Set_of_Values, Final_arrays)    #Creation of header row

    Output_Array = np.array([Header] * (count + 1), dtype=object)   #Create output array from header row

    Fill_output_array(Set_of_Values, Input_Array, count, Final_arrays, Output_Array)    #Filling the output array with the extracted data

#   ------------ IF CHOSEN PRINTS THE OUTPUT IN A CSV FILE ------------
#   ---------- ELSE THE RESULTS ARE DUMPED INTO THE TERMINAL ----------

    if CSV:
        np.savetxt('data.csv', Output_Array, delimiter=',', fmt='%s')
        print('Data has been saved in data.csv')
    else:
        print(Output_Array)

#EOF
