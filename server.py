from flask import Flask, render_template, redirect, url_for, request, session, flash
from mysqlLib import MySQL_Conn
from pprint import pprint
from helperLib import convertDay, User
import os


app = Flask(__name__)

connection = MySQL_Conn.getInstance('healthkart', 'root')
user = User()

@app.route('/login')
def home2():	#add
	if not session.get('logged_in'):
		return render_template('loginpage.html')
	else:
		uname = user.getName()

		if uname[0] == "P":
			return redirect(url_for('patient_home'))
			

		elif uname[0] == "E":
			if connection.connect():
				occp = connection.execute("select Occupation from employees \
					where EmployeeID = '%s'" %uname);

				print(occp, occp[0][0])

				if occp[0][0] == "D":
					# return render_template("path to patient dashboard")
					return "Proceed to doctor login " + str(user.getName())

				else:
					return "Dashboard not Ready!"

@app.route("/")
def homePage():
	return render_template("homepage.html")

@app.route("/signup", methods = ['GET', 'POST'])
def signup():
	return render_template("signup_page.html")

@app.route("/signupEntry", methods=['GET', 'POST'])
def signupCheck():
	import datetime

	name = request.form['name']
	gender = request.form['gender']
	dob = request.form['DOB']
	house = request.form['HouseNo']
	street = request.form['Street']
	city = request.form['city']
	district = request.form['District']
	state = request.form['State']
	pincode = request.form['Pincode']
	contactNo = request.form['contactNo']
	BloodGroup = request.form['BloodGroup']
	ptype = request.form['type']

	if datetime.datetime.strptime(dob, '%Y-%m-%d').date() > datetime.date.today():
		flash(f'Invalid DOB')
		return redirect(url_for('signup'))

	if len(pincode)!=6 or not pincode.isdigit():
		flash(f'Invalid Pincode')
		return redirect(url_for('signup'))

	if len(contactNo)!=10 or not contactNo.isdigit():
		flash(f'Invalid Phone Number')
		return redirect(url_for('signup'))

	if BloodGroup not in ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']:
		flash(f'Inavlid Blood Group')
		return redirect(url_for('signup'))

	if connection.connect():
		idCount = connection.execute("select count(1) from patients");
		idCount = idCount[0][0]

	id_int = str(idCount+1)
	pid = "P" + "0"*(4-len(id_int)) + id_int

	if connection.connect(): 
		query = "insert into patients values('%s', '%s', '%s', '%s', '%s', '%s', '%s', \
		'%s', '%s', '%s', '%s', '%s', '%s')" %(pid, name, house, street, city, state, \
			district, pincode, contactNo, BloodGroup, dob, gender, ptype)
		connection.execute(query, -1)
		connection.execute("insert into Logins value('%s', SHA2('%s', 256))" %(pid, "pass" + id_int), -1)
		flash(f'Signed up successfully! Patient ID is {pid}. Login to Continue', 'success')
		return redirect(url_for('home2'))

	return redirect(url_for('homepage'))



@app.route("/loginCheck", methods=['GET', 'POST'])
def login():

	username = request.form['username']
	password = request.form['password']
	# print(username, password)
	if connection.connect():
		rec = connection.execute("select count(1) from Logins\
		 where UserID = '%s' and Password = SHA2(\""'%s'"\", 256)" %(username, password))

	if rec[0][0] == 1:
		user.update(username)
		# print(user.getName())
		session['logged_in'] = True
	else:
		flash(f'Invalid UserID or Password')
	return home2()



@app.route("/patient")
def patient_home():
	import datetime
	patientID = user.getName()

	if connection.connect():
		rec = connection.execute("select visits.VisitDate, doctors.DoctorName, doctors.DepartmentName, \
			visits.DoctorRemarks, medrecommended.MedicineName, testsrecommended.Testname from visits \
			join medrecommended on visits.visitID = medrecommended.visitID join testsrecommended on \
			visits.visitID = testsrecommended.visitID join doctors on visits.DoctorID = doctors.DoctorID \
			where PatientID = '%s' order by (VisitDate)" %(user.getName()))

	# TODO: Multiple medicines/tests list -- correct
	history = rec
	return render_template("patient_home.html", patientID = patientID, history = history)

@app.route("/patient/medicine_info")
def patient_med_info():
	patientID = user.getName()
	if connection.connect():
		meds = connection.execute("select MedicineName, SaltName, Cost from medicines join contains \
			on medicines.MedicineID = contains.MedicineID join salts on contains.SaltID = salts.SaltID\
			 group by MedicineName")

	# meds = [['med name','salts','200'], ['med name','salts','200']] #name of med, salts, cost
	return render_template("medicine_info.html", patientID = patientID, medicines = meds)

@app.route("/patient/test_info")
def patient_test_info():
	patientID = user.getName()
	if connection.connect():
		tests = connection.execute("select TestName, TestDescription, TestCost from labtests")
	# tests = [['test name','desc','200'], ['test name','desc','200']] #name, desc, cost
	return render_template("test_info.html", patientID = patientID, tests = tests)

@app.route("/patient/test_reports")
def patient_test_reports():
	#Medical history - date, doc dep, doc name, rerks, tests, medicines
	#date, test_name, results, normal_result, normal/abnormal
	patientID = user.getName()
	if connection.connect():
		test_rep = connection.execute("select visits.VisitDate, test_reports.TestName, test_reports.TestResult, \
			testnormalresults.RangeLow,testnormalresults.RangeHigh from test_reports join visits on\
			test_reports.VisitID = visits.VisitID join testnormalresults\
			on test_reports.TestName = testnormalresults.TestName where\
			visits.PatientID = '%s' and \
			testnormalresults.AgeLow <= (select(FLOOR(DATEDIFF(NOW(), DOB)/365))\
			from patients where patients.PatientID = '%s') and\
			testnormalresults.AgeHigh >= (select(FLOOR(DATEDIFF(NOW(), DOB)/365))\
			from patients where patients.PatientID = '%s') and (testnormalresults.Gender = (select Gender\
			from patients where patients.PatientID = '%s') or testnormalresults.Gender = 'B')\
			ORDER BY (visits.VisitDate);" %(patientID, patientID, patientID, patientID))
		# print("quey")

	# print("hello!!")
	test_reports = []
	for i in range(len(test_rep)):
		temp = []
		for j in test_rep[i]:
			temp.append(j)
		test_reports.append(temp)
		if test_rep[i][-3]<=test_rep[i][-1] and test_rep[i][-3]>=test_rep[i][-2]:
			res = "Normal"
		else:
			res = "Abnormal"

		test_reports[i][-2] = str(test_rep[i][-2]) + "-" + str(test_rep[i][-1])
		test_reports[i][-1] = res
		
	return render_template("test_reports.html", patientID = patientID, test_reports = test_reports)


@app.route("/patient/edit_profile", methods=['GET', 'POST'])
def patient_edit_profile():
	return render_template("index.html", patientID = patientID, patient_name = patient_name)

@app.route("/patient/book_appointment", methods=['GET', 'POST'])
def patient_book_appointment():
	patientID = user.getName()
	all_depts = []
	if connection.connect():
		depts = connection.execute("select DepartmentName from departments")
		for i in depts:
			all_depts.append(i[0])
	return render_template("book_appointment.html", patientID = patientID, depts = all_depts)

@app.route("/patient/book_appointment_doctor", methods = ['GET', 'POST'])
def choosedoctor():
	if request.method != 'POST':
		return patient_book_appointment()
	dept = request.form['Department']
	doctors = []
	if connection.connect():
		docs = connection.execute("select DoctorID, DoctorName from doctors where DepartmentName = '%s'" %dept)
		for i in docs:
			doctors.append(("Dr. " + i[1], i[0]))
	return render_template("book_appointment_doctor.html", patientID = user.getName(), doctors = doctors, dept = dept)


@app.route("/patient/book_appointment_slot", methods = ['GET', 'POST'])
def book_slot():
	if request.method != 'POST':
		return patient_book_appointment()

	import datetime

	appointment_details = request.form['Doctor']
	# print(appointment_details)
	appointment_details = appointment_details.split(';')
	dept = appointment_details[1]
	doctor = appointment_details[0]
	did = appointment_details[-1]

	cur_date = datetime.date.today()
	cur_day = cur_date.weekday()
	iter_date = cur_date
	iter_day = cur_day
	one_day = datetime.timedelta(days=1)
	count = cur_day
	days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

	available_slots = []

	slot_dict = dict()

	if connection.connect():
		slots = connection.execute("select * from doctor_availability_chart where DoctorID = '%s'" %did)

	# print(slots)
	for i in slots:
		startT = (i[2].seconds)//60
		endT = (i[3].seconds)//60
		if i[1] in slot_dict:
			slot_dict[i[1]].append(tuple((startT, endT)))

		else:
			slot_dict[i[1]] = [tuple((startT, endT))]

	while count <= 13:
		day_conv = convertDay(days[iter_day])

		if day_conv in slot_dict:
			button = []
			button.append(str(iter_date)+" "+days[iter_day])

			for t in slot_dict[day_conv]:
				# print(t)
				start_time = t[0]
				end_time = t[1]
				slots = (end_time - start_time)//20	#calculate from start and end dates

				appointments = connection.execute("select SlotNumber from appointments \
					where DoctorID = '%s' and VisitDate = '%s'" %(did, iter_date))
				appointments = [i[0] for i in appointments]

				# print(appointments)

				sttime = start_time
				for i in range(slots):
					# print(i+1, appointments, (i+1) not in appointments)
					if (i+1) not in appointments:
						sttimeh = sttime//60
						sttimem = sttime%60
						amPm = "AM"
						sttimem = str(sttimem)
						if len(sttimem)<2:
							sttimem += "0"
						if sttimeh>12:
							sttimeh -= 12
							amPm = "PM"
						if sttimeh == 12:
							amPm = "PM"
						button.append(str(sttimeh) + ":" + sttimem + " " + amPm)
					sttime = start_time + 20*(i + 1)

				available_slots.append(button)

		iter_date += one_day
		iter_day = iter_date.weekday()
		count += 1

	return render_template("book_appointment_slot.html", dept = dept, doctor = doctor, 
							dID = did, available_slots = available_slots, patientID = user.getName())



@app.route("/patient/slot_booked", methods = ['GET', 'POST'])
def slot_booked():
	import datetime

	if request.method != 'POST':
		return patient_book_appointment()
	doc_day_slot = (request.form["slot_booked"]).split(';')
	dID = doc_day_slot[0]
	doctor = doc_day_slot[1]
	day = doc_day_slot[2].split(" ")
	date = day[0]
	day = day[-1]
	convDay = convertDay(day)
	slot = doc_day_slot[3]

	if connection.connect():
		start_time = connection.execute("select StartTime from doctor_availability_chart where\
		 DoctorID = '%s' and Day = '%s'" %(dID, convDay))
		start_time = start_time[0][0].seconds

		start_time_m = start_time//60
		temp_time = slot.split(" ")
		temp_time_t = temp_time[0].split(":")
		time_h = int(temp_time_t[0])
		time_min = int(temp_time_t[1])

		total = time_h*60 + time_min

		# print(start_time_m, total)
		if temp_time[-1] == "PM" and time_h != 12:
			total += 720

		slot_num = (total-start_time_m)//20 + 1

		cnt = connection.execute("select count(1) from appointments")
		cnt = cnt[0][0]
		cnt+=1
		cnt = str(cnt)

		connection.execute("insert into appointments values ('%s', '%s', '%s', '%s', '%s', %d)" \
			%(cnt, user.getName(), dID, date, convDay, slot_num), -1)


	return render_template("slot_booked.html", doctor = doctor, day = doc_day_slot[2],\
	 slot = slot, patientID = user.getName())





#Change html for appointments
#check booked appoints - booked appointment list with cancel

#later = indented medicine tab


@app.route("/doctors")
def doctor_home():
	return 0
	# view today's schedule

@app.route("/doctors/week_schedule")
def doctor_schedule():
	return 0
	# week

@app.route("/doctors/medicine_info")
def doc_med_info():
	return 0

@app.route("/doctors/test_info")
def doc_test_info():
	return 0

@app.route("/doctor/check_patient_record")
def doc_check_record():
	"""
	patient name
	date
	doc name
	doc dept
	doc remarks
	"""
	table = [['a','b','c'], ['d','e','f']]
	return 0

@app.route("/doctors/patient_diagnose")
def doc_patient_diagnose():
	#form to fill in patient diagnose
	"""
	FLASK FORM Expiry date everyting etc etc
	patient id
	remarks
	meds
	tests
	"""
	return 0

@app.route("/doctors/edit_profile")
def edit_profile():
	"""
	update address
	contact number
	change password
	"""
	return 0


if __name__ == "__main__":
	app.secret_key = os.urandom(12)
	app.run(debug=True)

# PatientID | DoctorID | VisitDate  | VisitDay | SlotNumber