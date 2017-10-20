import numpy as np
import os
from subprocess import call
from path import *
from updateparams import *

def run (params_list, tag, cross = True):
	
	
	#Delete unnecessary output file in CLASS
	os.system ("rm class_syn/output/*")
	os.system ("rm class_new/output/*")

	# Run CLASS (syncronous gauge)
	os.chdir (path_CLASS_syn)
	oldfile = "params_prac_.ini"
	newfile = "params_prac2_.ini"
	clfile = "params_prac_cl.dat"
	clout = path_data + "/params_prac_cl_" + tag + ".dat"
	setparamsfile_CLASS (params_list, oldfile, newfile)
	call ('./class {0}'.format (newfile), shell = True)	
	os.chdir ("output")
	outfile_syn = path_data + "/delta_syn_{0}.dat".format (tag)
	os.system ("cp delta.dat {0}".format (outfile_syn))
	os.system ("cp {0} {1}".format (clfile, clout))
	if tag == "0":
		cl_out = path_result + "/cl_" + tag + ".dat"
		os.system ("cp params_prac_cl.dat {1}".format(tag, cl_out))

	os.system ("rm *")
	os.chdir ("../")
	os.chdir ("../")
	
	if cross == True:
		# Run CLASS (newtonian gauge)
		os.chdir (path_CLASS_new)
		oldfile = "params_prac_.ini"
		newfile = "params_prac2_.ini"
		setparamsfile_CLASS (params_list, oldfile, newfile)
		call ('./class  {0}'.format (newfile), shell = True)	
		os.chdir ("output")
		outfile_new = path_data + "/delta_new_{0}.dat".format (tag)
		os.system ("cp delta.dat {0}".format (outfile_new))
		#os.system("cp delta.dat {0}/delta_new.dat".format (path_data))
		os.system ("rm *")
		os.chdir ("../")
		os.chdir ("../")
	
	os.chdir (path_HYREC)
	# Run HYREC	
	oldfile = "input_prac.dat"
	newfile = "input_prac2.dat"
	outfile_HYREC = "output_prac_{0}.dat".format (tag)
	setparamsfile_HYREC (params_list, oldfile, newfile)
	os.system ("gcc -lm -O3 hyrectools.c helium.c hydrogen.c history.c hyrec.c -o hyrec")
	call ("./hyrec < {0} > {1}".format (newfile, outfile_HYREC), shell = True)	
	os.chdir ("../")
	
	'''
	# Calculate 21cm fluctuation coefficients
	outfile_21 = path_data + "/transfer21.txt"
	os.system ("python c_z.py {0} {1} {2}".format (outfile_syn, outfile_HYREC, "transfer21.txt"))
	os.system ("cp transfer21.txt {0}".format (outfile_21))
	os.system ("rm transfer21.txt")
	'''
	
	# Calculate C_l
	outfile_HYREC = "HYREC/output_prac.dat"
	if cross == True:
		outfile_cl21 = path_result + "/cl21T_{}.txt".format (tag)
		file_names = np.array ([params_input, outfile_syn, outfile_new, outfile_HYREC, outfile_cl21])
		np.savetxt (path_data + '/file_names_{0}.txt'.format (tag), file_names, fmt="%s")
		#os.system ("python run_cl21.py {0} {1} {2} {3} {4}".format (outfile_syn, outfile_HYREC, outfile_cl21, params_input, outfile_new))
	else:
		outfile_cl21 = path_result + "/cl2121_{}.txt".format (tag)
		file_names = np.array ([params_input, outfile_syn, 'None', outfile_HYREC, outfile_cl21])
		np.savetxt (path_data + '/file_names_{0}.txt'.format (tag), file_names, fmt="%s")
		#os.system ("python run_cl21.py {0} {1} {2} {3} {4}".format (outfile_syn, outfile_HYREC, outfile_cl21, params_input, 'None'))
		
# Load cosmological parameters
#params_list = np.loadtxt (params_input)[0:,]
#tag = "baryon"
#run (params_list, tag)
#run (params_list, '0')
