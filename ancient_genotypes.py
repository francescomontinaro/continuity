import msprime as msp
import numpy as np
import scipy.optimize as opt
import matplotlib.pyplot as plt
import scipy.stats as st
import scipy.special as sp
import copy as cp
from scipy.sparse.linalg import expm_multiply as expma

class FreqError(Exception):
	pass

def ancient_sample(num_modern=1000,anc_time=200,Ne=10000,mu=1.25e-8,length=1000,num_rep=1000, coverage=False):
	samples = [msp.Sample(population=0,time=0)]*num_modern
	samples.extend([msp.Sample(population=0,time=anc_time)]*2)
	sims = msp.simulate(samples=samples,Ne=Ne,mutation_rate=mu,length=length,num_replicates=num_rep)
	freq = []
	anc = []
	for sim in sims:
		for position, variant in sim.variants():
			var_array = map(int,list(variant))
			cur_freq = sum(var_array[:-2])/float(num_modern)
			if cur_freq == 0 or cur_freq == 1: continue
			freq.append(cur_freq)
			if not coverage:
				cur_site = np.array([0,0,0])
				cur_site[sum(var_array[-2:])]=1
				anc.append(cur_site)
			else:
				num_reads = st.poisson.rvs(coverage)
				reads = np.random.choice(var_array[-2:],size=num_reads, replace=True)
				GL = st.binom.pmf(sum(reads),num_reads,[0,.5,1])
				GL = GL/sum(GL)
				anc.append(GL)
	return np.array(freq), anc

def ancient_sample_split(num_modern=1000,anc_time=200,split_time=400,Ne0=10000,Ne1=10000,mu=1.25e-8,length=1000,num_rep=1000, coverage=False):
	samples = [msp.Sample(population=0,time=0)]*num_modern
	samples.extend([msp.Sample(population=1,time=anc_time)]*2)
	pop_config = [msp.PopulationConfiguration(initial_size=Ne0),msp.PopulationConfiguration(initial_size=Ne1)]
	divergence = [msp.MassMigration(time=split_time,source=1,destination=0,proportion=1.0)]
	sims = msp.simulate(samples=samples,Ne=Ne0,population_configurations=pop_config,demographic_events=divergence,mutation_rate=mu,length=length,num_replicates=num_rep)
	freq = []
	anc = []
	for sim in sims:
		for position, variant in sim.variants():
			var_array = map(int,list(variant))
			cur_freq = sum(var_array[:-2])/float(num_modern)
			if cur_freq == 0 or cur_freq == 1: continue
			if not coverage:
				cur_site = np.array([0,0,0])
				cur_site[sum(var_array[-2:])]=1
				anc.append(cur_site)
			else:
				num_reads = st.poisson.rvs(coverage)
				reads = np.random.choice(var_array[-2:],size=num_reads, replace=True)
				GL = st.binom.pmf(sum(reads),num_reads,[0,.5,1])
				GL = GL/sum(GL)
				anc.append(GL)
	return np.array(freq), anc


def ancient_sample_mix(num_modern=1000,anc_pop = 0, anc_time=200,mix_time=300,split_time=400,f=0.0,Ne0=10000,Ne1=10000,mu=1.25e-8,length=1000,num_rep=1000,coverage=False):
	if mix_time > split_time:
		print "mixture occurs more anciently than population split!"
		return None
	if f < 0 or f > 1:
		print "Admixture fraction is not in [0,1]"
		return None
	samples = [msp.Sample(population=0,time=0)]*num_modern
	samples.extend([msp.Sample(population=anc_pop,time=anc_time)]*2)
	pop_config = [msp.PopulationConfiguration(initial_size=Ne0),msp.PopulationConfiguration(initial_size=Ne1)]
	divergence = [msp.MassMigration(time=mix_time,source=0,destination=1,proportion = f),
			msp.MassMigration(time=split_time,source=1,destination=0,proportion=1.0)]
	sims = msp.simulate(samples=samples,Ne=Ne0,population_configurations=pop_config,demographic_events=divergence,mutation_rate=mu,length=length,num_replicates=num_rep)
	freq = []
	anc = []
	for sim in sims:
		for position, variant in sim.variants():
			var_array = map(int,list(variant))
			cur_freq = sum(var_array[:-2])/float(num_modern)
			if cur_freq == 0 or cur_freq == 1: continue
			freq.append(cur_freq)
			if not coverage:
				cur_site = np.array([0,0,0])
				cur_site[sum(var_array[-2:])]=1
				if len(cur_site) > 3:
					print var_array[-2:]
					print cur_site
					raw_input()
				anc.append(cur_site)
			else:
				num_reads = st.poisson.rvs(coverage)
				reads = np.random.choice(var_array[-2:],size=num_reads, replace=True)
				derived_reads = sum(reads)
				#if derived_reads == 0: 
				#	GL = np.array([1,0,0]) #TODO: Fix hack. Avoids infinities by assuming sites with no derived reads are ancestral 
				#elif derived_reads == num_reads:
				#	GL = np.array([0,0,1]) #TODO: Fix this hack. AVoids infinities by assuming sites with all derived reads are derived
				#else:
				#	GL = st.beta.pdf([0,.5,1],.5+derived_reads,.5+num_reads-derived_reads)
				#GL = GL/sum(GL)
				GL = st.binom.pmf(derived_reads,num_reads,[0,.5,1])
				anc.append(GL)
			#print var_array[-2:]
			#print anc
			#raw_input()
	return np.array(freq), anc

def ancient_sample_mix_multiple(num_modern=1000,anc_pop = 0, anc_num = 1, anc_time=200,mix_time=300,split_time=400,f=0.0,Ne0=10000,Ne1=10000,mu=1.25e-8,length=1000,num_rep=1000,coverage=False):
	if mix_time > split_time:
		print "mixture occurs more anciently than population split!"
		return None
	if f < 0 or f > 1:
		print "Admixture fraction is not in [0,1]"
		return None
	samples = [msp.Sample(population=0,time=0)]*num_modern
	samples.extend([msp.Sample(population=anc_pop,time=anc_time)]*(2*anc_num))
	pop_config = [msp.PopulationConfiguration(initial_size=Ne0),msp.PopulationConfiguration(initial_size=Ne1)]
	divergence = [msp.MassMigration(time=mix_time,source=0,destination=1,proportion = f),
			msp.MassMigration(time=split_time,source=1,destination=0,proportion=1.0)]
	sims = msp.simulate(samples=samples,Ne=Ne0,population_configurations=pop_config,demographic_events=divergence,mutation_rate=mu,length=length,num_replicates=num_rep)
	freq = []
	anc = []
	for sim in sims:
		for position, variant in sim.variants():
			var_array = map(int,list(variant))
			cur_freq = sum(var_array[:-(2*anc_num)])/float(num_modern)
			if cur_freq == 0 or cur_freq == 1: continue
			freq.append(cur_freq)
			if not coverage:
				cur_site = np.array([0,0,0])
				cur_site[sum(var_array[-2:])]=1
				if len(cur_site) > 3:
					print var_array[-2:]
					print cur_site
					raw_input()
				anc.append(cur_site)
			else:
				for i in range(anc_num):
					num_reads = st.poisson.rvs(coverage)
					if i == 0: cur_GT = var_array[-2:]
					else: cur_GT = var_array[-(2*(i+1)):-(2*i)],
					reads = np.random.choice(cur_GT,size=num_reads, replace=True)
					derived_reads = sum(reads)
					anc.append((num_reads-derived_reads,derived_reads))
			#print var_array[-2:]
			#print anc
			#raw_input()
	return np.array(freq), anc

def get_het_prob(freq,anc):
	anc_dict = {}
	for i in range(len(freq)):
		if freq[i] in anc_dict:
			anc_dict[freq[i]] += anc[i]
		else:
			anc_dict[freq[i]] = np.array([0.0,0.0,0.0])
			anc_dict[freq[i]] += anc[i]
	unique_freqs = sorted(np.unique(freq))
	pHet = []
	for i in range(len(unique_freqs)):
		cur_anc = anc_dict[unique_freqs[i]]
		try:
			pHet.append(cur_anc[1]/(cur_anc[1]+cur_anc[2]))
		except ZeroDivisionError:
			pHet.append(None)
	return np.array(unique_freqs), np.array(pHet), anc_dict

def expected_het_anc(x0,t):
	return 1.0/(3.0/2.0+(2*x0-1)/(1+np.exp(2*t)-2*x0))

def expected_het_split(x0,t1,t2):
	return 1.0/(1.0/2.0+(np.exp(2*t1+t2))/(1+np.exp(2*t1)-2*x0))

def expected_moments_split(x0,t1,t2):
	Ehet = np.exp(-3.*t1-t2)*(1.+np.exp(2.*t1)-2.*x0)*x0
	Eder = 1./2.*np.exp(-3.*t1-t2)*(2.*x0+np.exp(2.*t1)*(2.*np.exp(t2)-1.)-1.)*x0
	Eanc = 1.0  - Ehet - Eder
	return Eanc, Ehet, Eder

def get_numbers_from_dict(anc_dict):
	het = []
	hom = []
	for freq in sorted(anc_dict.keys()):
		het.append(anc_dict[freq][1])
		hom.append(anc_dict[freq][2])
	return np.array(het), np.array(hom)

#freqs, het, hom should be FIXED, determiend by data
def het_hom_likelihood_anc(t,freqs,het,hom):
	#check if 0 or 1 in freqs
	if 0 in freqs or 1 in freqs:
		raise FreqError("Remove sites that are monomophric in modern population")
	pHetExpect = expected_het_anc(freqs,t)
	likeVec = het*np.log(pHetExpect)+hom*np.log(1-pHetExpect)
	return(sum(likeVec))
	
#freqs, het, hom should be FIXED, determiend by data
def het_hom_likelihood_split(t1,t2,freqs,het,hom):
	if 0 in freqs or 1 in freqs:
		raise FreqError("Remove sites that are monomophric in modern population")
	pHetExpect = expected_het_split(freqs,t1,t2)
	likeVec = het*np.log(pHetExpect)+hom*np.log(1-pHetExpect)
	return(sum(likeVec))

#GLs should be a matrix
#freqs is the frequency of each site, should be same length as GLs
def GL_likelihood_split(t1,t2,freqs,GLs):
	expect = np.transpose(expected_moments_split(freqs,t1,t2))
	likePerLocus = np.sum(GLs*expect,axis=1)
	LL = np.sum(np.log(likePerLocus))
	return LL	

def het_hom_likelihood_mixture(t1,t2,t3,p,freqs,het,hom):
	if 0 in freqs or 1 in freqs:
		raise FreqError("Remove sites that are monomophric in modern population")
	pHetAnc = expected_het_anc(freqs,t1)
	pHetSplit = expected_het_split(freqs,t2,t3)
	pHetExpect = p*pHetAnc+(1.-p)*pHetSplit
	likeVec = het*np.log(pHetExpect)+hom*np.log(1-pHetExpect)
	return(sum(likeVec))

def chi_squared_anc(t,freqs,het,hom):
	pHetExpect = expected_het_anc(freqs,t)
	num = het+hom
	pHat = het/num
	pHat[np.isnan(pHat)]=0
	residuals = (np.sqrt(num)*(pHat-pHetExpect)**1/np.sqrt(pHetExpect*(1-pHetExpect)))
	return residuals	 

def cf_sum_anc(k,t,freqs,het,hom):
	num = het+hom
	pHetExpect = expected_het_anc(freqs,t)
	exp_sum = np.sum(1./(1-pHetExpect))
	exp_part = np.exp(1j*k*exp_sum)
	prod_internal = (1-pHetExpect+pHetExpect*np.exp(1j*k/(num*pHetExpect*(1-pHetExpect))))**num
	prod_internal[np.isnan(prod_internal)] = 1
	prod_part = np.prod(prod_internal)
	return exp_part*prod_part

def test_and_plot(anc_dict,x0Anc = st.uniform.rvs(size=1), x0Split = st.uniform.rvs(size=2),plot=True):
	het,hom = get_numbers_from_dict(anc_dict)
	freqs = np.sort(anc_dict.keys())
	ancTest = opt.fmin_l_bfgs_b(func=lambda x: -het_hom_likelihood_anc(x[0],freqs,het,hom), x0 = x0Anc, approx_grad=True,bounds=[[.0001,1000]],factr=10,pgtol=1e-15)
	splitTest = opt.fmin_l_bfgs_b(func=lambda x: -het_hom_likelihood_split(x[0],x[1],freqs,het,hom), x0 = x0Split, approx_grad=True,bounds=[[.0001,100],[.0001,100]],factr=10,pgtol=1e-15)
	if plot:
		tAnc = ancTest[0][0]
		t1 = splitTest[0][0]
		t2 = splitTest[0][1]
		hetAnc = expected_het_anc(freqs,ancTest[0][0])
		hetSplit = expected_het_split(freqs,splitTest[0][0],splitTest[0][1])
		plt.plot(freqs,het/(het+hom),'o',label="data")
		plt.plot(freqs,hetAnc,'r',label="anc, t = %f"%tAnc)
		plt.plot(freqs,hetSplit,'y',label="split, t1 = %f t2 = %f"%(t1,t2))
		plt.xlabel("Frequency")
		plt.ylabel("Proportion of het sites")
		plt.legend()
	return ancTest,splitTest

def test_and_plot_GL():
	return 0

def generate_genotypes(n):
	n -= 1 #NB: This is just because Python is dumb about what n means
	GTs = [[0],[1],[2]]
	for i in range(n):
		newGTs = []
		for GT in GTs:
			for j in (0,1,2):	
				newGT = cp.deepcopy(GT)
				newGT.append(j)
				newGTs.append(newGT)
		GTs = newGTs
	return np.array(GTs)

def generate_Q(n):
	Q = np.zeros((n,n))
	#NB: indexing is weird b/c Python. 
	#In 1-offset, Qii = -i*(i-1)/2, Qi,i-1 = i*(i-1)/2
	for i in range(1,n+1):
		Q[i-1,i-1] = -i*(i-1)/2
		Q[i-1,i-2] = i*(i-1)/2
	return Q

def generate_Qd(n):
	Q = np.zeros((n,n))
	for i in range(1,n+1):
		Q[i-1,i-1] = -i*(i+1)/2
		Q[i-1,i-2] = i*(i-1)/2
	return Q

#NB: Should be freq PER locus
def generate_x(freq,n):
	pows = range(1,n+1)
	xMat = np.array(map(lambda x: np.array(x)**pows,freq))
	return np.transpose(xMat)

def compute_Ey(freq,n,t1,t2):
	Qd = generate_Qd(n)
	Q = generate_Q(n)
	x = generate_x(freq,n)
	backward = expma(Qd*t1,x)
	Ey = np.vstack((np.ones(len(freq)),expma(Q*t2,backward)))
	return Ey

#NB: this does NOT include the combinatorial constant 
def compute_sampling_probs(Ey):
 	n = Ey.shape[0]-1 #NB: number of haploids, -1 because of the row of 1s at the top...
	numFreq = Ey.shape[1]
	probs = []
	for j in range(numFreq):
		probs.append([])
		for k in np.arange(n+1): #all possible freqs, including 0 and 1
		 	i = np.arange(0,n-k+1)
			cur_prob = (-1)**i*sp.binom(n-k,i)*Ey[i+k,j]
			cur_prob = np.sum(cur_prob)
			probs[-1].append(cur_prob)
	return np.array(probs)

#NB: Takes the WHOLE matrix of genotypes
#reads is an array where each row is a sample, reads[:,0] is ancestral reads, reads[:,1] is derived reads at that site
def compute_read_like(reads,GTs):
	p = np.array([0,.5,1])
	read_like = []
	#Hack to deal with the fact that some freqs may not have multiple sites...
	try:
		der = reads[:,1]
		total = reads[:,0]+reads[:,1]
	except IndexError:
		der = reads[1]
		total = reads[0]+reads[1]
	for GT in GTs:
		cur_likes = np.product(st.binom.pmf(der,total,p[GT]))
		read_like.append(cur_likes)
	return np.array(read_like)

#NB: Sampling prob is just for ONE frequency in this case
def compute_genotype_sampling_probs(sampling_prob, GTs):
	GT_prob = map(lambda GT: 2**sum(GT==1)*sampling_prob[sum(GT)],GTs)
	return np.array(GT_prob)

#reads is a list of arrays, sorted by freq
##the first level corresponds to the freqs in freq
##within each frequency, there are arrays of reads that can be passed to compute_read_like
def compute_GT_like(reads,freq,t1,t2):
	if reads[0][0].ndim == 1:
		n_diploid = 1
	else:
		n_diploid = len(reads[0][0])
	n_haploid = 2*n_diploid
	GTs = generate_genotypes(n_diploid)	
	Ey = compute_Ey(freq,n_haploid,t1,t2)
	sampling_prob = compute_sampling_probs(Ey)
	per_site_like = []
	for i in range(len(freq)):
		GT_prob = compute_genotype_sampling_probs(sampling_prob[i,:],GTs)
		for j in range(len(reads[i])):
			read_like = compute_read_like(reads[i][j],GTs)
			cur_prob = sum(read_like*GT_prob)
			per_site_like.append(cur_prob)	
	return np.log(per_site_like)

