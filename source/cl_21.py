import numpy as np
from scipy.interpolate import interp2d
from scipy.integrate import simps
import selection_function21cm as sf
import matplotlib.pyplot as plt
import scipy.special
import sys
import matplotlib.ticker
from tools import *
from path import *
import derivative as dv

def set_cl_21 (tag, Yp_BBN):		# At the end, it would take z_m_list, w_list as arguments
	""" Construct object of class cl_21 """
	
	infile = path_data + '/file_names_{0}.txt'.format (tag)
	file_names = np.genfromtxt(infile, dtype="str")[0:]
	params_input = file_names[0]
	infile_syn = file_names[1]
	infile_new = file_names[2]
	infile_HYREC = file_names[3]
	
	params_list = np.loadtxt (params_input)[0:,]
	Cl = cl_21 (params_list, infile_HYREC, infile_syn, infile_new, Yp_BBN)
	Cl.test_run () 
	Cl.c_z ()
	return Cl
	

class cl_21 (object):
	def __init__ (self, params_list, infile_HYREC, infile_syn, infile_new, Yp_BBN = True):
		self.Yp_BBN = Yp_BBN
		self.params_list = params_list
		self.infile_syn = infile_syn
		self.infile_new = infile_new
		self.infile_HYREC = infile_HYREC


		# Load data from CLASS
		z = np.loadtxt(self.infile_syn)[0:,0]
		print ('z data', len(z))
		k = np.loadtxt(self.infile_syn)[0:,1]
		print ('k data', len(k))
		self.zlist2 = np.array(sorted(set(z)))
		self.klist2 = np.array(sorted(set(k)))
		self.number_of_z2 = len(self.zlist2)
		self.number_of_k2 = len(self.klist2)
		self.hubble_class = np.loadtxt(self.infile_syn)[0:self.number_of_z2,4][::-1]
		print ('hubble data', len(self.hubble_class))
		self.baryon = -np.loadtxt(self.infile_syn)[0:,2]
		self.baryon_dot = -np.loadtxt(self.infile_syn)[0:,3]

		As = (np.e**self.params_list[4])*10**(-10)
		print(As)
		n_s = self.params_list[5]
		k_pivot = 0.05
		self.k_list = np.logspace (-4,5, 5000)
		self.P_phi = As * (self.k_list/k_pivot)**(n_s-1.) * 2.*np.pi**2. / self.k_list**3.

		a_0 = 10.**-2./4.
		n = 10000
		scale_factor = np.logspace (np.log10(a_0), 0, n)
		scale_factor_reverse = scale_factor[::-1]
		self.redshift2 = 1./scale_factor_reverse - 1.
		hubble_class2 = np.interp (self.redshift2, self.zlist2, self.hubble_class)

		chi_class = []
		for i in range(len(hubble_class2)):
			chi_class.append (simps (1./hubble_class2[:i+1], self.redshift2[:i+1]))
		chi_class = np.array (chi_class)
		self.chi_class = np.interp (self.zlist2, self.redshift2, chi_class)
		
		# HYREC 
		self.z_HYREC = np.loadtxt(self.infile_HYREC)[0:,0]
		self.x_HYREC = np.loadtxt(self.infile_HYREC)[0:,1]
		Tm_Tr = np.loadtxt(self.infile_HYREC)[0:,2]
		T_cmb = 2.7255
		self.Tr = T_cmb*(1.+self.z_HYREC)
		self.Tm = self.Tr * Tm_Tr
		self.T_T = None
		self.T_H = None
		self.T_b = None
		if self.Yp_BBN == True:
			w = self.params_list[1]
			dN = self.params_list[9] - 3.046
			y = 0.2311 + 0.9502*w - 11.27*w**2 + dN*(0.01356 + 0.008581*w - 0.1810*w**2) + dN**2 * (-0.0009795 - 0.001370*w + 0.01746*w**2)
			self.Yp = y
		else:
			self.Yp = self.params_list[11]
		self.c = 299792458.
		self.Mpc_to_m = 3.0857*10.**22.
		self.eV_to_m_inv = 5076142.131979696
		self.h = self.params_list[10]
		self.Omega_b = self.params_list[1]/self.h**2
		self.rho_cr = 8.056*10.**-11. * self.h**2. # eV^4
		self.mp = 938.2720813*10.**6.  #eV
		self.me = 0.5109989461*10.**6.	#eV
		self.sigma_T = 6.6524587158 * 10. **-29.
		self.J_to_eV = 6.2415093433*10.**18.
		self.k_B = 8.613303*10.**-5. # eV/K
		self.wavelength = 0.21 #m
		self.E10 = 0.068															# K
		self.A10 = 2.85*10.**-15. / self.c											# /m	
		self.B10 = self.A10*(1.+1./(np.e**(self.E10/self.Tr)-1.))							# /m
		
		l_list = np.logspace(np.log10(2), np.log10(5000), 500)
		#l_list = np.logspace(np.log10(2), np.log10(10), 2)
		for i in range(len(l_list)):
			l_list[i] = int(l_list[i])
		l_list = sorted(set(l_list))
		l_list[-1] += 1.
		self.l_list = np.array (l_list)


	def test_run (self):
		""" Calculate coefficients of 21 cm fluctuations (linear terms) """

		zlist = self.zlist2.copy ()
		hubble_class = self.hubble_class.copy ()
	
		z = self.z_HYREC.copy ()
		x = self.x_HYREC.copy ()

		hubble = np.interp (z[::-1], zlist, hubble_class)[::-1]
		n_H = (1-self.Yp)*self.rho_cr*self.Omega_b/self.mp*(1+z)**3 		# eV^3
		n_H *= self.eV_to_m_inv**3											# /m^3
		kappa = 3.1*10**-11 *self.Tm**0.357 * np.e**(-32/self.Tm) * 10**-6 			# m^3/s
		kappa /= self.c														# m^2
		wavelength = self.wavelength	
		C10 = n_H*kappa														# /m
		C01 = 3*np.e**(-self.E10/self.Tm)*C10											# /m
		I_nu = 2*self.k_B*self.Tr/wavelength**2									# eV/m^2
		I_nu *= self.eV_to_m_inv											# /m^3
	
		hubble = hubble/self.Mpc_to_m
		Ts = self.Tr + (self.Tm-self.Tr)*C10/(C10+self.A10*self.Tm/self.E10)
	
		a = kappa*n_H
		b = self.A10*self.Tr/self.E10
		D = (1+z)**-1 * 3*self.E10/(32*np.pi)*1/4*self.Yp*wavelength**3*self.A10*n_H**2*kappa/(hubble*self.Tm*(kappa*n_H+self.A10*self.Tr/self.E10))
		C = (1+z)**-1 * 3*self.E10/(32*np.pi)*(1-x)*wavelength**3*self.A10
		T_b = -C*self.E10*kappa*n_H**2*(self.Tr-self.Tm)/(hubble*(self.E10*kappa*n_H + self.A10*self.Tr)*self.Tm)
		T_H = -C*self.E10*kappa*n_H**2*(self.E10*kappa*n_H+2*self.A10*self.Tr)*(self.Tr-self.Tm)/(hubble*(self.E10*kappa*n_H+self.A10*self.Tr)**2*self.Tm)
		T_T = (0.357*C*self.E10*kappa*n_H**2*(-89.6359*self.A10*self.Tr**2+89.6359*self.A10*self.Tr*self.Tm+2.80112*self.E10*kappa*n_H*self.Tr*self.Tm+1.80112*self.A10*self.Tr**2*self.Tm+self.A10*self.Tr*self.Tm**2))/(hubble*(self.E10*kappa*n_H+self.A10*self.Tr)**2*self.Tm**2)
		T_HH = - self.A10**2*C*self.E10*kappa*n_H**2*self.Tr**2*(self.Tr-self.Tm)/(hubble*(self.E10*kappa*n_H+self.A10*self.Tr)**3*self.Tm)
		T_HT = (0.714*C*self.E10*kappa*n_H**2*(-89.6359*self.A10**2*self.Tr**3+1.40056*self.E10**2*kappa**2*n_H**2*self.Tr*self.Tm+89.6359*self.A10**2*self.Tr**2*self.Tm+4.20168*self.A10*self.E10*kappa*n_H*self.Tr**2*self.Tm+1.80112*self.A10**2*self.Tr**3*self.Tm+self.A10**2*self.Tr**2*self.Tm**2))/(hubble*(self.E10*kappa*n_H+self.A10*self.Tr)**3*self.Tm**2)
		T_TT = (C*self.E10*kappa*n_H**2*(512*self.A10*self.E10*kappa*n_H*self.Tr**2-512*self.A10**2*self.Tr**3-512*self.A10*self.E10*kappa*n_H*self.Tr*self.Tm+512*self.A10**2*self.Tr**2*self.Tm+75.424*self.A10*self.E10*kappa*n_H*self.Tr**2*self.Tm+52.576*self.A10**2*self.Tr**3*self.Tm-43.424*self.A10*self.E10*kappa*n_H*self.Tr*self.Tm**2-self.E10**2*kappa**2*n_H**2*self.Tr*self.Tm**2-20.576*self.A10**2*self.Tr**2*self.Tm**2-1.40078*self.A10*self.E10*kappa*n_H*self.Tr**2*self.Tm**2-0.528225*self.A10**2*self.Tr**3*self.Tm**2-1.11022*10**-16*self.E10**2*kappa**2*n_H**2*self.Tm**3-0.242225*self.A10*self.E10*kappa*n_H*self.Tr*self.Tm**3-0.114776*self.A10**2*self.Tr**2*self.Tm**3))/(hubble*(self.E10*kappa*n_H+self.A10*self.Tr)**3*self.Tm**3)

		self.T_T = T_T
		self.T_H = T_H
		self.T_b = T_b
		
		
		return z, T_T, T_H, T_b

	def c_z (self):
		""" Calculate C1(z) which is defiend as T_{Tgas} = C1(z) T_{b} """
		# Interpolate HyRec table
		ALPHA_FILE = default + "/class_syn/hyrec/Alpha_inf.dat"
		RR_FILE = default + "/class_syn/hyrec/R_inf.dat"
		NTR = 100
		NTM = 40
		TR_MIN = 0.004
		TR_MAX = 0.4
		TM_TR_MIN = 0.1
		TM_TR_MAX = 1.0

		logTR_tab = maketab (np.log(TR_MIN), np.log(TR_MAX), NTR)
		TM_TR_tab = maketab (TM_TR_MIN, TM_TR_MAX, NTM)
		DlogTR = logTR_tab[1] - logTR_tab[0]
		DTM_TR = TM_TR_tab[1] - TM_TR_tab[0]

		logR2p2s_tab = np.log(np.loadtxt (RR_FILE)[0:])
		logAlpha_tab = np.zeros([2,NTM,NTR])
		for i in range(NTR):
			Alpha1 = np.loadtxt(ALPHA_FILE)[i*NTM:(i+1)*NTM,0]
			Alpha2 = np.loadtxt(ALPHA_FILE)[i*NTM:(i+1)*NTM,1]
			logAlpha_tab[0,:,i] = np.log(Alpha1)
			logAlpha_tab[1,:,i] = np.log(Alpha2)

		hubble_class = self.hubble_class[::-1].copy ()

		z = self.z_HYREC.copy ()
		x = self.x_HYREC.copy ()

		new_z = np.linspace(1000,0,20000)
		x = np.interp (new_z[::-1], z[::-1], x[::-1])[::-1]
		hubble = np.interp (new_z[::-1], self.zlist2, hubble_class[::-1])[::-1]
		Tr = np.interp (new_z[::-1], z[::-1], self.Tr[::-1])[::-1]
		Tm = np.interp (new_z[::-1], z[::-1], self.Tm[::-1])[::-1]
		a_r = 4*5.670373 * 10**-8 * self.J_to_eV	#eV m^-2 s^-1 K^-4
		x_He = self.Yp/(4*(1-self.Yp))
		gamma = (8*self.sigma_T*a_r*Tr**4)/(3*(1+x_He+x)*self.me) *x	# s^-1
		#gamma /= self.c		# m^-1
		Tr *= self.k_B
		Tm *= self.k_B
		Tm_Tr = Tm/Tr
		
		#plt.figure(10)
		#plt.loglog (new_z+1,(Tr-Tm)/Tm)
		#plt.title (r'$(T_r-T_m)/T_m$')
		#plt.savefig ('tr-tm_tm.pdf')

		hubble = hubble * self.c / self.Mpc_to_m
		hubble_class = hubble_class *self.c / self.Mpc_to_m

		n_H = (1-self.Yp)*self.rho_cr*self.Omega_b/self.mp*(1+new_z)**3		# eV^3
		n_H *= self.eV_to_m_inv**3											# /m^3
		n_H *= 1e-6
		L2s1s = 8.2206

		Beta1 = []
		Beta2 = []
		Alpha1 = []
		Alpha2 = []
		for i in range(len(new_z)):
			Alpha, Beta, R2p2s = interpolate_rates (Tr[i], Tm_Tr[i], logAlpha_tab,logR2p2s_tab, DTM_TR, DlogTR)
			Beta1.append (Beta[0])
			Beta2.append (Beta[1])
			Alpha1.append (Alpha[0])
			Alpha2.append (Alpha[1])
		AB = np.array(Alpha1) + np.array(Alpha2)
		Beta_ = np.array(Beta1) + np.array(Beta2)
		RLya = 4.662899067555897e15 *hubble /n_H/(1.-x)
		#RLya = 4.662899067555897e15 *(Hubble + theta_b/3.) /n_H/(1.-x)
		C = (3*RLya + L2s1s)/(3*RLya + L2s1s + 4*Beta_)
		dlogC_dlogRLya = -dv.derivative (np.log(RLya), np.log(C))

		x_dot = -C*AB*n_H*x**2

		T21 = []
		T21_2 = []
		redshift_distortion = []
		redshift = []
		wavenumber = []
		zz = np.linspace(400,0,1000)
		T_T = np.interp(zz[::-1], self.z_HYREC[::-1], self.T_T[::-1])[::-1]
		T_H = np.interp(zz[::-1], self.z_HYREC[::-1], self.T_H[::-1])[::-1]
		T_b = np.interp(zz[::-1], self.z_HYREC[::-1], self.T_b[::-1])[::-1]
			
		#for i in [self.number_of_k2-1]:
		#for i in range(self.number_of_k2):
		for i in [0,100,200,300,400,500,600,700]:
			kk = self.klist2[::-1][i]
			print (i, kk)
			b = self.baryon[i*self.number_of_z2:(i+1)*self.number_of_z2]
			b = np.interp (new_z[::-1], self.zlist2, b[::-1])[::-1]
			b_dot = self.baryon_dot[i*self.number_of_z2:(i+1)*self.number_of_z2]*(-hubble_class)
			b_dot = np.interp (new_z[::-1], self.zlist2, b_dot[::-1])[::-1] 
			theta_b = -b_dot*(1+new_z)
	
			delta_x = [0]
			delta_Tm = [0]
			delta_x_ini = 0
			delta_Tm_ini = 0
			for i in range(len(new_z)-1):
				dz = new_z[i]-new_z[i+1]
				Alpha, Beta, R2p2s = interpolate_rates (Tr[i], Tm_Tr[i], logAlpha_tab,logR2p2s_tab, DTM_TR, DlogTR)
	
	
				dlogAB_dlogTm = []
				#for j in range(len(new_z)):
				for j in [i-1, i, i+1]:
					Alpha2, _, _ = interpolate_rates (Tr[i], Tm_Tr[j], logAlpha_tab,logR2p2s_tab,DTM_TR, DlogTR)
					#Alpha2, _, _ = interpolate_rates (TR[j], TM_TR[j], logAlpha_tab,logR2p2s_tab)
					dlogAB_dlogTm.append (np.log(Alpha2[0]+Alpha2[1]))
				dlogAB_dlogTm = np.array (dlogAB_dlogTm)
				#dlogAB_dlogTM = dv.derivative (TM[::-1], dlogAB_dlogTM[::-1])[::-1]
				dlogAB_dlogTm = dv.derivative ([np.log(Tm[i-1]), np.log(Tm[i]), np.log(Tm[i+1])][::-1], dlogAB_dlogTm[::-1])[::-1]
	
				ddelta_Tm_dz = -1./(hubble[i]*(1.+new_z[i])) * ( gamma[i]*( (Tr[i]-Tm[i])/Tm[i]*delta_x_ini - Tr[i]/Tm[i]*delta_Tm_ini) + 2./3.*(1.+new_z[i])*b_dot[i])
				delta_Tm_ini -= ddelta_Tm_dz*dz
				delta_Tm.append (delta_Tm_ini)

				ddelta_x_dz = -1./(hubble[i]*(1.+new_z[i]))*x_dot[i]/x[i] * (delta_x_ini + b[i] + dlogAB_dlogTm[1] * delta_Tm_ini + dlogC_dlogRLya[i]*(theta_b[i]/(3.*hubble[i])-b[i]))
				delta_x_ini -= ddelta_x_dz*dz
				delta_x.append (delta_x_ini)
				print (delta_x_ini, b[i], dlogAB_dlogTm[1], dlogC_dlogRLya[i]*(theta_b[i]/(3.*hubble[i])-b[i]))
			#plt.figure(1)
			#fig = plt.subplot(1,1,1)
			#plt.xscale('log', basex=2)
			#plt.plot(1+new_z, delta_Tm*(1+new_z), label = r'Without $\delta_{x_e}$')
			#plt.xlabel (r'$1+z$', size = 15)
			#plt.ylabel (r'$\delta_{T_\mathrm{gas}} (1+z)$', size = 15)
			#fig.set_xticks([5,10,50,100,500])
			#fig.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
			#plt.legend ()
			#plt.show()
			new_delta_x = -np.array(delta_x)
			#plt.figure(1)
			#plt.loglog (new_z+1, new_delta_x, label = '{}'.format(kk))
			#plt.figure(2)
			#plt.loglog (new_z+1, delta_Tm, label = '{}'.format(kk))
			#plt.figure(3)
			#plt.loglog (new_z+1, b, label = '{}'.format(kk))
			delta_Tm = np.interp(zz[::-1], new_z[::-1], delta_Tm[::-1])[::-1]

			transfer_21 = T_H 
			transfer_21_2 = T_T * delta_Tm
			distortion = T_b
			T21 += list(transfer_21)
			T21_2 += list(transfer_21_2)
			redshift_distortion += list(distortion)
			redshift += list(zz)
			wavenumber += list(np.ones(len(zz))*kk)
		plt.figure (1)
		plt.title (r'$-\delta_{x_e}$')
		plt.legend (prop={'size':10})
		plt.savefig ('delta_x_e.pdf')
		plt.figure (2)
		plt.title (r'$\delta_{T_m}$')
		plt.legend (prop={'size':10})
		plt.axis([1,10000,10**-8,10**5])
		plt.savefig('T_m.pdf')
		plt.figure (3)
		plt.legend (prop={'size':10})
		plt.title (r'$\delta_b$')
		plt.savefig('b.pdf')
		
		self.T21 = np.array (T21)
		self.T21_2 = np.array (T21_2)
		self.redshift_distortion = np.array (redshift_distortion)
		self.zlist = np.array (redshift)
		wavenumber = np.array (wavenumber)
		self.zz = zz	
	
		data = np.column_stack (( self.zlist, self.T21, self.T21_2 ))
		np.savetxt('transfer_21.txt', data, fmt = '%1.6e')
		

	def cl21T (self, z_m, w):
		""" Calculate cross-correlation functions of ISW and 21 cm """

		z, sel, _ = sf.run_sel (w, z_m)
		
		chi_class_local = np.interp (z, self.zlist2, self.chi_class)
		hubble_local = np.interp (z, self.zlist2, self.hubble_class)
		dphidz = np.loadtxt(self.infile_new)[0:,5]
		T_dphidz = []
		T_baryon = []
		delta_21 = []
		delta_21_2 = []
		for i in range(self.number_of_k2):
			p = dphidz[self.number_of_z2*i:self.number_of_z2*(i+1)][::-1]
			T_dphidz.append (p)
			bb = self.baryon[self.number_of_z2*i:self.number_of_z2*(i+1)][::-1]
			T_baryon.append (bb)
				
			pp = self.T21[len(self.zz)*i:len(self.zz)*(i+1)][::-1]
			delta_21.append (pp)
			ppp = self.T21_2[len(self.zz)*i:len(self.zz)*(i+1)][::-1]
			delta_21_2.append (ppp)
	
		zz = self.zz[::-1].copy ()
		
		T_dphidz = interp2d (self.zlist2, self.klist2, T_dphidz[::-1], kind = 'cubic')
		T_baryon = interp2d (self.zlist2, self.klist2, T_baryon[::-1], kind = 'cubic')
		delta_21 = interp2d (zz, self.klist2, delta_21[::-1], kind = 'cubic')
		delta_21_2 = interp2d (zz, self.klist2, delta_21_2[::-1], kind = 'cubic')

		#delta_21 = self.T21[::-1].copy ()
		cl_list = []
		for l in self.l_list:
			print (l)
			kk = (l+1./2.)/chi_class_local
			P_phi_local = np.interp (kk, self.k_list, self.P_phi)
			
			transfer_21 = []
			transfer_dphidz = []
			for j in range(len(kk)):
				T = delta_21 (z[j], kk[j])[0]			# not dependent on k, though
				bb = T_baryon (z[j], kk[j])[0]
				T_2 = delta_21_2 (z[j], kk[j])[0]
				transfer_21.append (T*bb+T_2)
				p = T_dphidz (z[j], kk[j])[0]
				transfer_dphidz.append (p)
			transfer_21 = np.array (transfer_21)
			transfer_dphidz = np.array (transfer_dphidz)
			
			integrand = -2 * P_phi_local * sel * transfer_21 * transfer_dphidz * hubble_local / chi_class_local**2
			cl = simps (integrand, z)
			cl_list.append (cl)
	
		cl_list = np.array (cl_list)
		
		return cl_list



	def cl21 (self, z_m, w):
		""" Calculate 21 cm auto-correlation functions """
		
		z, sel1, _ = sf.run_sel (w[0], z_m[0])
		z, sel2, _ = sf.run_sel (w[1], z_m[1])

		chi_class_local = np.interp (z, self.zlist2, self.chi_class)
		hubble_local = np.interp (z, self.zlist2, self.hubble_class)
		
		T_baryon = []
		delta_21 = []
		delta_21_2 = []
		for i in range(self.number_of_k2):
			bb = self.baryon[self.number_of_z2*i:self.number_of_z2*(i+1)][::-1]
			T_baryon.append (bb)
		
			pp = self.T21[len(self.zz)*i:len(self.zz)*(i+1)][::-1]
			delta_21.append (pp)
			ppp = self.T21_2[len(self.zz)*i:len(self.zz)*(i+1)][::-1]
			delta_21_2.append (ppp)
		
		zz = self.zz[::-1].copy ()
		
		T_baryon = interp2d (self.zlist2, self.klist2, T_baryon[::-1], kind = 'cubic')
		delta_21 = interp2d (zz, self.klist2, delta_21[::-1], kind = 'cubic')
		delta_21_2 = interp2d (zz, self.klist2, delta_21_2[::-1], kind = 'cubic')

		cl_list = []
		for l in self.l_list:
			print (l)
			kk = (l+1./2.)/chi_class_local
			P_phi_local = np.interp (kk, self.k_list, self.P_phi)
			
			transfer_21 = []
			for j in range(len(kk)):
				T = delta_21 (z[j], kk[j])[0] 
				bb = T_baryon (z[j], kk[j])[0]
				T_2 = delta_21_2 (z[j], kk[j])[0]
				transfer_21.append (T*bb + T_2)
			transfer_21 = np.array (transfer_21)
	
			integrand = P_phi_local * sel1 * sel2 * transfer_21**2 * hubble_local /chi_class_local**2
			cl = simps (integrand, z)
			cl_list.append (cl)
	
		cl_list = np.array (cl_list)
		
		return cl_list


	def cl21_exact (self, z_m, w):
		
		z, sel, _ = sf.run_sel (w, z_m)

		chi_class_local = np.interp (z, self.redshift2, self.chi_class)
		hubble_local = np.interp (z, self.redshift2, self.hubble_class)
		
		#T21 = self.T21[0:self.number_of_z][::-1]
		#redshift_distortion = self.redshift_distortion[0:self.number_of_z][::-1]
		redshift_distortion = self.redshift_distortion[0:len(self.zz)][::-1]
		
		T_baryon = []
		delta_21 = []
		delta_21_2 = []
		distortion = []
		for i in range(self.number_of_k2):
			bb = self.baryon[self.number_of_z2*i:self.number_of_z2*(i+1)][::-1]
			T_baryon.append (bb)
		
			pp = self.T21[len(self.zz)*i:len(self.zz)*(i+1)][::-1]
			delta_21.append (pp)
			ppp = self.T21_2[len(self.zz)*i:len(self.zz)*(i+1)][::-1]
			delta_21_2.append (ppp)
		
			distortion.append (redshift_distortion*bb)
		
		zz = self.zz[::-1].copy ()
		
		T_baryon = interp2d (self.zlist2, self.klist2, T_baryon[::-1], kind = 'cubic')
		delta_21 = interp2d (zz, self.klist2, delta_21[::-1], kind = 'cubic')
		delta_21_2 = interp2d (zz, self.klist2, delta_21_2[::-1], kind = 'cubic')
		distortion = interp2d (zz, self.klist2, distortion[::-1], kind = 'cubic')
		
		"""
		delta_21 =[]
		distortion = []
		for i in range(number_of_k):
			bb = baryon[number_of_z*i:number_of_z*(i+1)][::-1]
				
			#d = T21[number_of_z*i:number_of_z*(i+1)][::-1]
			d = T21[number_of_z*(number_of_k-1):number_of_z*number_of_k][::-1]
			d = d*bb
			delta_21.append (d)
			d = redshift_distortion[number_of_z*i:number_of_z*(i+1)][::-1]
			d = d*bb
			distortion.append (d)
		delta_21 = interp2d (zlist, klist, delta_21[::-1], kind = 'cubic')
		distortion = interp2d (zlist, klist, distortion[::-1], kind = 'cubic')
		"""
		
		cl_list = []
		for l in l_list:
			print (l)
			alpha_list = []
			beta_list = []
			
			#P0_list = []
			#P0v_list = []
			#Pv_list = []
			for j in range(len(self.k_list2)):
				jl = scipy.special.spherical_jn (int(l), self.k_list2[j]*chi_class_local)
				jl_2 = scipy.special.spherical_jn (int(l), self.k_list2[j]*chi_class_local, 2) 
				
				T = delta_21 (z, self.k_list2[j])[0]
				T_2 = delta_21_2 (z, self.k_list2[j])[0]
				bb = T_baryon (z, self.k_list2[j])[0]

				distor = distortion (z, self.k_list2[j])[0]
				alpha = simps (jl*sel*(T*bb + T_2), z)
				beta = simps (jl_2*sel*distor, z)
				
				#transfer_21 = delta_21 (z_m, k_list[j])[0]
				#distor = distortion (z_m, k_list[j])[0]
				#alpha = simps (jl*sel, redshift)
				#beta = simps (jl_2*sel, redshift)
				alpha_list.append (alpha)
				beta_list.append (beta)
			
				#P0 = P_phi[j]*transfer_21**2
				#P0v = P_phi[j]*transfer_21*distor
				#Pv = P_phi[j]*distor**2
				#P0_list.append (P0)
				#P0v_list.append (P0v)
				#Pv_list.append (Pv)
	
			alpha_list = np.array (alpha_list)
			beta_list = np.array (beta_list)
			#P0_list = np.array (P0_list)
			#P0v_list = np.array (P0v_list)
			#Pv_list = np.array (Pv_list)
	
			integrand = 2/np.pi * self.P_phi * self.k_list2**2 * (alpha_list**2 - 2*alpha_list*beta_list + beta_list**2)
			#integrand1 = 2/np.pi * k_list**2 * (P0_list*alpha_list**2 + P0v_list*2*alpha_list*beta_list + Pv_list*beta_list**2)
			#integrand1 = 2/np.pi * P_phi * k_list**2 * alpha_list**2
			#integrand2 = 2/np.pi * P_phi * k_list**2 * 2*alpha_list*beta_list 
			#integrand3 = 2/np.pi * P_phi * k_list**2 * beta_list**2
			
			cl = simps (integrand, self.k_list2)
			#cl_ab = simps (integrand2, k_list)
			#cl_bb = simps (integrand3, k_list)
			
			cl_list.append (cl)
			#cl_list_ab.append (cl_ab)
			#cl_list_bb.append (cl_bb)
	
		cl_list = np.array (cl_list)
		#cl_list_ab = np.array (cl_list_ab)
		#cl_list_bb = np.array (cl_list_bb)
		print (cl_list)
		
		return cl_list

	def cl21_sharp (self, z_m, w):
		
		z, sel, _ = sf.run_sel (w, z_m)

		chi_class_local = np.interp (z, self.redshift2, self.chi_class)
		hubble_local = np.interp (z, self.redshift2, self.hubble_class)
		
		dphidz = np.loadtxt(self.infile_new)[0:,5]
		T_baryon = []
		for i in range(self.number_of_k2):
			bb = self.baryon[self.number_of_z2*i:self.number_of_z2*(i+1)][::-1]
			T_baryon.append (bb)
		T_baryon = interp2d (self.zlist2, self.klist2, T_baryon[::-1], kind = 'cubic')
		
		"""
		delta_21 =[]
		distortion = []
		for i in range(number_of_k):
			bb = self.baryon[number_of_z*i:number_of_z*(i+1)][::-1]
			d = self.T21[number_of_z*(number_of_k-1):number_of_z*number_of_k][::-1]
			d = d*bb
			delta_21.append (d)
			d = self.redshift_distortion[number_of_z*i:number_of_z*(i+1)][::-1]
			d = d*bb
			distortion.append (d)
		delta_21 = interp2d (zlist, klist, delta_21[::-1], kind = 'cubic')
		distortion = interp2d (zlist, klist, distortion[::-1], kind = 'cubic')
		"""
		
		delta_21 = self.T21[0:self.number_of_z][::-1]
		distortion = self.redshift_distortion[0:self.number_of_z][::-1]

		chi_class_z_m = np.interp (z_m, z, chi_class_local) 
		cl_list = []
		for l in l_list:
			print (l)
			jl = scipy.special.spherical_jn (int(l), self.k_list*chi_class_z_m)
			jl_2 = scipy.special.spherical_jn (int(l), self.k_list*chi_class_z_m, 2) 
			
			transfer_21 = []
			distor = []
			
			transfer_21_z_m = np.interp (z_m, self.zlist, delta_21)
			distor_z_m = np.interp (z_m, self.zlist, distortion)
			
			for j in range(len(self.k_list)):
				bb = T_baryon (z_m, k_list[j])[0]
				transfer_21.append (transfer_21_z_m*bb)
				distor.append (distor_z_m*bb)
				
			transfer_21 = np.array (transfer_21)
			distor = np.array (distor)
			
			integrand = 2/np.pi * self.P_phi * self.k_list**2 * (transfer_21**2*jl**2 + 2*transfer_21*distor*jl*jl_2 + distor**2*jl_2**2)
			cl = simps (integrand, self.k_list)
			cl_list.append (cl)
	
		cl_list = np.array (cl_list)
		print (cl_list)
		return cl_list

