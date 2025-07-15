import os
import pandas as pd
import random
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
from werkzeug.exceptions import NotFound
from werkzeug.utils import secure_filename

# Import models
from models import db, Room, Student, Exam, SeatAllocation

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "seatify_secret_key")

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads/timetable'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configure database
# Use environment variable if available, otherwise use MySQL
mysql_password = os.environ.get('MYSQL_PASSWORD', 'dazzle@mysql')
mysql_user = os.environ.get('MYSQL_USER', 'root')
mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
mysql_db = os.environ.get('MYSQL_DB', 'seatify')
# Use PostgreSQL in Replit, MySQL locally
if os.environ.get('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
else:
    # URL encode the password to handle special characters
    from urllib.parse import quote_plus
    mysql_password_encoded = quote_plus(mysql_password)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql://{mysql_user}:{mysql_password_encoded}@{mysql_host}/{mysql_db}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy with app
db.init_app(app)

# Make sure all models are created
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    """Render the home page"""
    return render_template('index.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """Handle admin login"""
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Static admin credentials
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_fun'))
        else:
            error = 'Invalid username or password'
    
    return render_template('admin-login.html', error=error)

@app.route('/admin_fun')
def admin_fun():
    """Render the admin function selection page"""
    if not session.get('admin_logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('admin_login'))
    
    return render_template('admin_fun.html')

@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    """Handle student login"""
    error = None
    if request.method == 'POST':
        register_number = request.form['username']
        password = request.form['password']
        
        # Look for the student in the database
        student = Student.query.filter_by(register_number=register_number).first()
        
        if student:
            # Password format: first 3 letters of name (lowercase) + 123
            expected_password = student.name[:3].lower() + "123"
            
            if password == expected_password:
                session['student_id'] = student.id
                session['register_number'] = student.register_number
                flash('Login successful!', 'success')
                return redirect(url_for('student_dashboard'))
            else:
                error = "Invalid password. Password should be first 3 letters of your name (lowercase) followed by '123'."
        else:
            error = "Student with this register number not found."
    
    return render_template('student-login.html', error=error)

@app.route('/student-dashboard')
def student_dashboard():
    """Render the student dashboard"""
    if not session.get('student_id'):
        flash('Please login first', 'error')
        return redirect(url_for('student_login'))
    
    student_id = session.get('student_id')
    student = Student.query.get(student_id)
    
    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('student_login'))
    
    # Get current date
    current_date = datetime.now().date()
    
    # Get all exams for this student
    allocations = SeatAllocation.query.filter_by(student_id=student_id).all()
    
    exams = []
    for allocation in allocations:
        exam = Exam.query.get(allocation.exam_id)
        room = Room.query.get(allocation.room_id)
        
        if exam and room:
            # Only include future exams
            if exam.date.date() >= current_date:
                exams.append({
                    'date': exam.date,
                    'fn_an': exam.fn_an,
                    'int_ext': exam.int_ext,
                    'subject_code': exam.subject_code,
                    'block_name': room.block_name,
                    'room_number': room.room_no,
                    'floor': room.floor
                })
    
    # Sort exams by date and session (FN before AN)
    exams.sort(key=lambda x: (x['date'], 0 if x['fn_an'] == 'FN' else 1))
    
    # Format dates for display
    for exam in exams:
        exam['date'] = exam['date'].strftime('%Y-%m-%d')
    
    # Get timetable for student's semester
    timetable = None
    timetable_path = None
    
    # Get all timetable files
    timetable_dir = app.config['UPLOAD_FOLDER']
    if os.path.exists(timetable_dir):
        for filename in os.listdir(timetable_dir):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                # Extract semester from filename (e.g., IT-1-S5-dec-2025.jpg -> S5)
                match = re.search(r'S(\d+)', filename)
                if match:
                    file_semester = match.group(1)
                    # Check if this timetable is for student's semester
                    if file_semester == student.semester:
                        # Check if file is within 24 days of upload
                        file_path = os.path.join(timetable_dir, filename)
                        file_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).date()
                        days_old = (current_date - file_modified).days
                        
                        if days_old <= 24:
                            timetable = filename
                            # Update the path to be relative to static folder
                            timetable_path = 'uploads/timetable/' + filename
                            break
    
    return render_template('student-dashboard.html',
                          register_number=student.register_number,
                          student_name=student.name,
                          department=student.department,
                          semester=student.semester,
                          exams=exams,
                          timetable=timetable,
                          timetable_path=timetable_path)

@app.route('/std_data', methods=['GET', 'POST'])
def std_data():
    """Handle student data uploads"""
    if not session.get('admin_logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded!', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected!', 'error')
            return redirect(request.url)
        
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            try:
                # Check if filename follows the required format
                filename = file.filename.split('.')[0]  # Remove extension
                
                if '_' not in filename:
                    flash('Filename must follow format: departmentcode_semester (e.g., CSE_3)', 'error')
                    return redirect(request.url)
                
                department, semester = filename.split('_', 1)
                
                # Read the Excel file
                df = pd.read_excel(file)
                
                # Validate required columns
                if not {'register_number', 'name'}.issubset(df.columns):
                    flash('Excel file must contain "register_number" and "name" columns.', 'error')
                    return redirect(request.url)
                
                # Create a table for this department and semester if doesn't exist
                table_name = f"{department.lower()}_{semester}"
                
                # Process each row in the Excel file
                count = 0
                for _, row in df.iterrows():
                    register_number = str(row['register_number']).strip()
                    name = str(row['name']).strip()
                    
                    # Check if student already exists
                    existing_student = Student.query.filter_by(register_number=register_number).first()
                    
                    if not existing_student:
                        # Create new student
                        student = Student(
                            register_number=register_number,
                            name=name,
                            department=department.upper(),
                            semester=semester
                        )
                        db.session.add(student)
                        count += 1
                
                db.session.commit()
                flash(f'Successfully uploaded {count} new students!', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Invalid file type. Please upload an Excel file (.xlsx, .xls).', 'error')
    
    return render_template('std_data.html')

@app.route('/room_data', methods=['GET', 'POST'])
def room_data():
    """Handle room data uploads"""
    if not session.get('admin_logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded!', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected!', 'error')
            return redirect(request.url)
        
        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            try:
                # Read the Excel file
                df = pd.read_excel(file)
                
                # Validate required columns
                if not {'room_no', 'capacity'}.issubset(df.columns):
                    flash('Excel file must contain "room_no" and "capacity" columns.', 'error')
                    return redirect(request.url)
                
                # Process each row in the Excel file
                new_count = 0
                for _, row in df.iterrows():
                    room_no = str(row['room_no']).strip()
                    capacity = int(row['capacity'])
                    
                    # Check if room already exists
                    existing_room = Room.query.filter_by(room_no=room_no).first()
                    
                    if not existing_room:
                        # Create new room with fixed row/column configuration
                        room = Room(room_no=room_no, capacity=42)  # Force capacity to 42
                        room.row_count = 6  # Fixed at 6 rows
                        room.col_count = 7  # Fixed at 7 columns
                        db.session.add(room)
                        new_count += 1
                    else:
                        # Update existing room with fixed row/column configuration
                        existing_room.capacity = 42  # Force capacity to 42
                        existing_room.row_count = 6  # Fixed at 6 rows
                        existing_room.col_count = 7  # Fixed at 7 columns
                
                db.session.commit()
                flash(f'Successfully processed room data! Added {new_count} new rooms.', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Invalid file type. Please upload an Excel file (.xlsx, .xls).', 'error')
    
    return render_template('room_data.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    """Render the admin dashboard for exam scheduling"""
    if not session.get('admin_logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('admin_login'))
    
    # Get all student tables (departments and semesters)
    tables = []
    students = Student.query.all()
    
    # Get unique department_semester combinations
    dept_sem_set = set()
    for student in students:
        dept_sem_set.add(f"{student.department.lower()}_{student.semester}")
    
    tables = sorted(list(dept_sem_set))
    
    return render_template('admin-dashboard.html', tables=tables)

@app.route('/generate_seat_allocation')
def generate_seat_allocation():
    """Generate and display seat allocation"""
    if not session.get('admin_logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('admin_login'))
    
    # Get parameters from request
    date_str = request.args.get('date')
    fn_an = request.args.get('fn_an')
    int_ext = request.args.get('int_ext')
    subject_code = request.args.get('subject_code')
    tables = request.args.get('tables', '').split(',')
    
    if not all([date_str, fn_an, int_ext, subject_code, tables]):
        flash('All fields are required', 'error')
        return redirect(url_for('admin_dashboard'))
    
    try:
        # Convert date string to datetime object
        date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Create new exam if it doesn't exist
        existing_exam = Exam.query.filter_by(
            date=date,
            fn_an=fn_an,
            int_ext=int_ext,
            subject_code=subject_code
        ).first()
        
        if existing_exam:
            exam = existing_exam
        else:
            # Create a new exam
            exam = Exam(
                date=date,
                fn_an=fn_an,
                int_ext=int_ext,
                subject_code=subject_code
            )
            db.session.add(exam)
            db.session.commit()
        
        # Get all rooms
        rooms = Room.query.all()
        
        if not rooms:
            flash('No rooms found. Please add rooms first.', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Get students for each selected department+semester
        department_students = {}
        for table in tables:
            if not table:  # Skip empty strings
                continue
            
            try:
                # Split table name into department and semester
                department, semester = table.split('_', 1)
                
                # Get students for this department and semester
                students = Student.query.filter_by(
                    department=department.upper(),
                    semester=semester
                ).all()
                
                if students:  # Only add if there are students
                    department_students[department.upper()] = students
                
            except Exception as e:
                flash(f'Error loading students from {table}: {str(e)}', 'error')
        
        # If no students found, show error
        if not department_students:
            flash('No students found for the selected classes.', 'error')
            return redirect(url_for('admin_dashboard'))

        # Initialize room allocations and tracking variables
        room_allocations = {}
        room_counts = {}
        room_seat_numbers = {}
        room_filled_columns = {}  # Track which columns are filled in each room
        room_column_counts = {}  # Track number of students in each column
        room_column_classes = {}  # Track which class (dept+sem) is in each column
        allocated_students = set()
        students_processed = 0

        # Initialize room tracking
        for room in rooms:
            room_allocations[room.id] = []
            room_counts[room.id] = 0
            room_seat_numbers[room.id] = 1
            room_filled_columns[room.id] = set()  # Initialize empty set for filled columns
            room_column_counts[room.id] = {col: 0 for col in range(1, 8)}  # Initialize column counts
            room_column_classes[room.id] = {col: None for col in range(1, 8)}  # Initialize column classes

        # First, check for existing allocations on the same date and session
        existing_allocations = SeatAllocation.query.join(Exam).filter(
            Exam.date == date,
            Exam.fn_an == fn_an
        ).all()

        # Mark filled columns and their classes
        for allocation in existing_allocations:
            student = Student.query.get(allocation.student_id)
            room_filled_columns[allocation.room_id].add(allocation.col)
            room_counts[allocation.room_id] += 1
            room_column_counts[allocation.room_id][allocation.col] += 1
            # Store both department and semester as class identifier
            room_column_classes[allocation.room_id][allocation.col] = f"{student.department}_{student.semester}"

        # Check if this is the first allocation for this session
        is_first_allocation = len(existing_allocations) == 0

        # Process each department's students
        for dept, students in department_students.items():
            for student in students:
                if student.id in allocated_students:
                    continue

                # Find the best room and column for allocation
                best_room = None
                best_col = None
                best_row = 0

                # First, try to find space in partially filled rooms
                for room in rooms:
                    if room_counts[room.id] >= 42:
                        continue

                    # Define column priority order
                    odd_columns = [1, 3, 5, 7]  # Priority order for odd columns
                    even_columns = [2, 4, 6]    # Priority order for even columns
                    
                    # First try partially filled odd columns
                    for col in odd_columns:
                        if col in room_filled_columns[room.id]:
                            # Check if column is not full (less than 6 students)
                            if room_column_counts[room.id][col] < 6:
                                # Check if adjacent columns have students from the same class
                                adjacent_cols = [col - 1, col + 1]
                                has_same_class_adjacent = False
                                current_class = f"{dept}_{student.semester}"
                                
                                for adj_col in adjacent_cols:
                                    if 1 <= adj_col <= 7:  # Check if adjacent column is valid
                                        if room_column_classes[room.id][adj_col] == current_class:
                                            has_same_class_adjacent = True
                                            break
                                
                                if not has_same_class_adjacent:
                                    best_room = room
                                    best_col = col
                                    best_row = room_column_counts[room.id][col]
                                    break
                    
                    # If no space in odd columns, try even columns
                    if not best_room:
                        for col in even_columns:
                            if col in room_filled_columns[room.id]:
                                # Check if column is not full (less than 6 students)
                                if room_column_counts[room.id][col] < 6:
                                    # Check if adjacent columns have students from the same class
                                    adjacent_cols = [col - 1, col + 1]
                                    has_same_class_adjacent = False
                                    current_class = f"{dept}_{student.semester}"
                                    
                                    for adj_col in adjacent_cols:
                                        if 1 <= adj_col <= 7:  # Check if adjacent column is valid
                                            if room_column_classes[room.id][adj_col] == current_class:
                                                has_same_class_adjacent = True
                                                break
                                    
                                    if not has_same_class_adjacent:
                                        best_room = room
                                        best_col = col
                                        best_row = room_column_counts[room.id][col]
                                        break
                    
                    # If still no space, try unfilled odd columns
                    if not best_room:
                        for col in odd_columns:
                            if col not in room_filled_columns[room.id]:
                                # Check if adjacent columns have students from the same class
                                adjacent_cols = [col - 1, col + 1]
                                has_same_class_adjacent = False
                                current_class = f"{dept}_{student.semester}"
                                
                                for adj_col in adjacent_cols:
                                    if 1 <= adj_col <= 7:  # Check if adjacent column is valid
                                        if room_column_classes[room.id][adj_col] == current_class:
                                            has_same_class_adjacent = True
                                            break
                                
                                if not has_same_class_adjacent:
                                    best_room = room
                                    best_col = col
                                    best_row = 0
                                    break
                    
                    # Finally, try unfilled even columns
                    if not best_room:
                        for col in even_columns:
                            if col not in room_filled_columns[room.id]:
                                # Check if adjacent columns have students from the same class
                                adjacent_cols = [col - 1, col + 1]
                                has_same_class_adjacent = False
                                current_class = f"{dept}_{student.semester}"
                                
                                for adj_col in adjacent_cols:
                                    if 1 <= adj_col <= 7:  # Check if adjacent column is valid
                                        if room_column_classes[room.id][adj_col] == current_class:
                                            has_same_class_adjacent = True
                                            break
                                
                                if not has_same_class_adjacent:
                                    best_room = room
                                    best_col = col
                                    best_row = 0
                                    break

                # If no space in existing rooms, look for empty rooms
                if not best_room:
                    for room in rooms:
                        if room_counts[room.id] >= 42:
                            continue

                        # For new rooms, start with column 1
                        if 1 not in room_filled_columns[room.id]:
                            best_room = room
                            best_col = 1
                            best_row = 0
                            break

                if not best_room:
                    flash('Not enough rooms to allocate all students.', 'error')
                    break

                # Get next seat number for this room
                seat_no = room_seat_numbers[best_room.id]
                room_seat_numbers[best_room.id] += 1

                # Calculate row number based on column count
                row = room_column_counts[best_room.id][best_col] + 1

                # Create seat allocation
                allocation = SeatAllocation(
                    exam_id=exam.id,
                    room_id=best_room.id,
                    student_id=student.id,
                    row=row,  # Use calculated row number
                    col=best_col,
                    seat_no=seat_no
                )
                db.session.add(allocation)

                # Add to room allocations for display
                room_allocations[best_room.id].append([
                    student.register_number,
                    best_room.room_no,
                    row,  # Use calculated row number
                    best_col,
                    seat_no
                ])

                # Mark student as allocated and increment counts
                allocated_students.add(student.id)
                room_counts[best_room.id] += 1
                room_column_counts[best_room.id][best_col] += 1
                room_column_classes[best_room.id][best_col] = f"{dept}_{student.semester}"
                students_processed += 1

                # If column is full, mark it as filled
                if room_column_counts[best_room.id][best_col] >= 6:
                    room_filled_columns[best_room.id].add(best_col)

        # Commit all allocations
        db.session.commit()

        # Format room allocations for template
        formatted_allocations = {}
        used_rooms = []  # Track which rooms were actually used
        
        for room in rooms:
            if room_allocations[room.id]:  # Only include rooms that have allocations
                formatted_allocations[room.room_no] = room_allocations[room.id]
                used_rooms.append(room.room_no)
        
        return render_template('seating.html',
                            date=date.strftime('%Y-%m-%d'),
                            fn_an=fn_an,
                            int_ext=int_ext,
                            subject_code=subject_code,
                            rooms=used_rooms,  # Only pass the used rooms
                            room_allocations=formatted_allocations)
        
    except Exception as e:
        flash(f'Error generating seat allocation: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/get_student_info')
def get_student_info():
    """API to get student information"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    register_number = request.args.get('register_number')
    
    if not register_number:
        return jsonify({'error': 'Register number is required'}), 400
    
    student = Student.query.filter_by(register_number=register_number).first()
    
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    exams = []
    allocations = SeatAllocation.query.filter_by(student_id=student.id).all()
    
    for allocation in allocations:
        exam = Exam.query.get(allocation.exam_id)
        room = Room.query.get(allocation.room_id)
        
        if exam and room:
            exams.append({
                'date': exam.date.strftime('%Y-%m-%d'),
                'fn_an': exam.fn_an,
                'subject_code': exam.subject_code,
                'room_no': room.room_no,
                'seat_no': allocation.seat_no
            })
    
    return jsonify({
        'name': student.name,
        'department': student.department,
        'semester': student.semester,
        'exams': exams
    })

@app.route('/logout')
def logout():
    """Handle logout for both admin and student"""
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/timetable-upload')
def timetable_upload():
    """Render the timetable upload page"""
    if not session.get('admin_logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('admin_login'))
    return render_template('timetable.html')

@app.route('/upload-timetable', methods=['POST'])
def upload_timetable():
    """Handle timetable image upload"""
    if not session.get('admin_logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('admin_login'))
    
    if 'timetable' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('timetable_upload'))
    
    file = request.files['timetable']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('timetable_upload'))
    
    if file and allowed_file(file.filename):
        # Get the original filename without extension
        original_filename = os.path.splitext(file.filename)[0]
        
        # Validate filename format (IT-1-S5-dec-2025)
        if not re.match(r'^IT-[12]-S[1-8]-[a-z]{3}-\d{4}$', original_filename):
            flash('Invalid filename format. Use format: IT-1-S5-dec-2025', 'error')
            return redirect(url_for('timetable_upload'))
        
        # Extract information from filename
        # original_filename format: IT-1-S5-dec-2025
        parts = original_filename.split('-')
        exam_type = parts[0]  # IT
        internal_number = parts[1]  # 1 or 2
        semester = parts[2]  # S5
        month = parts[3]  # dec
        year = parts[4]  # 2025
        
        # Validate month
        valid_months = {'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'}
        if month.lower() not in valid_months:
            flash('Invalid month. Use three-letter month code (e.g., dec, jan, feb)', 'error')
            return redirect(url_for('timetable_upload'))
        
        # Create new filename with extension
        extension = os.path.splitext(file.filename)[1].lower()
        new_filename = f"{original_filename}{extension}"
        
        # Check if file with same name already exists
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        if os.path.exists(filepath):
            flash('A timetable with this name already exists. Please use a different name.', 'error')
            return redirect(url_for('timetable_upload'))
        
        # Save the file
        file.save(filepath)
        
        flash(f'Time table uploaded successfully! ({new_filename})', 'success')
    else:
        flash('Invalid file type. Please upload JPG, JPEG, or PNG files only.', 'error')
    
    return redirect(url_for('timetable_upload'))

@app.route('/get_scheduled_classes')
def get_scheduled_classes():
    """API to get classes already scheduled for a date and session"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    date_str = request.args.get('date')
    fn_an = request.args.get('fn_an')
    
    if not date_str or not fn_an:
        return jsonify({'error': 'Date and session are required'}), 400
    
    try:
        # Convert date string to datetime object
        date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Get all allocations for this date and session
        allocations = SeatAllocation.query.join(Exam).filter(
            Exam.date == date,
            Exam.fn_an == fn_an
        ).all()
        
        # Get unique department_semester combinations
        scheduled_classes = set()
        for allocation in allocations:
            student = Student.query.get(allocation.student_id)
            if student:
                scheduled_classes.add(f"{student.department.lower()}_{student.semester}")
        
        return jsonify({
            'scheduled_classes': list(scheduled_classes)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', 
                          error_code=404, 
                          error_message="Page not found."), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', 
                          error_code=500, 
                          error_message="Internal server error."), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)