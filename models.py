import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

class Room(db.Model):
    """
    Model for storing room information
    Each room has a unique room_no (e.g., 'AD 115') and a capacity
    """
    __tablename__ = 'rooms'

    id = Column(Integer, primary_key=True)
    room_no = Column(String(20), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False)
    block_name = Column(String(50))  # Extracted from room_no (e.g., 'AD')
    floor = Column(String(10))  # Extracted from room_no (e.g., '1')
    row_count = Column(Integer)  # Maximum number of rows in the room
    col_count = Column(Integer)  # Maximum number of columns in the room
    
    # Relationship with SeatAllocation model
    allocations = relationship('SeatAllocation', back_populates='room', cascade='all, delete-orphan')
    
    def __init__(self, room_no, capacity):
        self.room_no = room_no
        self.capacity = capacity
        
        # Extract block name and floor from room_no
        # Assuming format is "BlockCode RoomNumber" (e.g., "AD 115")
        parts = room_no.split(' ')
        if len(parts) >= 2:
            self.block_name = parts[0]
            room_number = parts[1]
            # Floor is the first digit of the room number
            if room_number and len(room_number) > 0:
                self.floor = room_number[0]
            else:
                self.floor = "0"
        else:
            self.block_name = room_no
            self.floor = "0"
        
        # Calculate row and column count based on capacity
        # Simple formula: assume a square grid, ceiling of square root
        import math
        grid_size = math.ceil(math.sqrt(capacity))
        self.row_count = grid_size
        self.col_count = grid_size

    def __repr__(self):
        return f"<Room {self.room_no} (Capacity: {self.capacity})>"


class Student(db.Model):
    """
    Model for storing student information
    Students are organized by department and semester
    """
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True)
    register_number = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    department = Column(String(50), nullable=False)
    semester = Column(String(10), nullable=False)
    
    # Relationship with SeatAllocation model
    allocations = relationship('SeatAllocation', back_populates='student', cascade='all, delete-orphan')
    
    def __init__(self, register_number, name, department, semester):
        self.register_number = register_number
        self.name = name
        self.department = department
        self.semester = semester

    def __repr__(self):
        return f"<Student {self.register_number} - {self.name}>"


class Exam(db.Model):
    """
    Model for storing exam information
    """
    __tablename__ = 'exams'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    fn_an = Column(String(5), nullable=False)  # 'FN' or 'AN'
    int_ext = Column(String(5), nullable=False)  # 'INT' or 'EXT'
    subject_code = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationship with SeatAllocation model
    allocations = relationship('SeatAllocation', back_populates='exam', cascade='all, delete-orphan')
    
    def __init__(self, date, fn_an, int_ext, subject_code):
        self.date = date
        self.fn_an = fn_an
        self.int_ext = int_ext
        self.subject_code = subject_code

    def __repr__(self):
        return f"<Exam {self.subject_code} on {self.date.strftime('%Y-%m-%d')} {self.fn_an}>"


class SeatAllocation(db.Model):
    """
    Model for storing seat allocation information
    Links students to rooms for specific exams
    """
    __tablename__ = 'seat_allocations'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=False)
    exam_id = Column(Integer, ForeignKey('exams.id'), nullable=False)
    row = Column(Integer, nullable=False)
    col = Column(Integer, nullable=False)
    seat_no = Column(Integer, nullable=False)
    
    # Relationships
    student = relationship('Student', back_populates='allocations')
    room = relationship('Room', back_populates='allocations')
    exam = relationship('Exam', back_populates='allocations')
    
    def __init__(self, student_id, room_id, exam_id, row, col, seat_no):
        self.student_id = student_id
        self.room_id = room_id
        self.exam_id = exam_id
        self.row = row
        self.col = col
        self.seat_no = seat_no

    def __repr__(self):
        return f"<SeatAllocation Student:{self.student_id} Room:{self.room_id} Seat:{self.seat_no}>"