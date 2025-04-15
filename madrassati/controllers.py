from werkzeug.security import generate_password_hash
from datetime import datetime, timezone, timedelta
from madrassati.extensions import db
from madrassati.models import (
    Parent,
    Student,
    Group,
    Level,
    Teacher,
    Module,
    Session,
    Semester,
    TeacherGroupAssociation,
    FeeStatus,
)

#NeeeOte :::: neeed to fix this line 155:
#                Session.query.filter(
                    #Session.semester_id == semester_id,
                   # Session.group_id == group_id,
                   # Session.start_time == session_datetime,
 #               ).delete()

# ----------------
# Parent Controllers
# ----------------


def create_parent(
    email, password, phone_number, first_name=None, last_name=None, address=None
):
    """
    Create a new parent in the database

    Returns:
        tuple: (parent_id, message) or (None, error_message)
    """
    # Check if parent with email already exists
    if Parent.query.filter_by(email=email).first():
        return None, "Parent with this email already exists"

    # Create password hash
    password_hash = generate_password_hash(password)

    try:
        new_parent = Parent(
            email=email,
            password_hash=password_hash,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
            address=address,
        )

        db.session.add(new_parent)
        db.session.commit()

        return new_parent.id, "Parent created successfully"

    except Exception as e:
        db.session.rollback()
        return None, str(e)


def add_child(
    parent_id, email, password, level_id, first_name=None, last_name=None, docs_url=None
):
    """
    Add a child (student) to a parent

    Returns:
        tuple: (student_id, message) or (None, error_message)
    """
    # Check if parent exists
    parent = Parent.query.get(parent_id)
    if not parent:
        return None, "Parent not found"

    # Check if level exists
    level = Level.query.get(level_id)
    if not level:
        return None, "Level not found"

    # Create password hash for student
    password_hash = generate_password_hash(password)

    try:
        new_student = Student(
            email=email,
            password_hash=password_hash,
            level_id=level_id,
            parent_id=parent_id,
            first_name=first_name,
            last_name=last_name,
            docs_url=docs_url,
        )

        db.session.add(new_student)
        db.session.commit()

        return new_student.id, "Student added successfully"

    except Exception as e:
        db.session.rollback()
        return None, str(e)


def get_parents():
    """
    Get all parents

    Returns:
        tuple: (list of parent dicts, message) or (None, error_message)
    """
    try:
        parents = Parent.query.all()

        result = []
        for parent in parents:
            result.append(
                {
                    "id": parent.id,
                    "name": f"{parent.first_name} {parent.last_name}",
                    "email": parent.email,
                    "phone": parent.phone_number,
                    "children_count": len(parent.students),
                    "created_at": parent.created_at.isoformat(),
                }
            )

        return result, "Success"

    except Exception as e:
        return None, str(e)


def get_parents_by_paid(status="paid"):
    """
    Get parents filtered by payment status

    Args:
        status: The payment status to filter by ('paid', 'unpaid', 'overdue')

    Returns:
        tuple: (list of parent dicts, message) or (None, error_message)
    """
    try:
        # Map the status to the enum
        fee_status = None
        if status.lower() == "paid":
            fee_status = FeeStatus.PAID
        elif status.lower() == "unpaid":
            fee_status = FeeStatus.UNPAID
        elif status.lower() == "overdue":
            fee_status = FeeStatus.OVERDUE
        else:
            return None, "Invalid status parameter"

        # Using join to get parents with fees of the given status
        parents_with_status = (
            db.session.query(Parent)
            # note need to fix this join dont forget it
       #     .join(Parent.fees)
            .filter(Parent.fees.any(status=fee_status))
            .all()
        )

        result = []
        for parent in parents_with_status:
            result.append(
                {
                    "id": parent.id,
                    "name": f"{parent.first_name} {parent.last_name}",
                    "email": parent.email,
                    "phone": parent.phone_number,
                    "created_at": parent.created_at.isoformat(),
                }
            )

        return result, "Success"

    except Exception as e:
        return None, str(e)


# ----------------
# Student Controllers
# ----------------


def get_students(filter_type=None, filter_value=None):
    """
    Get all students with optional filtering

    Args:
        filter_type: Optional filter type ('level', 'group', 'approved')
        filter_value: Value to filter by (level_id, group_id, or True/False for approved)

    Returns:
        tuple: (list of student dicts, message) or (None, error_message)
    """
    try:
        query = Student.query

        # Apply filter if provided
        if filter_type and filter_value is not None:
            if filter_type == "level":
                query = query.filter_by(level_id=filter_value)
            elif filter_type == "group":
                query = query.filter_by(group_id=filter_value)
            elif filter_type == "approved":
                query = query.filter_by(is_approved=bool(filter_value))
            else:
                return None, "Invalid filter type"

        students = query.all()

        result = []
        for student in students:
            result.append(
                {
                    "id": student.id,
                    "name": f"{student.first_name} {student.last_name}",
                    "email": student.email,
                    "level": student.level.name if student.level else None,
                    "level_id": student.level_id,
                    "group": student.group.name if student.group else None,
                    "group_id": student.group_id,
                    "parent": (
                        f"{student.parent.first_name} {student.parent.last_name}"
                        if student.parent
                        else None
                    ),
                    "is_approved": student.is_approved,
                    "created_at": student.created_at.isoformat(),
                }
            )

        return result, "Success"

    except Exception as e:
        return None, str(e)


# ----------------
# Group Controllers
# ----------------


def add_group(name, level_id):
    """
    Add a new group

    Returns:
        tuple: (group_id, message) or (None, error_message)
    """
    # Check if level exists
    level = Level.query.get(level_id)
    if not level:
        return None, "Level not found"

    try:
        new_group = Group(name=name, level_id=level_id)

        db.session.add(new_group)
        db.session.commit()

        return new_group.id, "Group created successfully"

    except Exception as e:
        db.session.rollback()
        return None, str(e)


def get_groups(level_id=None):
    """
    Get all groups with optional level filtering

    Args:
        level_id: Optional level ID to filter groups by

    Returns:
        tuple: (list of group dicts, message) or (None, error_message)
    """
    try:
        query = Group.query

        # Apply level filter if provided
        if level_id is not None:
            query = query.filter_by(level_id=level_id)

        groups = query.all()

        result = []
        for group in groups:
            # Get teacher names for this group
            teachers = []
            for assoc in group.teacher_associations:
                if assoc.teacher:
                    teachers.append(
                        f"{assoc.teacher.first_name} {assoc.teacher.last_name}"
                    )

            result.append(
                {
                    "id": group.id,
                    "name": group.name,
                    "level": group.level.name if group.level else None,
                    "level_id": group.level_id,
                    "students_count": len(group.students),
                    "teachers": teachers,
                }
            )

        return result, "Success"

    except Exception as e:
        return None, str(e)


def assign_student_to_group(student_id, group_id):
    """
    Assign a student to a group

    Returns:
        tuple: (True, message) or (False, error_message)
    """
    # Check if group and student exist
    group = Group.query.get(group_id)
    if not group:
        return False, "Group not found"

    student = Student.query.get(student_id)
    if not student:
        return False, "Student not found"

    # Check if the student's level matches the group's level
    if student.level_id != group.level_id:
        return False, "Student's level doesn't match group's level"

    try:
        student.group_id = group_id
        db.session.commit()

        return True, f"Student {student_id} assigned to group {group_id}"

    except Exception as e:
        db.session.rollback()
        return False, str(e)


def remove_student_from_group(student_id, group_id):
    """
    Remove a student from a group

    Returns:
        tuple: (True, message) or (False, error_message)
    """
    # Check if student exists and belongs to the specified group
    student = Student.query.filter_by(id=student_id, group_id=group_id).first()
    if not student:
        return False, "Student not found in this group"

    try:
        student.group_id = None
        db.session.commit()

        return True, f"Student {student_id} removed from group {group_id}"

    except Exception as e:
        db.session.rollback()
        return False, str(e)


# ----------------
# Teacher Controllers
# ----------------


def add_teacher(
    email,
    password,
    phone_number,
    first_name=None,
    last_name=None,
    address=None,
    module_key=None,
):
    """
    Add a new teacher

    Returns:
        tuple: (teacher_id, message) or (None, error_message)
    """
    # Check if teacher with email already exists
    if Teacher.query.filter_by(email=email).first():
        return None, "Teacher with this email already exists"

    # Create password hash
    password_hash = generate_password_hash(password)

    try:
        new_teacher = Teacher(
            email=email,
            password_hash=password_hash,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
            address=address,
            module_key=module_key,
        )

        db.session.add(new_teacher)
        db.session.commit()

        return new_teacher.id, "Teacher created successfully"

    except Exception as e:
        db.session.rollback()
        return None, str(e)


def get_teachers():
    """
    Get all teachers

    Returns:
        tuple: (list of teacher dicts, message) or (None, error_message)
    """
    try:
        teachers = Teacher.query.all()

        result = []
        for teacher in teachers:
            # Get groups for this teacher
            groups = []
            for assoc in teacher.assigned_groups:
                if assoc.group:
                    groups.append({"id": assoc.group.id, "name": assoc.group.name})

            # Get modules for this teacher
            modules = []
            for module in teacher.modules:
                modules.append({"id": module.id, "name": module.name})

            result.append(
                {
                    "id": teacher.id,
                    "name": f"{teacher.first_name} {teacher.last_name}",
                    "email": teacher.email,
                    "phone": teacher.phone_number,
                    "module_key": teacher.module_key,
                    "groups": groups,
                    "modules": modules,
                }
            )

        return result, "Success"

    except Exception as e:
        return None, str(e)


# ----------------
# Session & Semester Controllers
# ----------------


def add_sessions(
    teacher_id, module_id, group_id, semester_id, day_of_week, time_str, week_number
):
    """
    Add sessions for a specific week in a semester

    Args:
        teacher_id: ID of the teacher
        module_id: ID of the module
        group_id: ID of the group
        semester_id: ID of the semester
        day_of_week: Day of the week (0=Monday, 6=Sunday)
        time_str: Time in "HH:MM" format (24-hour)
        week_number: Week number in the semester (1-based)

    Returns:
        tuple: (session_id, message) or (None, error_message)
    """
    # Check if teacher, module, group, and semester exist
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return None, "Teacher not found"

    module = Module.query.get(module_id)
    if not module:
        return None, "Module not found"

    group = Group.query.get(group_id)
    if not group:
        return None, "Group not found"

    semester = Semester.query.get(semester_id)
    if not semester:
        return None, "Semester not found"

    try:
        # Calculate the exact date based on semester start and week number
        session_date = semester.start_date + timedelta(
            weeks=week_number - 1,  # Convert to 0-based weeks
            days=day_of_week,  # Add specific day of week
        )

        # Parse time
        hour, minute = map(int, time_str.split(":"))

        # Create the session datetime
        session_datetime = datetime.combine(session_date, datetime.min.time()).replace(
            hour=hour, minute=minute
        )

        # Create session
        new_session = Session(
            teacher_id=teacher_id,
            module_id=module_id,
            group_id=group_id,
            semester_id=semester_id,
            start_time=session_datetime,
            weeks=week_number,
        )

        db.session.add(new_session)
        db.session.commit()

        # Return the formatted start time as YY-MM-DD-HH:MM
        formatted_time = session_datetime.strftime("%y-%m-%d-%H:%M")
        return new_session.id, f"Session created at {formatted_time}"

    except Exception as e:
        db.session.rollback()
        return None, str(e)


def modify_schedule(semester_id, group_id, weekly_schedule):
    """
    Modify the schedule by adding recurring weekly sessions from current week to semester end,
    resolving any conflicts

    Args:
        semester_id: ID of the semester
        group_id: ID of the group
        weekly_schedule: List of weekly session templates with:
            - day_of_week (int): 0=Monday to 6=Sunday
            - time_str (str): "HH:MM" format
            - teacher_id (int)
            - module_id (int)

    Returns:
        tuple: (list of new session IDs, message) or (None, error_message)
    """
    try:
        # Verify semester and group exist
        semester = Semester.query.get(semester_id)
        if not semester:
            return None, "Semester not found"

        group = Group.query.get(group_id)
        if not group:
            return None, "Group not found"

        # Get current week (1-based)
        today = datetime.now(timezone.utc).date()
        current_week = ((today - semester.start_date).days // 7) + 1
        total_weeks = semester.duration

        if current_week > total_weeks:
            return None, "Semester has already ended"

        # Start transaction
        db.session.begin()
        created_session_ids = []

        for week_number in range(current_week, total_weeks + 1):
            for session_template in weekly_schedule:
                # Calculate the exact datetime
                session_date = semester.start_date + timedelta(
                    weeks=week_number - 1, days=session_template["day_of_week"]
                )

                # Skip if this date is in the past
                if session_date < today:
                    continue

                # Parse time
                hour, minute = map(int, session_template["time_str"].split(":"))

                # Create the session datetime
                session_datetime = datetime.combine(
                    session_date, datetime.min.time()
                ).replace(hour=hour, minute=minute)

                # Delete any existing session at this exact time
                Session.query.filter(
                    #Session.semester_id == semester_id,
                   # Session.group_id == group_id,
                   # Session.start_time == session_datetime,
                ).delete()

                # Create new session
                new_session = Session(
                    teacher_id=session_template["teacher_id"],
                    module_id=session_template["module_id"],
                    group_id=group_id,
                    semester_id=semester_id,
                    start_time=session_datetime,
                    weeks=week_number,
                )
                db.session.add(new_session)
                created_session_ids.append(new_session.id)

        db.session.commit()

        return (
            created_session_ids,
            f"Added {len(created_session_ids)} sessions from week {current_week} to {total_weeks}",
        )

    except Exception as e:
        db.session.rollback()
        return None, f"Error updating schedule: {str(e)}"


def get_sessions_by_trimestre_id_and_group_id(semester_id, group_id):
    """
    Get all sessions for a specific semester/trimestre and group, filtered by current week

    Returns:
        tuple: (dict with sessions and semester info, message) or (None, error_message)
    """
    semester = Semester.query.get(semester_id)
    if not semester:
        return None, "Semester not found"

    group = Group.query.get(group_id)
    if not group:
        return None, "Group not found"

    try:
        # Calculate current week
        today = datetime.now(timezone.utc).date()
        semester_start = semester.start_date
        current_week = ((today - semester_start).days // 7) + 1

        # Get sessions for this week, group, and semester
        # need to fix this toooo note urgent gemini you need to seeeeee this
        sessions = Session.query.filter(
            #Session.semester_id == semester_id,
            #Session.group_id == group_id,
            Session.weeks == current_week,
        ).all()

        result = []
        for session in sessions:
            result.append(
                {
                    "id": session.id,
                    "teacher": (
                        f"{session.teacher.first_name} {session.teacher.last_name}"
                        if session.teacher
                        else None
                    ),
                    "teacher_id": session.teacher_id,
                    "module": session.module.name if session.module else None,
                    "module_id": session.module_id,
                    "start_time": session.start_time.strftime(
                        "%y-%m-%d-%H:%M"
                    ),  # Format as YY-MM-DD-HH:MM
                    "week_number": session.weeks,
                }
            )

        return {
            "sessions": result,
            "current_week": current_week,
            "total_weeks": semester.duration,
            "semester_name": semester.name,
            "group_name": group.name,
        }, "Success"

    except Exception as e:
        return None, str(e)


def delete_sessions(session_ids):
    """
    Delete multiple sessions

    Args:
        session_ids: List of session IDs to delete

    Returns:
        tuple: (deleted_count, message) or (None, error_message)
    """
    if not session_ids:
        return 0, "No session IDs provided"

    try:
        deleted_count = 0
        for session_id in session_ids:
            session = Session.query.get(session_id)
            if session:
                db.session.delete(session)
                deleted_count += 1

        db.session.commit()

        return deleted_count, f"Successfully deleted {deleted_count} sessions"

    except Exception as e:
        db.session.rollback()
        return None, str(e)
