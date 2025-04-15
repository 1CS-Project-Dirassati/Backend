import enum  # Needed for Enum type
from madrassati.extensions import db
from datetime import datetime, timezone


# --- Enums ---
# Using Enums makes status fields more robust and readable
class FeeStatus(enum.Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


# --- Models ---


class Admin(db.Model):
    """Represents an administrator user with system privileges."""

    __tablename__ = "admin"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)  # Store HASHED passwords
    # Consider sqlalchemy_utils.PhoneNumberType for validation if library is available
    phone_number = db.Column(db.String(20), nullable=False)
    is_super_admin = db.Column(
        db.Boolean, default=False, nullable=False
    )  # Explicit nullable=False
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<Admin id={self.id} email={self.email}>"

    # __init__ can be omitted if you rely on keyword arguments during creation,
    # or defined similarly to Parent/Teacher if specific logic is needed.
    # Remember to pass the HASHED password.


class Parent(db.Model):
    """Represents a parent or guardian of one or more students."""

    # Changed table name from "user" to "parent"
    __tablename__ = "parent"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Store HASHED passwords
    phone_number = db.Column(db.String(20), nullable=False)
    is_phone_verified = db.Column(db.Boolean, default=False, nullable=False)
    address = db.Column(db.String(255), nullable=True)
    profile_picture = db.Column(
        db.String(255), default="static/images/default_profile.png"
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships defined using back_populates
    students = db.relationship(
        "Student", back_populates="parent", cascade="all, delete-orphan"
    )
    fees = db.relationship("Fee", back_populates="parent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Parent id={self.id} email={self.email}>"

    def __init__(
        self,
        email,
        password_hash,
        phone_number,
        first_name=None,
        last_name=None,
        address=None,
    ):
        """Initializes a Parent instance. Expects a pre-hashed password."""
        self.email = email
        self.password = password_hash  # Expecting hash
        self.phone_number = phone_number
        self.first_name = first_name
        self.last_name = last_name
        self.address = address
        # Default values for boolean flags are handled by Column definition


class Teacher(db.Model):
    """Represents a teacher responsible for modules and groups."""

    __tablename__ = "teacher"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)  # Store HASHED passwords
    phone_number = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    profile_picture = db.Column(
        db.String(255), default="static/images/default_profile.png"
    )
    # module_key seems specific, kept it but ensure its purpose is clear.
    module_key = db.Column(db.String(100), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships defined using back_populates
    modules = db.relationship("Module", back_populates="teacher")
    assigned_groups = db.relationship(
        "TeacherGroupAssociation",
        back_populates="teacher",
        cascade="all, delete-orphan",
    )
    sessions = db.relationship("Session", back_populates="teacher")

    def __repr__(self):
        return f"<Teacher id={self.id} email={self.email}>"

    def __init__(
        self,
        email,
        password_hash,
        phone_number,
        first_name=None,
        last_name=None,
        address=None,
        module_key=None,
    ):
        """Initializes a Teacher instance. Expects a pre-hashed password."""
        self.email = email
        self.password = password_hash  # Expecting hash
        self.phone_number = phone_number
        self.first_name = first_name
        self.last_name = last_name
        self.address = address
        self.module_key = module_key


class Module(db.Model):
    """Represents a subject or course module taught."""

    __tablename__ = "module"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    teacher_id = db.Column(
        db.Integer, db.ForeignKey("teacher.id"), nullable=False, index=True
    )

    # Relationships defined using back_populates
    teacher = db.relationship("Teacher", back_populates="modules")
    level_associations = db.relationship(
        "LevelModuleAssociation", back_populates="module", cascade="all, delete-orphan"
    )
    sessions = db.relationship("Session", back_populates="module")

    def __repr__(self):
        return f"<Module id={self.id} name={self.name}>"


# Renamed from Groups to Group, table name singular
class Group(db.Model):
    """Represents a group of students within a specific level."""

    __tablename__ = "group"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    level_id = db.Column(
        db.Integer, db.ForeignKey("level.id"), nullable=False, index=True
    )
    # teacher_id removed - Teachers are linked via TeacherGroupAssociation (Many-to-Many)

    # Relationships defined using back_populates
    level = db.relationship("Level", back_populates="groups")
    teacher_associations = db.relationship(
        "TeacherGroupAssociation", back_populates="group", cascade="all, delete-orphan"
    )
    students = db.relationship("Student", back_populates="group")
    sessions = db.relationship("Session", back_populates="group")
    semesters = db.relationship(
        "Semester", back_populates="group"
    )  # If Semester *must* link to group

    def __repr__(self):
        return f"<Group id={self.id} name={self.name} level_id={self.level_id}>"

    def __init__(self, name, level_id):
        """Initializes a Group instance."""
        self.name = name
        self.level_id = level_id


class Level(db.Model):
    """Represents an academic or study level."""

    __tablename__ = "level"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)

    # Relationships defined using back_populates
    groups = db.relationship("Group", back_populates="level")
    module_associations = db.relationship(
        "LevelModuleAssociation", back_populates="level", cascade="all, delete-orphan"
    )
    students = db.relationship("Student", back_populates="level")
    semesters = db.relationship(
        "Semester", back_populates="level"
    )  # Linking Semester to Level

    def __repr__(self):
        return f"<Level id={self.id} name={self.name}>"


# Renamed from TG, using composite PK and descriptive name
class TeacherGroupAssociation(db.Model):
    """Association table linking Teachers to the Groups they teach (Many-to-Many)."""

    __tablename__ = "teacher_group_association"

    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"), index=True)
    group_id = db.Column(
        db.Integer, db.ForeignKey("group.id"), index=True
    )  # Changed FK target

    # Composite Primary Key
    __table_args__ = (db.PrimaryKeyConstraint("teacher_id", "group_id"),)

    # Relationships defined using back_populates
    teacher = db.relationship("Teacher", back_populates="assigned_groups")
    group = db.relationship(
        "Group", back_populates="teacher_associations"
    )  # Changed target model

    def __repr__(self):
        return f"<TeacherGroupAssociation teacher_id={self.teacher_id} group_id={self.group_id}>"


# Renamed from LM, using composite PK and descriptive name
class LevelModuleAssociation(db.Model):
    """Association table linking Levels to the Modules taught in them (Many-to-Many)."""

    __tablename__ = "level_module_association"

    level_id = db.Column(db.Integer, db.ForeignKey("level.id"), index=True)
    module_id = db.Column(db.Integer, db.ForeignKey("module.id"), index=True)

    # Composite Primary Key
    __table_args__ = (db.PrimaryKeyConstraint("level_id", "module_id"),)

    # Relationships defined using back_populates
    level = db.relationship("Level", back_populates="module_associations")
    module = db.relationship("Module", back_populates="level_associations")

    def __repr__(self):
        return f"<LevelModuleAssociation level_id={self.level_id} module_id={self.module_id}>"


class Student(db.Model):
    """Represents a student enrolled in the system."""

    __tablename__ = "student"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)  # Store HASHED passwords
    level_id = db.Column(
        db.Integer, db.ForeignKey("level.id"), nullable=False, index=True
    )
    group_id = db.Column(
        db.Integer, db.ForeignKey("group.id"), nullable=True, index=True
    )  # Changed FK target
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    # Changed FK target table to "parent"
    parent_id = db.Column(
        db.Integer, db.ForeignKey("parent.id"), nullable=False, index=True
    )
    docs_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships defined using back_populates
    # Changed target_model to "Parent"
    parent = db.relationship("Parent", back_populates="students")
    level = db.relationship("Level", back_populates="students")
    # Changed target_model to "Group"
    group = db.relationship("Group", back_populates="students")
    absences = db.relationship(
        "Absence", back_populates="student", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Student id={self.id} email={self.email} level_id={self.level_id} group_id={self.group_id}>"

    def __init__(
        self,
        email,
        password_hash,
        level_id,
        parent_id,
        first_name=None,
        last_name=None,
        group_id=None,
        docs_url=None,
    ):
        """Initializes a Student instance. Expects a pre-hashed password."""
        self.email = email
        self.password = password_hash  # Expecting hash
        self.level_id = level_id
        self.parent_id = parent_id
        self.group_id = group_id
        self.first_name = first_name
        self.last_name = last_name
        self.docs_url = docs_url


class Session(db.Model):
    """Represents a scheduled class session for a specific module and group."""

    __tablename__ = "session"

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(
        db.Integer, db.ForeignKey("teacher.id"), nullable=False, index=True
    )
    module_id = db.Column(
        db.Integer, db.ForeignKey("module.id"), nullable=False, index=True
    )
    # Changed FK target to "group"
    group_id = db.Column(
        db.Integer, db.ForeignKey("group.id"), nullable=False, index=True
    )
    semester_id = db.Column(
        db.Integer, db.ForeignKey("semester.id"), nullable=False, index=True
    )
    start_time = db.Column(
        db.DateTime(timezone=True), nullable=False, index=True
    )  # Added index
    # Add end_time or duration?
    weeks = db.Column(db.Integer, nullable=True)  # Example: Duration in minutes

    # Relationships defined using back_populates
    teacher = db.relationship("Teacher", back_populates="sessions")
    module = db.relationship("Module", back_populates="sessions")
    # Changed target_model to "Group"
    group = db.relationship("Group", back_populates="sessions")
    semester = db.relationship("Semester", back_populates="sessions")
    absences = db.relationship(
        "Absence", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Session id={self.id} module_id={self.module_id} group_id={self.group_id} start={self.start_time}>"

    def __init__(
        self,
        teacher_id,
        module_id,
        group_id,
        semester_id,
        start_time,
        weeks=None,
    ):
        """Initializes a Session instance."""
        self.teacher_id = teacher_id
        self.module_id = module_id
        self.group_id = group_id
        self.semester_id = semester_id
        self.start_time = start_time
        self.weeks = weeks


# Renamed from Absences to Absence, table name singular
class Absence(db.Model):
    """Records an absence of a student from a specific session."""

    __tablename__ = "absence"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("student.id"), nullable=False, index=True
    )
    session_id = db.Column(
        db.Integer, db.ForeignKey("session.id"), nullable=False, index=True
    )
    justified = db.Column(db.Boolean, default=False, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    recorded_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships defined using back_populates
    student = db.relationship("Student", back_populates="absences")
    session = db.relationship("Session", back_populates="absences")

    # Unique constraint for student/session pair
    __table_args__ = (
        db.UniqueConstraint("student_id", "session_id", name="_student_session_uc"),
    )

    def __repr__(self):
        return f"<Absence id={self.id} student_id={self.student_id} session_id={self.session_id}>"


# Renamed from Fees to Fee, table name singular
class Fee(db.Model):
    """Represents a fee owed by a parent."""

    __tablename__ = "fee"

    id = db.Column(db.Integer, primary_key=True)
    # Changed FK target table to "parent"
    parent_id = db.Column(
        db.Integer, db.ForeignKey("parent.id"), nullable=False, index=True
    )
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)  # Added description
    due_date = db.Column(
        db.Date, nullable=False
    )  # Changed to Date for simplicity unless time is relevant
    # Using Enum for status
    status = db.Column(
        db.Enum(FeeStatus, name="fee_status_enum"),
        nullable=False,
        default=FeeStatus.UNPAID,
        index=True,
    )
    payment_date = db.Column(db.Date, nullable=True)  # Changed to Date
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships defined using back_populates
    # Changed target_model to "Parent"
    parent = db.relationship("Parent", back_populates="fees")

    def __repr__(self):
        return f"<Fee id={self.id} amount={self.amount} status={self.status.value} parent_id={self.parent_id}>"


class Semester(db.Model):
    """Represents an academic semester, linked to a level."""

    __tablename__ = "semester"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    # Changed from group_id to level_id
    level_id = db.Column(
        db.Integer, db.ForeignKey("level.id"), nullable=False, index=True
    )
    start_date = db.Column(db.Date, nullable=False)  # Changed to Date
    duration = db.Column(db.Integer, nullable=False)  # Duration in weeks (alternative)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships defined using back_populates
    # Changed relationship to Level
    level = db.relationship("Level", back_populates="semesters")
    sessions = db.relationship("Session", back_populates="semester")

    def __repr__(self):
        return f"<Semester id={self.id} name={self.name} level_id={self.level_id}>"

    # createParent =>id
    # addChild =>id
    # getParents => parents
    # getParentsByPaid => parents
    # getStudents =>students
    # addGroup =>id
    # getGroups =>groups
    # assignStudentToGroup =>msg
    # removeStudentFromGroup =>msg
    # addTeacher =>id
    # getTeachers =>teachers
    # addSessions , modifyTrimestre =>id
    # getSessionsByTrimestreId =>sessions + startTrimestre+ nmbrWeeks
    # deleteSessions =>msg
