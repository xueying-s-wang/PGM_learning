import numpy as np
from itertools import chain

burnin, maxit, sample_step, threshold = 50,5000,1,0.5
alpha= [[90,10],[90,10]]
beta = [10,10]
sample_size = maxit/sample_step - burnin/sample_step

sid2double, sid2source = {}, {} # double - entity,value, sid mapping source
entity2value2truth, entity2value2sid = {},{}
# read in rawdata and format
fr = open('rawdb0.txt','rb')
for line in fr: 
	arr = line.strip('\n').split('\t')
	sid, source = int(arr[3]), arr[2]
	entity,value = arr[0],arr[1]
	# build sid-ev and sid-src
	if sid not in sid2source:
		sid2source[sid]=source
		sid2double[sid]=set() # the operation (x in z) is faster when using set than list.
	sid2double[sid].add((entity,value)) # [] is not hasable while () is.
	# build the initial fact table $entity2value2truth$
	if entity not in entity2value2truth:
		entity2value2truth[entity]={}
	if value not in entity2value2truth[entity]:
		t = np.random.uniform(0,1)
		entity2value2truth[entity][value] = (t >= 0.5)
	# pre-claim table: fact-sid
	if entity not in entity2value2sid:
		entity2value2sid[entity]={}
	if value not in entity2value2sid[entity]:
		entity2value2sid[entity][value]=[]
	entity2value2sid[entity][value].append(sid)
fr.close()

# claim table with o and t
entity2value2sid2ob_t,n_sto = {},{}
for [entity,value2sid] in entity2value2sid.items():
	sids = entity2value2sid[entity].values()
	for [value,sid] in value2sid.items():
		if entity not in entity2value2sid2ob_t:
			entity2value2sid2ob_t[entity]={}
			# n_sto[entity]={}
		if value not in entity2value2sid2ob_t[entity]:
			entity2value2sid2ob_t[entity][value]={}	
			# n_sto[entity][value]={}
		for s in set(chain(*sids)):
			entity2value2sid2ob_t[entity][value][s] = [0.0,0.0]
			entity2value2sid2ob_t[entity][value][s][0] = ((entity,value) in sid2double[s]) # o
			entity2value2sid2ob_t[entity][value][s][1] = entity2value2truth[entity][value] # initial t
			if s not in n_sto:#fill in the n_sto matrix
				n_sto[s] = [[0, 0], [0, 0]]
			_t = int(entity2value2sid2ob_t[entity][value][s][1])
			_o = int(entity2value2sid2ob_t[entity][value][s][0])
			n_sto[s][_t][_o] += 1

## gibbs sampling 
it = 0
entity2value2prob = {} # probability of each fact 
while it < maxit:
	entity2value2condi={} # conditional distribution of each fact 
	it += 1
	for [entity,value2truth] in entity2value2truth.items():
		if entity not in entity2value2condi:
			entity2value2condi[entity] = {}
		if entity not in entity2value2prob:
			entity2value2prob[entity] = {}
		for [value,truth] in value2truth.items():
			if value not in entity2value2condi[entity]:
				entity2value2condi[entity][value]={}
			if value not in entity2value2prob[entity]:
				entity2value2prob[entity][value] = 0
			entity2value2condi[entity][value][int(truth)] = beta[int(truth)]
			entity2value2condi[entity][value][int(1-truth)] = beta[int(1-truth)]
			#for c in C_f
			for [sid, ob_t] in entity2value2sid2ob_t[entity][value].items():
				o, t = int(ob_t[0]), int(ob_t[1])
				# 
				entity2value2condi[entity][value][int(truth)] *= 1.0 * (n_sto[sid][t][o] - 1 + alpha[t][o]) / \
				(n_sto[sid][t][1] + n_sto[sid][t][0] - 1 + alpha[t][1] + alpha[t][0])
				entity2value2condi[entity][value][int(1-truth)] *= 1.0 * (n_sto[sid][1-t][o] - 1 + alpha[1-t][o]) / \
				(n_sto[sid][1-t][1] + n_sto[sid][1-t][0] - 1 + alpha[1-t][1] + alpha[1-t][0])
			# sample tf from conditional distribution 
			if np.random.uniform(0,1) < 1.0 * (entity2value2condi[entity][value][int(1-truth)]) / \
				(entity2value2condi[entity][value][int(1-truth)] + entity2value2condi[entity][value][int(truth)]):
				entity2value2truth[entity][value] = 1 - truth
				# update counts 
				for [sid, ob_t] in entity2value2sid2ob_t[entity][value].items():
					entity2value2sid2ob_t[entity][value][sid][1] = 1 - truth
					o, t = int(ob_t[0]), int(ob_t[1])
					n_sto[sid][1-t][o] -= 1
					n_sto[sid][t][o] += 1
			# calculate expectation of tf 
			if it > burnin and it % sample_step == 0:
				entity2value2prob[entity][value] += 1.0 * entity2value2truth[entity][value] / sample_size
				print entity2value2prob['HP']

fw = open('sample_output.txt','w')
for [entity, value2prob] in sorted(entity2value2prob.items()):
	for [value, prob] in sorted(value2prob.items()):
		fw.write(entity + ' ' + value + ' ' + str(prob >= threshold))
