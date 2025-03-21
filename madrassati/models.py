from werkzeug.security import generate_password_hash
from madrassati.extensions import db
from datetime import datetime, timezone, timedelta
#class User(db.Model):
#    id = db.Column(db.Integer, primary_key=True)
#    username = db.Column(db.String(80), unique=True, nullable=False)
#    password = db.Column(db.String(256), nullable=False)
#    phone = db.Column(db.String(256), nullable=False)
#    otp = db.Column(db.String(5))  # Field to store the OTP
#    otp_expiration = db.Column(db.DateTime)  # Field to store OTP expiration time
#    created_at = db.Column(db.DateTime, server_default=db.func.now())
#
#    def __init__(self, username, password,phone):
#        self.username = username
#        self.password = generate_password_hash(password)  # Hash password before storing
#        self.phone = phone


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=True)
    firstName = db.Column(db.String(50), nullable=True)
    lastName = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    isEmailVerified =  db.Column(db.Boolean,default=False)
    password = db.Column(db.String(200), nullable=False)
    phoneNumber = db.Column(db.String(20), nullable=False)
    isPhoneVerified = db.Column(db.Boolean,default=False)
    address = db.Column(db.String(255), nullable=True)
    profilePicture = db.Column(db.String(255))
    birthDate = db.Column(db.Date, nullable=True)
    createdAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __mapper_args__ = {'polymorphic_on': type, 'polymorphic_identity': 'user'}

    def __repr__(self):
        return f"<User {self.email}>"

    def __init__(self, email, password,phoneNumber):
        self.email = email
        self.password = password  # Hash password before storing
        self.phoneNumber = phoneNumber

class Parent(User):
    __tablename__ = 'parent'

    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    emergencyContact = db.Column(db.String(50))
    hasPaidFees = db.Column(db.Boolean, default=False)

    __mapper_args__ = {'polymorphic_identity': 'parent'}

    def __repr__(self):
        return f"<Parent id={self.id}>"
    def __init__(self, email, password, phoneNumber):
        super().__init__(email, password, phoneNumber)


class Teacher(User):
    __tablename__ = 'teacher'

    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    department = db.Column(db.String(100))
    salary = db.Column(db.Float)

    __mapper_args__ = {'polymorphic_identity': 'teacher'}

    def __repr__(self):
        return f"<Teacher id={self.id}>"
    def __init__(self, email, password, phoneNumber):
        super().__init__(email, password, phoneNumber)


class Student(User):
    __tablename__ = 'student'

    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    level = db.Column(db.String(50))
    year = db.Column(db.Integer)
    classroom = db.Column(db.String(50))
    isEnrolled = db.Column(db.Boolean, default=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('parent.id'), nullable=True)

    parent = db.relationship('Parent', backref=db.backref('children', lazy=True), foreign_keys=[parent_id])
    __mapper_args__ = {'polymorphic_identity': 'student'}

    def __repr__(self):
        return f"<Student id={self.id} level={self.level}>"



class PendingStudent(db.Model):
    __tablename__ = 'pending_student'

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('parent.id'), nullable=True)
    requestedLevel = db.Column(db.String(50))
    requestedYear = db.Column(db.Integer)
    isApproved = db.Column(db.Boolean, default=False)
    requestDate = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    parent = db.relationship('Parent', backref=db.backref('pending_students', lazy=True))

    def __repr__(self):
        return f"<PendingStudent id={self.id} isApproved={self.isApproved}>"



