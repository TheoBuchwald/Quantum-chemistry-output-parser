%chk=CCSD_Ethanol_gaus.chk
%nprocshared=4
%mem=4GB
#p opt freq ccsd/cc-pvdz geom=connectivity polar

Ethanol.xyz

0 1
 C                  1.01110000    0.07708000   -0.05953000
 C                  2.52569000    0.07985000   -0.06640000
 O                  3.00581000    1.24365000   -0.72365000
 H                  0.62516000   -0.80571000    0.45780000
 H                  0.61937000    0.08556000   -1.08199000
 H                  0.62645000    0.97441000    0.43620000
 H                  2.91751000   -0.80185000   -0.58251000
 H                  2.91316000    0.08142000    0.95654000
 H                  2.66453000    1.22802000   -1.63407000

 1 2 1.0 4 1.0 5 1.0 6 1.0
 2 3 1.0 7 1.0 8 1.0
 3 9 1.0
 4
 5
 6
 7
 8
 9

