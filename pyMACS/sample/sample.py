import numpy as np 
from .parseCif import parseCIF
from .import_NIST_table import import_NIST_table
import os
import shutil  
import lmfit 
from lmfit import Model,Parameters

class Sample(object):
	'''
	The purpose of this class is to perform operations related to intrinsic sample properties that will ultimately be simulated. 

	Parameters:

	a,b,c  - Lattice parameters in Ang 
	alpha,beta,gamma - Unit cell angles 
	name - the name of the sample
	astar,bstar,cstar - numpy arrays, Reciprocal lattice vectors(calculated)
	avec, bvec, cvec - real space vectors of the unit cell (calculated)
	cell_vol - unit cell volume (calculated)
	cell_vol_recip - volume of reciprocal unit cell (calculated)
	sample_shape - allowed values are 'cylinder' and 'box'
	sample_diameter_d - diameter of cylinder, in m
	sapmle_tilt - tilt from vertical axis in deg, 0 being vertical and axis is the x-axis (perpendicular to beam)
	sample_length - length of cylinder, in m 
	sample_widx - box width, in m 
	sample_widy - box width in beam direction in m 
	sample_widz - box height in m 
	ciffile - preferred method to initialize the sample.
	b_arr - scattering lengths of the ions in the sample. Can also be extracted from NIST tables, or use a custom value in the case of isotope enhancement

 
	'''

	def __init__(self,a=6.28,b=6.28,c=6.28,alpha=90.0,beta=90.0,gamma=90.0,cell_vol=None,V_recip=None,name='default_sample',sample_shape='cylinder',sample_diameter_d=0.02,sample_tilt=60.0,\
		sample_length=0.04,sample_widx=0.003,sample_widy=0.003,sample_widz=0.003,symm_ops=None,space_group=None,ciffile=None,laufile=None,customlaufile=None,b_arr=False,orient_u=[1,1,0],orient_v=[0,0,1],orient_w=[1,0,1],\
		rho_abs_fu=False,rho_abs=False,sigma_inc=False,sample_mosaic=30.0,delta_d=5E-4,abs_dict=False,crystal_axis_xrot=45.0,crystal_axis_yrot=0.0,crystal_axis_zrot=-15.0):
		nist_data = os.path.dirname(__file__)+'/nist_scattering_table.txt' #Included in this directory
		if b_arr==False:
			scatt_dict = import_NIST_table(nist_data)
			self.b_arr=False
			self.scatt_dict=scatt_dict
		else:
			scatt_dict=b_arr
			self.b_arr=True
			self.scatt_dict=b_arr
		if ciffile is None:
			print("WARNING: No cif file found. Importing sample parameters from a cif file is the preferred method to initialize the sample. Defaulting to TiO2.cif")
			ciffile=os.path.dirname(__file__+'/TiO2.cif')
			self.ciffile=ciffile
		
		if ciffile is not None:
			if type(ciffile) != str:
				print('Need to use a string for cif file.')
			cif_dict = parseCIF(ciffile)
			cif_obj =cif_dict
			self.ciffile=ciffile

			#Now can initialize all of the below parameters

		a = float(cif_obj['_cell_length_a'].split('(')[0])
		b = float(cif_obj['_cell_length_b'].split('(')[0])
		c = float(cif_obj['_cell_length_c'].split('(')[0])
		alpha = float(cif_obj['_cell_angle_alpha'].split('(')[0])
		beta = float(cif_obj['_cell_angle_beta'].split('(')[0])
		gamma = float(cif_obj['_cell_angle_gamma'].split('(')[0])
		cell_vol = float(cif_obj['_cell_volume'].split('(')[0])
		#Generate reciprocal lattice 
		alpha_r = alpha*np.pi/180.0
		beta_r = beta*np.pi/180.0
		gamma_r = gamma*np.pi/180.0
		avec = np.array([a,0.0,0.0])
		bvec = np.array([b*np.cos(gamma_r),b*np.sin(gamma_r),0])
		cvec = np.array([c*np.cos(beta_r),c*(np.cos(alpha_r)-np.cos(beta_r)*np.cos(gamma_r))/(np.sin(gamma_r)),\
			c*np.sqrt(1.0-np.cos(beta_r)**2-((np.cos(alpha_r)-np.cos(beta_r)*np.cos(gamma_r))/np.sin(gamma_r))**2)])
		V_recip=np.dot(avec,np.cross(bvec,cvec))
		astar = 2.0*np.pi*np.cross(bvec,cvec)/V_recip
		bstar = 2.0*np.pi*np.cross(cvec,avec)/V_recip
		cstar = 2.0*np.pi*np.cross(avec,bvec)/V_recip

		#The parameter that defines the space group is often inconsistent. Find something that contains the string
		# '_space_group' but not 'xyz'
		space_group = 'Undefined'
		for i in range(len(cif_obj)):
			key_str = cif_obj.keys()[i]
			if (('_space_group' in key_str) or ('_space_group_name_h-m' in key_str)) and ('xyz' not in key_str) and ('number' not in key_str) and ('symop_id' not in key_str):
				#found the key to the space group in the dictionary.
				space_key = key_str 
				space_group = cif_obj[key_str]
				continue 

		#Below are crystallographic properties
		self.avec = avec 
		self.bvec = bvec 
		self.cvec = cvec 
		self.astar_vec = astar
		self.bstar_vec = bstar
		self.cstar_vec = cstar
		self.a = a 
		self.b = b 
		self.c = c 
		self.alpha= alpha 
		self.beta = beta 
		self.gamma = gamma 
		self.alpha_star = alpha_r 
		self.beta_star = beta_r 
		self.gamma_star = gamma_r 
		self.cell_vol = cell_vol
		self.astar = np.linalg.norm(astar) 
		self.bstar = np.linalg.norm(bstar)
		self.cstar = np.linalg.norm(cstar) 
		self.cell_vol_recip = V_recip 
		self.space_group = space_group
		self.fname = ciffile 
		self.nist_file=nist_data
		self.scatt_dict = scatt_dict
		self.laufile=laufile
		self.customlaufile=customlaufile
		self.cif_dict = cif_obj
		self.abs_dict=abs_dict


		chem_sum = cif_obj['_chemical_formula_sum']
		try:
			formula_weight = float(cif_obj['_chemical_formula_weight'])
		except:
			#Need to calculate from chemsum, not implemented. yet..
			print("WARNING: Chemical weight not in cif file. Placeholder value used but should be updated manually using: \n Material.formula_weight=(val)")
			formula_weight = 100.0

		formula_units = int(cif_obj['_cell_formula_units_Z'])
		self.chem_sum = chem_sum 
		self.formula_weight=formula_weight
		self.formula_units = formula_units
		#Need to calculate some quantities used in simulation that are inherent to the sample
		structure_array=self.gen_unit_cell_positions()
		#Need two different quantities for the simulation. Abs xc / unit cell and absorption length for union components
		self.rho_abs=rho_abs
		self.sigma_inc=sigma_inc
		if self.rho_abs==False:
			try:
				cell_V = self.cell_vol 
				formula = self.chem_sum 
				num_units = self.formula_units
				formula_list = formula.split()
				atoms =[]
				for string in formula_list:
					num = ''.join(x for x in string if x.isdigit())
					ion = ''.join(x for x in string if x.isalpha())
					if not num:
						num=1
					atoms.append([ion,int(num)])
				sigma_abs = 0.0
				sigma_inc = 0.0
				for i in range(len(atoms)):
					if self.abs_dict==False:
						abs_xc_str = self.scatt_dict[atoms[i][0]][-1]
						inc_xc_str = self.scatt_dict[atoms[i][0]][4]
						abs_xc = float(abs_xc_str.split('(')[0])
						inc_xc = float(inc_xc_str.split('(')[0])
						sigma_abs = sigma_abs+(atoms[i][1]*abs_xc)
						sigma_inc = sigma_inc+(atoms[i][1]*inc_xc)
					else:
						abs_xc = self.abs_dict[atoms[i][0]]
						sigma_abs=sigma_abs + (atoms[i][1]*abs_xc)
				self.rho_abs_fu = sigma_abs
				self.rho_abs = sigma_abs*num_units
				if self.sigma_inc==False:
					self.sigma_inc = sigma_inc

				
			except Exception as e:
				print("WARNING- absorption cross section could not be specified.")
				print("Resolve this by checking your isotope composition or by specifying the absorption cross section")
				print("Per unit cell volume manually using sample.rho_abs=xxxxx ")
				print(e)
				self.rho_abs_fu=30.0
				self.rho_abs=30.0
				if self.sigma_inc==False:
					self.sigma_inc=1.0
		#Below are sample specific parameters used in the simulation
		self.sample_shape=sample_shape 
		self.sample_diameter_d = sample_diameter_d
		self.sample_tilt = sample_tilt 
		self.sample_length=sample_length
		self.sample_widx=sample_widx
		self.sample_widy=sample_widy 
		self.sample_widz=sample_widz 
		self.sample_mosaic=sample_mosaic
		self.delta_d = delta_d
		self.crystal_axis_xrot=crystal_axis_xrot
		self.crystal_axis_yrot=crystal_axis_yrot
		self.crystal_axis_zrot=crystal_axis_zrot
		self.spot_omega=None #Used for resolution function calculation in spot_sample component
		self.spot_twoTheta=None #Used for resolution function calculation in spot_sample component. 
		self.spot_HKL=None
		self.spot_Qmag=None
		self.inel_omega=None #Used for full resolution function calculation with inel_crystal component
		self.inel_HKL=None # Used for full resolution function calculation with the inel_crystal component
		self.inel_SF=None # Used for full resolution function calculation, custom structure factors
		self.spot_eideal=None 


		#Below info is for alignment and will probably need to be updated by user
		self.orient_u = orient_u
		self.orient_v = orient_v
		self.orient_w = orient_w
		self.avec_labframe=avec 
		self.bvec_labframe=bvec 
		self.cvec_labframe=cvec 
		self.astar_vec_labframe=astar
		self.bstar_vec_labframe=bstar
		self.cstar_vec_labframe=cstar
		self.labframe_mat=None
		# extracts some additional info in the cif file about the general unit cell
		f_lines = self.gen_flines()


	#Methods begin below
	def gen_flines(self):
		#simply retuns the flines string array
		cif_f = open(self.fname,'r')
		f_lines = cif_f.readlines()
		cif_f.close()
		return f_lines

	def generate_symmetry_operations(self):
		#Collect the symmetry equivalent sites. File format is 'site_id, symmetry equiv xyz'
		#Check for sure where the position is
		#returns the symmetry operations as array of strings, i.e. ['+x','+y','-z']

		symm_arr = self.cif_dict['_symmetry_equiv_pos_as_xyz']
		for i in range(len(symm_arr)):
			if type(symm_arr[i])==str:
				symm_arr[i]=symm_arr[i].split(',')
			else:
				pass
		#Now operations in format of ['+x','+y','+z']
		return symm_arr

	def gen_unique_coords(self):
		#Get the relevant atomic coordinates and displacement aprameters for unique positions
		f_lines = self.gen_flines()

		coords = {}
		#Make a dictionary of the ions and their positions- dctionary of format 
		# ['IonLabel': '['ion', fract_x, fract_y, fract_z, occupancy, Uiso, Uiso_val, Multiplicity]]

		atom_site_type_symbol_arr =  self.cif_dict['_atom_site_type_symbol']
		atom_site_label_arr = self.cif_dict['_atom_site_label']
		atom_site_fract_x_arr = self.cif_dict['_atom_site_fract_x']
		atom_site_fract_y_arr = self.cif_dict['_atom_site_fract_y']
		atom_site_fract_z_arr = self.cif_dict['_atom_site_fract_z']
		atom_site_occupancy_arr = self.cif_dict['_atom_site_occupancy']
		#The following may or may not be in the cif file
		try:
			atom_site_thermal_displace_type_arr = self.cif_dict['_atom_site_thermal_displace_type']
		except:
			atom_site_thermal_displace_type_arr = np.zeros(len(atom_site_type_symbol_arr))
		try:
			atom_site_U_iso_or_equiv_arr = self.cif_dict['_atom_site_U_iso_or_equiv']
		except:
			atom_site_U_iso_or_equiv_arr = np.zeros(len(atom_site_type_symbol_arr))
		try:
			atom_site_symmetry_multiplicity_arr = self.cif_dict['_atom_site_multiplicity']
		except:
			atom_site_symmetry_multiplicity_arr = np.zeros(len(atom_site_type_symbol_arr))
		for i in range(len(atom_site_label_arr)):
			ion = atom_site_type_symbol_arr[i]
			label = atom_site_label_arr[i]
			fract_x = atom_site_fract_x_arr[i]
			fract_y = atom_site_fract_y_arr[i]
			fract_z = atom_site_fract_z_arr[i]
			occupancy = atom_site_occupancy_arr[i]
			thermal_displace_type = atom_site_thermal_displace_type_arr[i]
			Uiso = atom_site_U_iso_or_equiv_arr[i]
			sym_mult = atom_site_symmetry_multiplicity_arr[i]
			coords[label]=[ion,fract_x,fract_y,fract_z,occupancy,thermal_displace_type,Uiso,sym_mult]
			#Note these are all still strings


		# The cif file tells the number of atom types in the cell- we can check the results of our symmetry operations with this.
		expected={}
		try:
			ion_list = self.cif_dict['_atom_type_symbol']
			ion_number = self.cif_dict['_atom_type_number_in_cell']
		except:
			ion_list = [0]
			ion_number = [0]
		for i in range(len(ion_list)):
			expected[ion_list[i]]=float(ion_number[i])
		#store this information for later
		self.expected_sites=expected
		return coords 
	def gen_unit_cell_positions(self):
			# Now we must generate all of the positions. We'll generate a list of format:
		#    [ion, x, y, z]
		# which makes structure factor calclation easier. 
		coords = self.gen_unique_coords()
		scatt_dict = self.scatt_dict
		symm_ops = self.generate_symmetry_operations()

		positions=[]
		structure_array=[]
		#for every ion, iterate over the symmetry operations. If the position already exists, it is not unique and not added to the posisions array 
		for position in coords:
			ion_coords = coords[position]
			ion = ion_coords[0]
			#For some reason O has a - next to it..
			ion = ion.replace('-','')
			ion = ion.replace('+','')
			ion = "".join([x for x in ion if x.isalpha()])
			x = float(ion_coords[1].replace(' ','').split('(')[0])
			y = float(ion_coords[2].replace(' ','').split('(')[0])
			z = float(ion_coords[3].replace(' ','').split('(')[0])
			try:
				if self.b_arr==False:
					b_el = float(scatt_dict[ion][1])
				else:
					b_el = float(scatt_dict[ion])
			except KeyError:
				print('Ion '+ion+' not found in NIST Tables or included b_arr. Include argument b_arr with proper elastic scattering lengths in fm when declaring Material object.')
				break
				return 0
			occupancy = float(ion_coords[4])

			for j in range(len(symm_ops)):
				symmetry = symm_ops[j]
				#replace the x with our new x, etc for y and z 
				x_sym = symmetry[0]
				x_eval_str = x_sym.replace('x',str(x))
				x_eval_str = x_eval_str.replace('y',str(y))
				x_eval_str = x_eval_str.replace('z',str(z))
				x_eval_str = x_eval_str.replace('/','*1.0/')
				y_sym = symmetry[1]
				y_eval_str = y_sym.replace('x',str(x))
				y_eval_str = y_eval_str.replace('y',str(y))
				y_eval_str = y_eval_str.replace('z',str(z))
				y_eval_str = y_eval_str.replace('/','*1.0/')

				z_sym = symmetry[2]
				z_eval_str = z_sym.replace('x',str(x))
				z_eval_str = z_eval_str.replace('y',str(y))
				z_eval_str = z_eval_str.replace('z',str(z))
				z_eval_str = z_eval_str.replace('/','*1.0/')
				x_pos = eval(x_eval_str)
				y_pos = eval(y_eval_str)
				z_pos = eval(z_eval_str)
				
				if x_pos==0.0:
					x_pos=0.0
				if y_pos==0.0:
					y_pos=0.0
				if z_pos==0.0:
					z_pos=0.0
				if x_pos<0.0:
					x_pos+=1.
				if x_pos>=1.0:
					x_pos-=1.
				if y_pos<=-0.0:
					y_pos+=1.
				if y_pos>=1.00:
					y_pos-=1.
				if z_pos<=-0.0:
					z_pos+=1.
				if z_pos>=1.00:
					z_pos-=1.0
				
				#assume that atoms can be no closer than 0.1 Ang
				z_pos = round(z_pos,5)
				x_pos = round(x_pos,5)
				y_pos = round(y_pos,5)
				occ = occupancy
				pos = [round(x_pos,5),round(y_pos,5),round(z_pos,5),occ]
				if pos not in positions:
					positions.append(pos)
					structure_array.append([ion,b_el,x_pos,y_pos,z_pos,occ])

		#Now we have all of the positions!
		self.unit_cell_xyz = structure_array
		return structure_array

	def gen_reflection_list(self,max_tau=20,maxQmag=1e10,b_dict=False):
		#Calculates the structure factor for all reflections in the unit cell. 
		# returns an array of arrays of format [H K L Freal Fi |F|^2 ]

		#NOTE add in occupancy later
		#Need to convert from fractional to real coordinates 
		structure = self.gen_unit_cell_positions()

		F_HKL = 0.0
		#Generate array of Q-vectors
		taulim = np.arange(-max_tau+1,max_tau)
		xx, yy, zz = np.meshgrid(taulim,taulim,taulim)
		x = xx.flatten()
		y = yy.flatten()
		z = zz.flatten()
		#array of reciprocal lattice vectors; 4th column will be structure factor^2
		tau = np.array([x,y,z, np.zeros(len(x))]).transpose()  

		ion_list = np.array(structure)[:,0]
		occupancy_arr = np.array(structure)[:,5].astype(float)
		b_array = occupancy_arr*np.array(structure)[:,1].astype(float)

		#Imported from the NIST site so this is in femtometers, for result to be barn divide by 1000
		b_array=b_array*0.1

		unit_cell_pos = np.array(structure)[:,2:5].astype(float)
		#Convert from fractional to real space.
		a_vec = self.avec
		b_vec =self.bvec
		c_vec = self.cvec

		i=0
		bad_ind = []
		for i in range(len(tau)):
			q_vect = tau[i][0:3]
			qmag = self.Qmag_HKL(q_vect[0],q_vect[1],q_vect[2])

			if qmag>maxQmag:
				bad_ind.append(i)
				tau[i,3]=0.0
			else:
				SF = 0
				#Sum over all ions in the cell
				for j in range(len(unit_cell_pos)):
					pos = unit_cell_pos[j]
					SF = SF + occupancy_arr[j]*b_array[j]*np.exp(2.0j*np.pi*np.inner(q_vect,pos))
				tau[i,3]=np.linalg.norm(SF)**2
		# Eliminate tiny values
		tau[:,3][tau[:,3] < 1e-8] = 0.0
		low_reflect_i = np.where(tau[:,3]==0.0)[0]
		zero_ind = np.where(tau[:,3]==0.0)[0]

		# Trim off values where Q is too high
		#tau=np.delete(tau,zero_ind)

		self.HKL_list = tau
		return tau
	def fetch_F_HKL(self,H,K,L):
		# Returns the SF^2 of a particular reflection
		try:
			HKL = self.HKL_list
		except AttributeError:
			HKL = self.gen_reflection_list()
		index = np.argmin(np.abs(H-HKL[:,0])+np.abs(K-HKL[:,1])+np.abs(L-HKL[:,2]))
		#print('|F|^2 for ['+str(H)+str(K)+str(L)+'] ='+str(HKL[index][3])+' (fm^2/sr)')
		return HKL[index]
	
	def Qmag_HKL(self,H,K,L):
		#Returns the magnitude of the q-vector of the assosciated HKL indec in Ang^-1
		#qvec = 2.0*np.pi*np.array(H*self.astar+K*self.bstar+L*self.cstar)
		qvec = np.array(H*self.astar_vec+K*self.bstar_vec+L*self.cstar_vec)
		qmag = np.linalg.norm(qvec)
		return qmag 

	def twotheta_hkl(self,H,K,L,E,mode='deg'):
		#Simply feeds into equivalent Q_HKL function then converts to twotheta
		lam_i = 9.045/np.sqrt(E)
		lam_f = 9.045/np.sqrt(E-0.0)
		ki = 2.0*np.pi/lam_i 
		kf = 2.0*np.pi/lam_f
		Qmag = self.Qmag_HKL(H,K,L)
		A = Qmag**2 - ki**2 - kf**2 
		B = 2.0*ki*kf 
		twoTheta = np.arccos(-A/B)
		if mode=='deg':
			return twoTheta*180.0/np.pi
		else:
			return twoTheta	

	def adjust_hkl_inelastic(self,H,K,L,Ei,Ef):
		#Let's say we want (0.5,0.5,2) Ei=7 Ef=5
		#The correct elastic representation is about [0.51097741, 0.51097741, 0.32138822]
		#tau =np.array([0.5,0.5,0.2])
		#tau = np.array([-0.6,-0.6,-0.4])
		tau = np.array([H,K,L])
		mag_tau = self.Qmag_HKL(*tau)
		#print(f'For Tau={tau} Q={mag_tau:.3f} Ang^-1')
		Ei = 7.0
		Ef = 5.0
		lam_i = 9.045/np.sqrt(Ei)
		lam_f = 9.045/np.sqrt(Ef)
		ki = np.array([0,0,1])*2.0*np.pi/lam_i
		kf_0 = np.array([0,0,1])*2.0*np.pi/lam_f #Not the correct direction
		ki_m = 2.0*np.pi/lam_i 
		kf_m = 2.0*np.pi/lam_f
		twoTheta =180.0*np.arccos((ki_m**2 + kf_m**2 - mag_tau**2)/(ki_m*kf_m*2.0))/np.pi
		#print(f'2theta={twoTheta:.3f} deg')
		twoTheta = np.pi*twoTheta/180.0
		asLab = self.astar_vec_labframe
		bsLab = self.bstar_vec_labframe
		csLab = self.cstar_vec_labframe

		u_lab = np.array(self.orient_u[0]*asLab+\
		                  self.orient_u[1]*bsLab+\
		                  self.orient_u[2]*csLab)#Reflection Q-vector in Ang^-1
		v_lab = np.array(self.orient_v[0]*asLab+\
		                self.orient_v[1]*bsLab+\
		                self.orient_v[2]*csLab)
		tau_lab = np.array(tau[0]*asLab+tau[1]*bsLab+tau[2]*csLab)

		#Get the respective A3 angle for this. 
		UdotTau = np.dot(tau_lab,u_lab)
		VdotTau = np.dot(tau_lab,v_lab)

		if (UdotTau>=0 and VdotTau>=0):
		    quadrant=1
		    ucheck = np.array([1,0,0])*np.linalg.norm(u_lab)
		    vcheck = np.array([0,0,1])*np.linalg.norm(v_lab)
		elif (UdotTau<0 and VdotTau>=0):
		    quadrant=2
		    ucheck = np.array([-1,0,0])*np.linalg.norm(u_lab)
		    vcheck = np.array([0,0,1])*np.linalg.norm(v_lab)
		elif (UdotTau<0 and VdotTau<0):
		    quadrant=3
		    ucheck = np.array([-1,0,0])*np.linalg.norm(u_lab)
		    vcheck = np.array([0,0,-1])*np.linalg.norm(v_lab)
		elif (UdotTau>0 and VdotTau<0):
		    quadrant=4
		    ucheck = np.array([1,0,0])*np.linalg.norm(u_lab)
		    vcheck = np.array([0,0,-1])*np.linalg.norm(v_lab)
		#print(f'Reflection Quadrant {quadrant}')
		tau = np.abs(tau)
		tau_lab = np.abs(tau_lab) #Fix the position of the reflection later

		#Check if the refelction is in plane:
		theta_ucheck = np.arccos(np.dot(tau_lab,ucheck)/\
		                        (np.linalg.norm(tau_lab)*np.linalg.norm(ucheck)))
		theta_vcheck = np.arccos(np.dot(tau_lab,vcheck)/\
		                        (np.linalg.norm(tau_lab)*np.linalg.norm(vcheck)))
		total_angle = theta_ucheck+theta_vcheck
		if np.abs(total_angle-np.pi/2)>0.01:
		    print(f'Warning: {tau} not in scattering plane.')
		    
		# Q = ki - kf, kf = ki - Q
		#print(f'Rotation twoTheta={twoTheta}')
		R = np.array([[np.cos(-twoTheta),0,np.sin(-twoTheta)],[0,1,0],[-np.sin(-twoTheta),0,np.cos(-twoTheta)]])
		kf = np.matmul(R,kf_0)
		Q_inel = ki-kf
		Q_inel_abs = np.abs(Q_inel)
		#Get angle between this q-vector and the lab frame q-vector
		A3 = np.arccos(np.dot(tau_lab,Q_inel)/(np.linalg.norm(tau_lab)*np.linalg.norm(Q_inel)))
		#print(f'A3={180.0*A3/np.pi:.3f} deg')
		#Rotate the sample such that these are in the same direction
		R = np.array([[np.cos(-A3),0,np.sin(-A3)],[0,1,0],[-np.sin(-A3),0,np.cos(-A3)]])
		urot = np.matmul(R,u_lab)
		vrot = np.matmul(R,v_lab)
		#Get Q-indices in this frame
		thetau = np.arccos(np.dot(urot,Q_inel)/(np.linalg.norm(Q_inel)*np.linalg.norm(urot)))
		thetav = np.arccos(np.dot(vrot,Q_inel)/(np.linalg.norm(Q_inel)*np.linalg.norm(vrot)))

		Qx = np.cos(thetau)*np.linalg.norm(Q_inel)/np.linalg.norm(urot)
		Qy = np.cos(thetav)*np.linalg.norm(Q_inel)/np.linalg.norm(vrot)
		#print(f'|Q_inel| {np.linalg.norm(Q_inel)}')
		#print(f'ki = {ki}, |ki|={np.linalg.norm(ki):.2f} Ang^-1')
		#print(f'kf inel = {kf} |kf inel|={np.linalg.norm(kf):.2f} Ang^-1')

		kf_hat = kf / np.linalg.norm(kf)
		kf_el = ki_m*kf_hat
		#print(f'kf el = {kf_el}, |kf el|={np.linalg.norm(kf_el):.2f} Ang^-1')

		tau_el = ki-kf_el

		#print(f'Q-lab elastic: {tau_el}')
		#print(f'|Q_el| = {np.linalg.norm(tau_el):.3f} Ang^-1')

		#Rotate u by the difference between kf and kf_el
		theta_kf = np.arccos(np.dot(Q_inel,tau_el)/(np.linalg.norm(tau_el)*np.linalg.norm(Q_inel)))
		theta_kf = theta_kf*2.0#30.0*np.pi/180.0
		#print(f'theta kf = {theta_kf*180.0/np.pi:.3f} deg')
		R = np.array([[np.cos(theta_kf),0,np.sin(theta_kf)],[0,1,0],[-np.sin(theta_kf),0,np.cos(theta_kf)]])
		urot = np.matmul(R,urot)
		vrot = np.matmul(R,vrot)

		thetau_el = np.arccos(np.dot(urot,tau_el)/(np.linalg.norm(tau_el)*np.linalg.norm(urot)))
		thetav_el = np.arccos(np.dot(vrot,tau_el)/(np.linalg.norm(tau_el)*np.linalg.norm(vrot)))

		Qx_el = np.cos(thetau_el)*np.linalg.norm(tau_el)/np.linalg.norm(urot)
		Qy_el = np.cos(thetav_el)*np.linalg.norm(tau_el)/np.linalg.norm(vrot)


		el_u = Qx_el
		el_v = Qy_el


		if quadrant==1:
		    reflection = el_u*np.array(self.orient_u) + \
		                    el_v*np.array(self.orient_v)
		elif quadrant==2:
		    reflection = el_u*-1.0*np.array(self.orient_u) + \
		                    el_v*np.array(self.orient_v)
		elif quadrant==3:
		    reflection = el_u*-1.0*np.array(self.orient_u) + \
		                    el_v*-1.0*np.array(self.orient_v)
		elif quadrant==4:
		    reflection = el_u*np.array(self.orient_u) + \
		                    el_v*-1.0*np.array(self.orient_v)
		#mcstas quirk:
		reflection*=-1.0
		return reflection 

	def twotheta_hkl_omega(self,H,K,L,Ei,omega,mode='deg'):
		#Given HKL indices, incident energy, and energy transfer, returns the scattering angle
		# Q^2 = ki^2 + kf^2 -2 ki kf cos(twoTheta)
		lam_i = 9.045/np.sqrt(Ei)
		lam_f = 9.045/np.sqrt(Ei-omega)
		ki = 2.0*np.pi/lam_i 
		kf = 2.0*np.pi/lam_f
		Qmag = self.Qmag_HKL(H,K,L)
		A = Qmag**2 - ki**2 - kf**2 
		B = 2.0*ki*kf 
		twoTheta = np.arccos(-A/B)
		if mode=='deg':
			return twoTheta*180.0/np.pi
		else:
			return twoTheta		

	def QE_to_twotheta(self,Qmag,Ei,omega,mode='deg'):
		#Given HKL indices, incident energy, and energy transfer, returns the scattering angle
		# Q^2 = ki^2 + kf^2 -2 ki kf cos(twoTheta)
		lam_i = 9.045/np.sqrt(Ei)
		lam_f = 9.045/np.sqrt(Ei-omega)
		ki = 2.0*np.pi/lam_i 
		kf = 2.0*np.pi/lam_f
		A = Qmag**2 - ki**2 - kf**2 
		B = 2.0*ki*kf 
		twoTheta = np.arccos(-A/B)
		if mode=='deg':
			return twoTheta*180.0/np.pi
		else:
			return twoTheta	

	def theory_powder_bragg_I(self,obsQ,intQ,intE,H,K,L,sample_mass):
		#Returns a scale factor to scale the data into  'barn/(eV mol sr fu)'
		#Makes a very rough assumption that Q^2 is constant through the integral (clearly it's not)
		#If you want to avoid this you need to evaluate int(Q^2), and input 1.0 as obsQ

		'''
		Input params:
			obsQ - center of bragg peak 
			intQ - integral in Q of bragg peak
			intE - integral in E of bragg peak (In meV!!)
			HKL, indices of bragg peak
			sample_mass- mass of sample in grams

		Returns:
			A scaling factor to normalize your dataset to the bragg peak.In units of fm^2
			Multiply by multiplicity afterwards if needed
		'''
		observed_Qsqr = obsQ**2 *(intQ)
		obs_E_int =intE #To become eV rather than meV
		I_obs = observed_Qsqr*obs_E_int
		f_HKL = self.fetch_F_HKL(H,K,L)[-1]
		#Convert to barn^2 / Sr
		f_HKL = f_HKL#*0.01
		#We want it per fu, so scale the fHKL to reflect this
		#f_HKL/=formula_scale
		density = self.formula_weight
		N = sample_mass/density 
		numerator = (4.0*np.pi)*I_obs*N 
		denom = f_HKL * (((2*np.pi)**3)/self.cell_vol)
		scaling_factor = denom/numerator 
		return scaling_factor

	def cif2lau(self,outdir=os.getcwd(),launame=None):
		#Attempt to use the baked in mcstas utility to make an lau file. 
		try:
			if launame is None:
				launame=self.ciffile.split('.')[0]+'.lau'
			os.system('cif2hkl --xtal '+self.ciffile)
			os.system('mv '+self.ciffile+'.hkl '+self.ciffile.split('.')[0]+'.lau')
			print('Conversion of CIF to crystallographical LAU file successful. ')
		except Exception as e:
			print('Converstion of CIF to crystallographical LAU file unsuccessful.')
			print('To get around this, prepare the lau file elsewhere and assign it in the following way:')
			print('macs_eperiment.sample.laufile=mylau.lau')
			print(e)
		self.laufile = self.ciffile.split('.')[0]+'.lau'
		#Need to remove lattice parameters from lau file
		with open(self.laufile,'r') as f:
			lines = f.readlines()
		with open(self.laufile,'w') as f:
			for line in lines:
				bad_writes = ['lattice_a','lattice_b','lattice_c','lattice_aa','lattice_bb','lattice_cc']
				if not any(bad_label in line for bad_label in bad_writes):
					f.write(line)
		return 1

	def gen_custom_lau(self,HKL_list,Sqwlist,Ei,omega,outdir=os.getcwd(),launame=None):
		#Given a set of reflections and strure factors, generates a custom LAU file with columnns of
		#  [ H K L E S(q,w)] as required by the single_crystal_inelastic component
		# Takes list of [H K L] indices, list of energy transfers for those indices, and structure factors.

		#Easiest to do this by editing the standard lau file 
		#Attempt to use the baked in mcstas utility to make an lau file. 
		try:
			if launame is None:
				launame=self.ciffile.split('.')[0]+'.lau'
			os.system('cif2hkl --xtal '+self.ciffile)
			os.system('mv '+self.ciffile+'.hkl '+self.ciffile.split('.')[0]+'.lau')
			print('Conversion of CIF to crystallographical LAU file successful. ')
		except Exception as e:
			print('Converstion of CIF to crystallographical LAU file unsuccessful.')
			print('To get around this, prepare the lau file elsewhere and assign it in the following way:')
			print('macs_eperiment.sample.laufile=mylau.lau')
			print(e)
		self.laufile = self.ciffile.split('.')[0]+'.lau'
		#Need to remove lattice parameters from lau file
		with open(self.laufile,'r') as f:
			lines = f.readlines()
		with open(self.laufile,'w') as f:
			for line in lines:
				bad_writes = ['lattice_a','lattice_b','lattice_c','lattice_aa','lattice_bb','lattice_cc']
				if not any(bad_label in line for bad_label in bad_writes):
					f.write(line)
		#Standard Lau file written. Now we write the custom one. 
		#write a new file 
		name = self.ciffile.split('.')[0]+'_custom.lau'
		shutil.copyfile(self.laufile,name)
		self.customlaufile=name 

		#Fix the HKL list to account for the energy transfer
		for i in range(len(HKL_list)):
			print('Requested Reflection')
			print(HKL_list[i])
			H=HKL_list[i,0]
			K=HKL_list[i,1]
			L=HKL_list[i,2]
			newHKL = self.adjust_hkl_inelastic(H,K,L,Ei,Ei-omega)
			newH,newK,newL = newHKL[0],newHKL[1],newHKL[2]
			print('Output HKL')
			print(newHKL)
			#replace nans with 0 
			if np.isnan(newH):
				newH=0
			if np.isnan(newK):
				newK=0
			if np.isnan(newL):
				newL=0
			HKL_list[i,0]=newH 
			HKL_list[i,1]=newK 
			HKL_list[i,2]=newL
		#Now, delete all lines below the header 
		#Column definitions need to be replaced by the following:
		hcol_str = '# column_h  1\n'
		kcol_str = '# column_k  2\n'
		lcol_str = '# column_l  3\n'
		multcol_str = '# column_j  4   multiplicity \'j\'\n'
		sfcol_str = '# column_F2 5   norm of scattering factor |F|^2 in [barn]\n'
		#Second to Last line should also be replaced by following string:
		new_numstr = '# List '+str(len(HKL_list))+' reflections for lambda >    0.0500 [Angs], decreasing d-spacing\n'
		#Last line should be following string
		new_laststr = '# H   K   L     Mult                   |Fc|^2\n'

		with open(self.customlaufile,'r') as f:
			lines = f.readlines()
		with open(self.customlaufile,'w') as f:
			for line in lines:
				if line[0]=='#' and 'column_' not in line:
					if 'List' in line and 'reflections' in line:
						f.write(new_numstr)
					elif 'Mult' in line and 'dspc' in line:
						f.write(new_laststr)
					else:
						f.write(line)
				if 'column_h' in line:
					f.write(hcol_str)
				if 'column_k' in line:
					f.write(kcol_str)
				if 'column_l' in line:
					f.write(lcol_str)
				if 'column_j' in line:
					f.write(multcol_str)
				if 'column_F2' in line:
					f.write(sfcol_str)



		#Generate matrix for reflections
		out_lau_mat = np.zeros((len(Sqwlist),5))
		out_lau_mat[:,0] = HKL_list[:,0]
		out_lau_mat[:,1] = HKL_list[:,1]
		out_lau_mat[:,2] = HKL_list[:,2]
		out_lau_mat[:,3] = 1 #Not omega but multiplicity
		out_lau_mat[:,4] = Sqwlist
		#Append custom lau file with the information after formatting each string
		f = open(self.customlaufile,'a')
		for i in range(len(out_lau_mat)):
			hstr = '{0: >8}'.format('{h:.3f}'.format(h=out_lau_mat[i,0]))
			kstr = '{0: >8}'.format('{k:.3f}'.format(k=out_lau_mat[i,1]))
			lstr = '{0: >8}'.format('{l:.3f}'.format(l=out_lau_mat[i,2]))
			wstr = '{0: >8}'.format('{w:.3f}'.format(w=out_lau_mat[i,3]))
			sfstr = '{0: >16}'.format('{sf:.6f}'.format(sf=out_lau_mat[i,4]))+'\n'
			line = hstr+kstr+lstr+wstr+sfstr
			f.write(line)
		f.close()
		#self.laufile = name
		#write the specified reflections to the file 
		return name

	def project_sample_realspace(self):
		#Given an alignment in the objects orient_u and orient_v, with u being perpendicular to beam and v parallel to beam
		#Used to write instr file, where convention is that x is perpendicular to beam, z is beam direction, y is vertical.
		#First, recover real space a* b* c* 
		u_dir = np.array([1.0,0.0,0.0]) #These are in the lab frame, u perp to beam
		v_dir = np.array([0.0,0.0,1.0])
		w_dir = np.array([0.0,1.0,0.0])
		#First find the direction of u_alignment before any rotations
		#We start by assuming that a is in the x direction, b is in the z-direction, c is in the y-direction
		dir_u_init = self.orient_u[0]*self.astar_vec+self.orient_u[1]*self.bstar_vec + self.orient_u[2]*self.cstar_vec
		dir_v_init = self.orient_v[0]*self.astar_vec+self.orient_v[1]*self.bstar_vec + self.orient_v[2]*self.cstar_vec
		dir_w_init = self.orient_w[0]*self.astar_vec+self.orient_w[1]*self.bstar_vec + self.orient_w[2]*self.cstar_vec
		#Need to check that these two directions are perpendicular- otherwise not a valid scattering plane. 
		#instead we set u to be parallel to the beam and v to have zero out of plane component which is the best we can do.
		dir_u_init_norm = dir_u_init / np.linalg.norm(dir_u_init)
		dir_v_init_norm = dir_v_init / np.linalg.norm(dir_v_init)
		dir_w_init_norm = dir_w_init / np.linalg.norm(dir_w_init)
		#Get the rotation matrix that will take u_init to u_dir
		u_dir_norm = u_dir/np.linalg.norm(u_dir)
		v_dir_norm = v_dir/np.linalg.norm(v_dir)
		w_dir_norm = w_dir/np.linalg.norm(w_dir)
		c = np.dot(dir_u_init_norm,u_dir_norm)
		v = np.cross(dir_u_init_norm,u_dir_norm)
		s = np.linalg.norm(v)
		vsubx = np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
		vsqr=np.dot(vsubx,vsubx)
		R = np.eye(3) + vsubx + (vsqr)*1.0/(1.0+c) #R will rotate the u-axis to be parallel to the beam in scattering plane
		#Apply R to all three lattice and reciprocal vectors
		avec_r1 = np.matmul(R,self.avec)
		bvec_r1 = np.matmul(R,self.bvec)
		cvec_r1 = np.matmul(R,self.cvec)
		astar_vec_r1 = np.matmul(R,self.astar_vec)
		bstar_vec_r1 = np.matmul(R,self.bstar_vec)
		cstar_vec_r1 = np.matmul(R,self.cstar_vec)
		#Now find a rotation about the z-axis that puts the new v-vector in the plane with positive x
		dir_v_r1 = self.orient_v[0]*astar_vec_r1 + self.orient_v[1]*bstar_vec_r1 + self.orient_v[2]*cstar_vec_r1
		dir_v_r1_norm = dir_v_r1 / np.linalg.norm(dir_v_r1)
		#Final direction is a unit vector same z, rotated along the z-axis such that there is zero y-component
		v_vec_final = np.array([np.sqrt(dir_v_r1_norm[0]**2 + dir_v_r1_norm[1]**2),0.0,dir_v_r1_norm[2]])
		#Same procedure as before to get the rotation matrix
		c = np.dot(dir_v_r1_norm,v_vec_final)
		c = np.around(c,8)
		v = np.cross(dir_v_r1_norm,v_vec_final)
		s = np.linalg.norm(v)
		vsubx = np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
		vsqr=np.dot(vsubx,vsubx)
		R = np.eye(3) + vsubx + (vsqr)*1.0/(1.0+c) #R will rotate the u-axis to be perpendicular to the beam in scattering plane
		#Handle the special case of when the v-vector needs to be reflected (c=-1)
		if c==-1.0:
			R = np.array([[-1.0,0,0],[0.0,1.0,0.0],[0.0,0.0,1.0]])
		#Apply R to all three lattice and reciprocal vectors
		avec_f = np.around(np.matmul(R,avec_r1),5)
		bvec_f = np.around(np.matmul(R,bvec_r1),5)
		cvec_f = np.around(np.matmul(R,cvec_r1),5)
		astar_vec_f = np.around(np.matmul(R,astar_vec_r1),5)
		bstar_vec_f = np.around(np.matmul(R,bstar_vec_r1),5)
		cstar_vec_f = np.around(np.matmul(R,cstar_vec_r1),5)
		self.avec_labframe=avec_f
		self.bvec_labframe=bvec_f
		self.cvec_labframe=cvec_f
		self.astar_vec_labframe=astar_vec_f
		self.bstar_vec_labframe=bstar_vec_f 
		self.cstar_vec_labframe=cstar_vec_f 
		labframe_mat = np.array([avec_f,bvec_f,cvec_f])
		self.labframe_mat=labframe_mat
