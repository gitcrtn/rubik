# rubik note
# Copyright (c) 2015 @Carotene
# 2014.10.28

import sqlite3
import os.path

import os
os.chdir(os.path.dirname(__file__))

import sys
sys.path.append("./libs/bottle")
sys.path.append("./libs/jinja2")
sys.path.append("./libs/markupsafe")

from bottle import Bottle, request, response, redirect, jinja2_template as template

class Data(object):
	def __init__(self):
		self.db_file = "./data.db"
		self.conn = None

	def open(self,initFunc=None):
		if self.conn:
			self.close()
		init = False
		if (initFunc is not None) and not os.path.isfile(self.db_file):
			init = True
		self.conn = sqlite3.connect(self.db_file, isolation_level=None)
		if init:
			initFunc()

	def close(self):
		if self.conn:
			self.conn.close()
			self.conn = None

	def create_table(self,name,format):
		self.conn.execute("create table if not exists %s ( %s )" % (name,format))

	def insert_record(self,table,value):
		self.conn.execute("insert into %s values ( %s )" % (table,value))

	def delete_record(self,table,id):
		print "[rubik_note] delete record: "
		print "[rubik_note]    table:%s, id:%s" % (table,id)
		rcd = self.records(table,where="id=%d" % id)
		if not rcd:
			print "[rubik_note]    id:%d is not exist." % id
			return
		print "[rubik_note]    " + str(rcd[0])
		self.conn.execute("delete from %s where id=%d" % (table,id))

	def update_record(self,table,id,value):
		self.conn.execute("update %s set %s where id=%s" % (table,value,id))

	def max_int(self,table,column,where=None):
		sql = "select max(%s) from %s" % (column,table)
		if where:
			sql += " where " + where
		r = self.conn.execute(sql).fetchone()
		if (r is None) or (r[0] is None):
			return -1
		else:
			return r[0]

	def records(self,table,where=None,sort=None):
		sql = "select * from " + table
		if where:
			sql += " where " + where
		if sort:
			sql += " order by " + sort
		return [row for row in self.conn.execute(sql)]

	def tables(self):
		return [c[0] for c in self.conn.execute("select name from sqlite_master where type='table'").fetchall()]

	def columns(self,table):
		return [d[0] for d in self.conn.execute("select * from " + table).description]

class Rubik(object):
	def __init__(self):
		self.colors = {}
		self.color_ids = {}
		self.cubes = {}
		self.rotations = {}
		self.cubefaces = {}
		self.nulls = {}
		self.columns = {}
		self.parents = {'procedure':'method','step':'procedure','pattern':'step','solution':'pattern'}
		self.children = dict((v,k) for k,v in self.parents.iteritems())
		self.incl_steps = ['procedure','step']
		self.incl_layout = ['procedure','step','pattern']

		self.data = Data()
		self.data.open()
		self.__init_data()
		self.data.close()

	def __init_data(self):
		print "[rubik_note] database initializing & loading ..."

		self.data.create_table("method","id integer, name varchar(255)")
		self.data.create_table("procedure","id integer, name varchar(255), method integer, step_number integer, layout integer")
		self.data.create_table("step","id integer, name varchar(255), procedure integer, step_number integer, layout integer")
		self.data.create_table("pattern","id integer, name varchar(255), step integer, before_layout integer, after_layout integer")
		self.data.create_table("solution","id integer, pattern integer, step_number integer, rotation integer")

		self.data.create_table("color","id integer, name varchar(10)")
		self.data.create_table("rotation","id integer, name varchar(2), vertices varchar(15), degree integer")
		self.data.create_table("cube","id integer, faces integer, color1 integer, color2 integer, color3 integer")
		self.data.create_table("cubeface","id integer, name varchar(3), faces integer")
		self.data.create_table("layout","id integer, x0 integer, x1 integer, y0 integer, y1 integer, z0 integer, z1 integer")
		self.data.create_table("grid",", ".join(["id integer"] + ["\'c%d\' integer" % i for i in xrange(9)]))

		self.__init_colors()
		self.__init_cubes()
		self.__init_rotations()
		self.__init_cubefaces()
		self.__init_grids()
		self.__init_layouts()
		self.__init_columns()

	def __init_columns(self):
		self.columns = {}
		for t in self.data.tables():
			self.columns[t] = self.data.columns(t)

	def __init_layouts(self):
		if self.data.max_int("layout","id") < 0:
			self.data.insert_record("layout", ", ".join(["0"] * 7))

	def __init_grids(self):
		if self.data.max_int("grid","id") < 0:
			self.data.insert_record("grid", ", ".join(["0"] * 10))

	def __init_cubefaces(self):
		if self.data.max_int("cubeface","id") < 25:
			id = 0
			faces = {'1':['121','011','211','101','110','112'],
					'2':['100','201','102','001','010','210','212','012','120','221','122','021'],
					'3':['000','200','202','002','020','220','222','022']}
			for f,v in faces.iteritems():
				for key in v:
					self.data.insert_record("cubeface", "%d, \"%s\", %s" % (id,key,f))
					id += 1
		self.cubefaces = {}
		for row in self.data.records("cubeface"):
			self.cubefaces[row[1]] = row[2]

	def __init_colors(self):
		if self.data.max_int("color","id") < 6:
			self.data.insert_record("color", "0, \'null\'")
			self.data.insert_record("color", "1, \'white\'")
			self.data.insert_record("color", "2, \'blue\'")
			self.data.insert_record("color", "3, \'red\'")
			self.data.insert_record("color", "4, \'orange\'")
			self.data.insert_record("color", "5, \'green\'")
			self.data.insert_record("color", "6, \'yellow\'")
		self.colors = {}
		self.color_ids = {}
		for row in self.data.records("color"):
			self.colors[row[1]] = row[0]
			self.color_ids[row[0]] = row[1]

	def __init_cubes(self):
		if self.data.max_int("cube","id") < 28:
			pair_names = [('white','yellow'),('green','blue'),('red','orange')]
			layout_pairs = []
			for p in pair_names:
				layout_pairs.append((self.colors[p[0]],self.colors[p[1]]))

			# center cube (null)
			id = 0
			self.data.insert_record("cube", str(id) + ", 1, 0, 0, 0")
			id += 1

			edge_sets = []
			corner_sets = []
			for a in xrange(1,7):
				# center cube
				self.data.insert_record("cube", str(id) + ", 1, %d, 0, 0" % a)
				id += 1
				for p in layout_pairs:
					if a in p:
						skip_colors = p
						break
				for b in xrange(1,7):
					if b in skip_colors:
						continue
					edge = set([a,b])
					if edge not in edge_sets:
						edge_sets.append(edge)
					for p in layout_pairs:
						if b in p:
							skip_colors_2 = skip_colors + p
							break
					for c in xrange(1,7):
						if c in skip_colors_2:
							continue
						corner = set([a,b,c])
						if corner not in corner_sets:
							corner_sets.append(corner)

			# edge cube
			self.data.insert_record("cube", str(id) + ", 2, 0, 0, 0")
			id += 1
			for e in edge_sets:
				self.data.insert_record("cube", str(id) + ", 2, %d, %d, 0" % tuple(e))
				id += 1

			# corner cube
			self.data.insert_record("cube", str(id) + ", 3, 0, 0, 0")
			id += 1
			for c in corner_sets:
				self.data.insert_record("cube", str(id) + ", 3, %d, %d, %d" % tuple(c))
				id += 1

		self.cubes = {}
		for row in self.data.records("cube"):
			id = row[0]
			faces = row[1]
			cube_keys = []
			for i in xrange(faces):
				cube_keys.append(str(row[2+i]))
			self.cubes[','.join(cube_keys)] = id

		self.nulls = {}
		null = str(self.colors['null'])
		self.nulls = {'1':self.cubes[null], '2':self.cubes[','.join([null,null])], '3':self.cubes[','.join([null,null,null])]}

	def __init_rotations(self):
		if self.data.max_int("rotation","id") < 26:
			names = ['F', 'B', 'R', 'L', 'U', 'D', 'S', 'M', 'E']
			postfixs = ['', '\'', '2']
			degrees = [90, -90, 180]
			vertices = ['002,202,222,022',
						'000,200,220,020',
						'202,200,220,222',
						'002,000,020,022',
						'222,220,020,022',
						'202,200,000,002',
						'221,201,001,021',
						'120,100,102,122',
						'212,210,010,012']
			id = 0
			for i,n in enumerate(names):
				for j,pf in enumerate(postfixs):
					self.data.insert_record("rotation", "%d, \"%s\", \"%s\", %d" % (id,n+pf,vertices[i],degrees[j]))
					id += 1

		self.rotations = {}
		for row in self.data.records("rotation"):
			id = row[0]
			name = row[1]
			vertex = row[2]
			degree = row[3]
			self.rotations[vertex] = {'name':name,'degree':degree,'id':id}

	def update(self,table,entity):
		import copy
		cols = copy.deepcopy(self.columns[table])
		cols.remove('id')
		values = ",".join(["%s=%s" % (c,self.__str(entity[c])) for c in cols])
		self.data.open(initFunc=self.__init_data)
		self.data.update_record(table,entity['id'],values)
		self.data.close()

	def __str(self,value):
		import types
		if type(value) in [types.StringType,types.UnicodeType]:
			return '\"%s\"' % value
		else:
			return str(value)

	def add(self,table,entity,close=True):
		cols = self.columns[table]
		values = ",".join([self.__str(entity[c]) for c in cols])
		if close: self.data.open(initFunc=self.__init_data)
		self.data.insert_record(table,values)
		if close: self.data.close()

	def template(self,table,parent_id=None,close=True):
		cols = self.columns[table]
		parent = None
		if table in self.parents.keys():
			parent = self.parents[table]
		if (parent is not None) and (parent_id is None):
			print 'Rubik.template() need parent_id for "%s".' % table
			raise
		ret = {}
		if close: self.data.open(initFunc=self.__init_data)
		for c in cols:
			if c == 'id':
				ret[c] = self.data.max_int(table,"id") + 1
			elif c == 'name':
				ret[c] = 'noname'
			elif c == parent:
				ret[c] = parent_id
			elif c == 'step_number' and (parent is not None):
				ret[c] = self.data.max_int(table,"step_number",where="%s=%d" % (parent,parent_id)) + 1
			else:
				ret[c] = 0
		if close: self.data.close()
		return ret

	def delete(self,table,id):
		self.data.open(initFunc=self.__init_data)
		self.data.delete_record(table,id)
		if table not in self.children.keys():
			return
		next_target_table = self.children[table]
		next_targets = self.list(next_target_table,parent_id=id,close=False)
		while next_target_table in self.children.keys():
			target_table = next_target_table
			next_target_table = self.children[target_table]
			targets = next_targets
			next_targets = []
			for t in targets:
				next_targets += self.list(next_target_table,parent_id=t['id'],close=False)
				self.data.delete_record(target_table,t['id'])
		for t in next_targets:
			self.data.delete_record(next_target_table,t['id'])
		self.data.close()

	def list(self,table,parent_id=None,close=True):
		if close: self.data.open(initFunc=self.__init_data)
		cols = self.columns[table]
		args = {'table':table}
		if (parent_id is not None) and (table in self.parents.keys()):
			args['where'] = "%s=%d" % (self.parents[table],parent_id)
		if table in self.incl_steps:
			args['sort'] = "step_number"
		ret = [dict((k,r[i]) for i,k in enumerate(cols)) for r in self.data.records(**args)]
		if close: self.data.close()
		return ret

	def get(self,table,id):
		self.data.open(initFunc=self.__init_data)
		r = self.data.records(table, where='id=%d' % id)
		if r:
			rr = r[0]
			cols = self.columns[table]
			self.data.close()
			ret = {}
			for i,c in enumerate(cols):
				ret[c] = rr[i]
			return ret
		else:
			self.data.close()
			return None

	# for only layout & grid
	def get_id(self,table,values):
		self.data.open(initFunc=self.__init_data)
		cols = self.data.columns(table)
		cols.remove("id")
		count = len(cols)
		wheres = []
		for i in xrange(count):
			wheres.append("%s=%s" % (cols[i],values[i]))
		where = " and ".join(wheres)
		rcd_id = self.data.max_int(table,"id",where=where)
		if rcd_id == -1:
			tmpl = self.template(table,close=False)
			rcd_id = tmpl["id"]
			print "[rubik_note] new %s id: %s" % (table,rcd_id)
			for i in xrange(count):
				tmpl[str(cols[i])] = values[i]
			self.add(table,tmpl,close=False)
			self.data.close()
			return rcd_id
		else:
			self.data.close()
			return rcd_id

class Server(object):
	def __init__(self,host,port):
		self.rubik = Rubik()
		self.__host = host
		self.__port = port
		self.__app = Bottle()
		self.__route()

	def __route(self):
		self.__app.route('/rubik', callback=self.__methods)
		self.__app.route('/rubik/method/<method_id:int>', callback=self.__procedures)
		self.__app.route('/rubik/procedure/<procedure_id:int>', callback=self.__steps)
		self.__app.route('/rubik/step/<step_id:int>', callback=self.__patterns)
		self.__app.route('/rubik/new/<datatype>', callback=self.__no_parent_new)
		self.__app.route('/rubik/<parent_datatype>/<parent_id:int>/new/<datatype>', callback=self.__new)
		self.__app.route('/rubik/<datatype>/<id:int>/edit', callback=self.__edit)
		self.__app.post('/rubik/done', callback=self.__done)

	def __methods(self):
		result = {'name':'method','up':None, 'has_step':False, 'has_layout':False}
		result['container'] = self.rubik.list("method")
		return template('index', result = result)

	def __procedures(self,method_id):
		method_rcd = self.rubik.get("method",method_id)
		if method_rcd is None:
			# no exist id  or  database deleted & reset
			return redirect("/rubik")
		method_name = method_rcd['name']
		result = {'name':'procedure', 'parent_name':'method', 'parent_id':method_id, 'up':"/rubik", 'has_step':True, 'has_layout':True}
		result['subtitle'] = 'method: ' + method_name
		result['container'] = self.rubik.list("procedure",parent_id=method_id)
		for r in result['container']:
			r['layout_color'] = self.__encode_layout_color_base64(r['layout'])
		#print result['subtitle']
		return template('index', result = result)

	def __steps(self,procedure_id):
		procedure_rcd = self.rubik.get("procedure",procedure_id)
		if procedure_rcd is None:
			# no exist id  or  database deleted & reset
			return redirect("/rubik")
		method_rcd = self.rubik.get("method",procedure_rcd['method'])
		result = {'name':'step', 'parent_name':'procedure', 'parent_id':procedure_id, 'up':"/rubik/method/"+str(procedure_rcd['method']), 'has_step':True, 'has_layout':True}
		result['subtitle'] = 'method: %s,<br>procedure: %d. %s' % (method_rcd['name'],procedure_rcd['step_number']+1,procedure_rcd['name'])
		result['container'] = self.rubik.list("step",parent_id=procedure_id)
		for r in result['container']:
			r['layout_color'] = self.__encode_layout_color_base64(r['layout'])
		#print result['subtitle']
		return template('index', result = result)

	def __patterns(self,step_id):
		step_rcd = self.rubik.get("step",step_id)
		if step_rcd is None:
			# no exist id  or  database deleted & reset
			return redirect("/rubik")
		procedure_rcd = self.rubik.get("procedure",step_rcd['procedure'])
		method_rcd = self.rubik.get("method",procedure_rcd['method'])
		result = {'name':'pattern', 'parent_name':'step', 'parent_id':step_id, 'up':"/rubik/procedure/"+str(step_rcd['procedure']), 'has_step':False, 'has_layout':True}
		result['subtitle'] = 'method: %s,<br>procedure: %d. %s,<br>step: %d. %s' % (method_rcd['name'],procedure_rcd['step_number']+1,procedure_rcd['name'],step_rcd['step_number']+1,step_rcd['name'])
		result['container'] = self.rubik.list("pattern",parent_id=step_id)
		#print result['subtitle']
		return template('index', result = result)

	def __decode_layout_color_base64(self,data_string):
		buf = [ord(c) for c in data_string.decode('base64')]
		ret = []
		for i in xrange(0,21,3):
			tmp = 0
			tmp += buf[i] + (buf[i+1] << 8) + (buf[i+2] << 16)
			for j in xrange(8):
				ret.append((tmp & (7 << (j*3))) >> (j*3))   # 7 == 0x0111
		ret.pop(-1)
		ret.pop(-1)
		return ret

	def __encode_colors_base64(self,colors):
		import base64
		count = len(colors)
		if count != 54:
			print "colors must be 54 numbers."
			raise
		buf = ""
		colors += [0,0]  # add delta. ( 8 - 54 % 8 == 2)
		for i in xrange(0,count,8):
			tmp = 0
			for j in xrange(8):
				tmp += ((colors[i+j] & 7) << (j*3))
			buf += chr(tmp & 255)
			buf += chr((tmp & (255 << 8)) >> 8)
			buf += chr((tmp & (255 << 16)) >> 16)
		return base64.b64encode(buf)

	def __encode_layout_color_base64(self,layout_id):
		rcd = self.rubik.get("layout",layout_id)
		grids = {}
		buf = []
		layout_columns = self.rubik.columns["layout"]
		grid_columns = self.rubik.columns["grid"]
		for lc in layout_columns:
			if lc == 'id':
				continue
			if not grids.has_key(rcd[lc]):
				grids[rcd[lc]] = self.rubik.get("grid",rcd[lc])
			for gc in grid_columns:
				if gc == 'id':
					continue
				buf.append(grids[rcd[lc]][gc])
		return self.__encode_colors_base64(buf)

	def __no_parent_new(self,datatype):
		return self.__new(datatype,None,None)

	def __new(self,datatype,parent_datatype,parent_id):
		result = {'name':datatype,'parent_name':parent_datatype,'parent_id':parent_id,'back':"/rubik",'up':None}
		if parent_datatype is not None:
			result['back'] += "/%s" % result['parent_name']
		else:
			result['parent_name'] = ""
		if parent_id is not None:
			result['back'] += "/%s" % result['parent_id']
		else:
			result['parent_id'] = -1
		return template('new', result = result)

	def __edit(self,datatype,id):
		result = {'name':datatype,'back':"/rubik",'up':None}
		entity = self.rubik.get(datatype,id)
		if entity is None:
			# no exist id  or  database deleted & reset
			return redirect("/rubik")

		result['entity'] = entity

		if datatype in self.rubik.parents.keys():
			result['back'] += "/%s/%s" % (self.rubik.parents[datatype],entity[self.rubik.parents[datatype]])

		result['layout_colors'] = []
		if datatype in self.rubik.incl_layout:
			if datatype=="pattern":
				result['layout_colors'].append(self.__encode_layout_color_base64(result['entity']['before_layout']))
				result['layout_colors'].append(self.__encode_layout_color_base64(result['entity']['after_layout']))
			else:
				result['layout_colors'].append(self.__encode_layout_color_base64(result['entity']['layout']))

		result['steps'] = self.__get_step_selection(datatype,entity)

		return template('edit', result = result)

	def __get_step_selection(self,datatype,entity):
		if datatype not in ["procedure","step"]:
			return []
		records = self.rubik.list(datatype,parent_id=entity[self.rubik.parents[datatype]])
		return range(len(records))

	def __done(self):
		datatype = request.forms.get('type')
		back = request.forms.get('back')
		page = request.forms.get('page')
		name = request.forms.get('name')

		if page == "new":
			parent_name = request.forms.get('parent_name')
			parent_id = int(request.forms.get('parent_id'))

			if not name:
				import datetime
				name = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
				#pageaddr = "/rubik"
				#if parent_id != "-1":
				#	pageaddr += "/%s/%s" % (parent_name,parent_id)
				#pageaddr += "/%s/%s" % (page,datatype)
				#return redirect(pageaddr)

			entity = self.rubik.template(datatype,parent_id=parent_id)
			entity['name'] = name
			self.rubik.add(datatype,entity)

		elif page == "edit":
			id = int(request.forms.get('id'))
			if request.forms.get('del'):
				self.rubik.delete(datatype,id)
			else:
				entity = self.rubik.get(datatype,id)

				if entity is None:
					# no exist id  or  database deleted & reset
					return redirect("/rubik")

				step = request.forms.get('step')
				if step is not None:
					self.__update_step(datatype,entity,int(step))

				layout_colors = request.forms.get('layout_colors')

				entity = self.rubik.get(datatype,id)

				entity['name'] = name

				if layout_colors:
					colors = layout_colors.split(":")
					count = len(colors)
					for i in xrange(count):
						buf = self.__decode_layout_color_base64(colors[i])
						g_ids = []
						for j in xrange(6):
							bufs = [buf[j*9+k] for k in xrange(9)]
							g_ids.append(self.rubik.get_id("grid",bufs))
						l_id = self.rubik.get_id("layout",g_ids)
						if count==1:
							entity["layout"] = l_id
						elif i==0:
							entity["before_layout"] = l_id
						else:
							entity["after_layout"] = l_id

				self.rubik.update(datatype,entity)

		redirect(back)

	def __update_step(self,datatype,entity,step):
		records = self.rubik.list(datatype,entity[self.rubik.parents[datatype]])
		if not len(records):
			return
		for i,r in enumerate(records):
			r['step_number'] = i
			self.rubik.update(datatype,r)

		entity = self.rubik.get(datatype,entity['id'])
		now_step = entity['step_number']

		if step == now_step:
			return

		for i,r in enumerate(records):
			if step > now_step:
				if (i <= now_step) or (i > step):
					continue
				r['step_number'] -= 1
				self.rubik.update(datatype,r)
			else:
				if (i < step) or (i >= now_step):
					continue
				r['step_number'] += 1
				self.rubik.update(datatype,r)

		entity['step_number'] = step
		self.rubik.update(datatype,entity)

	def start(self):
		self.__app.run(host=self.__host, port=self.__port, reloader=True, debug=True)

if __name__ == '__main__':
	from optparse import OptionParser
	parser = OptionParser()
	parser.add_option("-n", "--host", dest="host", help="hostname", type="string", default="localhost")
	parser.add_option("-p", "--port", dest="port", help="port", type="int", default=8080)
	options, args = parser.parse_args()
	s = Server(options.host,options.port)
	s.start()
