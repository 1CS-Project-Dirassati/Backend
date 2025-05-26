from app import db  # Make sure db is imported
from app.models import (
    TimeSlot,
    Admin,
    Absence,
    Chat,
    Fee,
    Group,
    Level,
    Lesson,  # Lesson is an alias for Cours
    Module,
    Message,
    Note,
    Notification,
    Parent,
    Salle,
    Semester,
    Student,
    Session,
    Teacher,
    User,
    TeacherModuleAssociation,
    TeacherGroupAssociation,
    FeeStatus,
    NoteType,
    NotificationType,
    TimeSlot,  # Enums
    AdminSchema,
    AbsenceSchema,
    ChatSchema,
    FeeSchema,
    GroupSchema,
    LevelSchema,
    LessonSchema,
    ModuleSchema,
    MessageSchema,
    NoteSchema,
    NotificationSchema,
    ParentSchema,
    SalleSchema,
    SemesterSchema,
    StudentSchema,
    SessionSchema,
    TeacherSchema,
    TeacherModuleAssociationSchema,
    TeacherGroupAssociationSchema,
)
from werkzeug.security import generate_password_hash
from datetime import datetime, date, timedelta, timezone
import random
from flask import current_app

# Instantiate Schemas and provide the SQLAlchemy session
admin_schema = AdminSchema(session=db.session)
teacher_schema = TeacherSchema(session=db.session)
parent_schema = ParentSchema(session=db.session)
student_schema = StudentSchema(session=db.session)
level_schema = LevelSchema(session=db.session)
semester_schema = SemesterSchema(session=db.session)
module_schema = ModuleSchema(session=db.session)
group_schema = GroupSchema(session=db.session)
salle_schema = SalleSchema(session=db.session)
session_schema = SessionSchema(session=db.session)
absence_schema = AbsenceSchema(session=db.session)
lesson_schema = LessonSchema(session=db.session)
note_schema = NoteSchema(session=db.session)
fee_schema = FeeSchema(session=db.session)
chat_schema = ChatSchema(session=db.session)
message_schema = MessageSchema(session=db.session)
notification_schema = NotificationSchema(session=db.session)
teacher_module_association_schema = TeacherModuleAssociationSchema(session=db.session)
teacher_group_association_schema = TeacherGroupAssociationSchema(session=db.session)

# --- Define a common password ---
COMMON_PLAIN_PASSWORD = "password123"
COMMON_HASHED_PASSWORD = generate_password_hash(COMMON_PLAIN_PASSWORD)


def add_dummy_data():
    if not current_app:
        print("Warning: Flask app context not available. Logging will be basic.")
        logger = print
    else:
        logger = current_app.logger.info

    logger("Starting dummy data population process.")
    logger(f"All users will be created with the password: '{COMMON_PLAIN_PASSWORD}'")

    # --- Users: Admins, Teachers, Parents, Students ---
    # Admins
    admins_instances = []
    for i in range(1, 3):
        admin_data = {
            "first_name": f"Admin{i}",
            "last_name": "User",
            "email": f"admin{i}@example.com",
            "phone_number": f"01020304{i:02d}",
            "is_super_admin": (i == 1),
            "password": COMMON_HASHED_PASSWORD,  # Use common hashed password
        }
        admin_instance = admin_schema.load(admin_data)
        admins_instances.append(admin_instance)
    db.session.add_all(admins_instances)
    logger(f"Prepared {len(admins_instances)} admin instances.")

    # Teachers
    teachers_instances = []
    for i in range(1, 7):
        teacher_data = {
            "first_name": f"Teacher{i}",
            "last_name": f"McTeach{i}",
            "email": f"teacher{i}@example.com",
            "phone_number": f"02030405{i:02d}",
            "address": f"{i} Education Rd, Schoolville",
            "password": COMMON_HASHED_PASSWORD,  # Use common hashed password
        }
        teacher_instance = teacher_schema.load(teacher_data)
        teachers_instances.append(teacher_instance)
    db.session.add_all(teachers_instances)
    logger(f"Prepared {len(teachers_instances)} teacher instances.")

    # Parents
    parents_instances = []
    for i in range(1, 16):
        parent_data = {
            "first_name": f"Parent{i}",
            "last_name": f"Guardian{i}",
            "email": f"parent{i}@example.com",
            "phone_number": f"03040506{i:02d}",
            "address": f"{i} Family Lane, Hometown",
            "is_email_verified": True,
            "is_phone_verified": random.choice([True, False]),
            "password": COMMON_HASHED_PASSWORD,  # Use common hashed password
        }
        parent_instance = parent_schema.load(parent_data)
        parents_instances.append(parent_instance)
    db.session.add_all(parents_instances)
    logger(f"Prepared {len(parents_instances)} parent instances.")

    db.session.flush()
    logger("Flushed session for Admin, Teacher, Parent IDs.")

    # Levels
    levels_data = [
        {"name": "Grade 1", "description": "Primary Level 1"},
        {"name": "Grade 2", "description": "Primary Level 2"},
        {"name": "Grade 3", "description": "Primary Level 3"},
    ]
    levels_instances = [level_schema.load(data) for data in levels_data]
    db.session.add_all(levels_instances)
    db.session.flush()
    logger(f"Created {len(levels_instances)} levels.")

    # Students
    students_instances = []
    if not levels_instances or not parents_instances:
        logger(
            "Error: Cannot create students without levels or parents. Aborting student creation."
        )
    else:
        for i in range(1, 26):
            assigned_level = random.choice(levels_instances)
            assigned_parent = random.choice(parents_instances)
            student_data = {
                "first_name": f"Student{i}",
                "last_name": f"Learner{i}",
                "email": f"student{i}@example.com",
                "level_id": assigned_level.id,
                "parent_id": assigned_parent.id,
                "is_approved": True,
                "docs_url": (
                    f"http://example.com/docs/student{i}" if i % 4 == 0 else None
                ),
                "password": COMMON_HASHED_PASSWORD,  # Use common hashed password
            }
            student_instance = student_schema.load(student_data)
            students_instances.append(student_instance)
        db.session.add_all(students_instances)
        logger(f"Prepared {len(students_instances)} student instances.")
        db.session.flush()

    # Semesters
    semesters_instances = []
    current_year = datetime.now(timezone.utc).year
    for level_inst in levels_instances:
        start_date_fall_obj = date(current_year, 9, 1)
        start_date_spring_obj = date(current_year + 1, 1, 20)
        semester_data_fall = {
            "name": f"{level_inst.name} - Fall {current_year}",
            "level_id": level_inst.id,
            "start_date": start_date_fall_obj.isoformat(),
            "duration": 16,
            "semester_index": 1,
        }
        semester_data_spring = {
            "name": f"{level_inst.name} - Spring {current_year+1}",
            "level_id": level_inst.id,
            "start_date": start_date_spring_obj.isoformat(),
            "duration": 16,
            "semester_index": 2,
        }
        semesters_instances.append(semester_schema.load(semester_data_fall))
        semesters_instances.append(semester_schema.load(semester_data_spring))
    db.session.add_all(semesters_instances)
    db.session.flush()
    logger(f"Created {len(semesters_instances)} semesters.")

    # Modules
    module_names_pool = [
        "Mathematics",
        "Science",
        "History",
        "Language Arts",
        "Geography",
        "Art",
        "Music",
    ]
    modules_instances = []
    for level_inst in levels_instances:
        level_semesters = [
            s for s in semesters_instances if s.level_id == level_inst.id
        ]
        for semester_inst in level_semesters:
            chosen_module_names = random.sample(
                module_names_pool, k=random.randint(2, 4)
            )
            for mod_name in chosen_module_names:
                module_data = {
                    "name": f"{mod_name} ({level_inst.name} - {semester_inst.name.split(' ')[2]})",
                    "description": f"Course for {mod_name} in {level_inst.name}, {semester_inst.name}",
                    "level_id": level_inst.id,
                    "semester_id": semester_inst.id,
                }
                modules_instances.append(module_schema.load(module_data))
    db.session.add_all(modules_instances)
    db.session.flush()
    logger(f"Created {len(modules_instances)} modules.")

    # Groups
    groups_instances = []
    for level_inst in levels_instances:
        for i in range(1, 3):
            group_data = {
                "name": f"{level_inst.name} - Group {chr(64+i)}",
                "level_id": level_inst.id,
            }
            groups_instances.append(group_schema.load(group_data))
    db.session.add_all(groups_instances)
    db.session.flush()
    logger(f"Created {len(groups_instances)} groups.")

    # Assign students to groups
    if students_instances:
        for student_inst in students_instances:
            level_groups = [
                g for g in groups_instances if g.level_id == student_inst.level_id
            ]
            if level_groups:
                student_inst.group_id = random.choice(level_groups).id
        logger("Assigned students to groups.")
        db.session.flush()

    # Salles
    salles_data = [
        {
            "name": f"Room A{100+i}",
            "capacity": random.randint(20, 30),
            "location": f"Building A",
        }
        for i in range(5)
    ]
    salles_data.extend(
        [
            {
                "name": f"Room B{100+i}",
                "capacity": random.randint(15, 25),
                "location": f"Building B",
            }
            for i in range(3)
        ]
    )
    salles_instances = [salle_schema.load(data) for data in salles_data]
    db.session.add_all(salles_instances)
    db.session.flush()
    logger(f"Created {len(salles_instances)} salles.")

    # Associations: Teacher-Module, Teacher-Group
    tm_associations_instances = []
    if not teachers_instances or not modules_instances:
        logger(
            "Skipping Teacher-Module associations due to missing teachers or modules."
        )
    else:
        for module_obj in modules_instances:
            num_teachers = min(len(teachers_instances), random.randint(1, 2))
            assigned_teachers = random.sample(teachers_instances, k=num_teachers)
            for teacher_obj in assigned_teachers:
                if (
                    not db.session.query(TeacherModuleAssociation)
                    .filter_by(teacher_id=teacher_obj.id, module_id=module_obj.id)
                    .first()
                ):
                    assoc_data = {
                        "teacher_id": teacher_obj.id,
                        "module_id": module_obj.id,
                    }
                    instance = teacher_module_association_schema.load(assoc_data)
                    tm_associations_instances.append(instance)
        if tm_associations_instances:
            db.session.add_all(tm_associations_instances)
            logger(
                f"Prepared {len(tm_associations_instances)} Teacher-Module associations."
            )

    tg_associations_instances = []
    if not teachers_instances or not groups_instances:
        logger("Skipping Teacher-Group associations due to missing teachers or groups.")
    else:
        for group_obj in groups_instances:
            num_teachers = min(len(teachers_instances), random.randint(1, 2))
            assigned_teachers = random.sample(teachers_instances, k=num_teachers)
            for teacher_obj in assigned_teachers:
                if (
                    not db.session.query(TeacherGroupAssociation)
                    .filter_by(teacher_id=teacher_obj.id, group_id=group_obj.id)
                    .first()
                ):
                    assoc_data = {
                        "teacher_id": teacher_obj.id,
                        "group_id": group_obj.id,
                    }
                    instance = teacher_group_association_schema.load(assoc_data)
                    tg_associations_instances.append(instance)
        if tg_associations_instances:
            db.session.add_all(tg_associations_instances)
            logger(
                f"Prepared {len(tg_associations_instances)} Teacher-Group associations."
            )
    db.session.flush()
    logger("Flushed session after creating associations.")

    # Sessions
    sessions_instances = []
    time_slots_all = list(TimeSlot)
    if (
        not groups_instances
        or not semesters_instances
        or not modules_instances
        or not tm_associations_instances
        or not salles_instances
    ):
        logger("Skipping session creation due to missing dependencies.")
    else:
        for group_obj in groups_instances:
            group_level_id = group_obj.level_id
            group_semesters = [
                s for s in semesters_instances if s.level_id == group_level_id
            ]
            for semester_obj in group_semesters:
                group_modules = [
                    m
                    for m in modules_instances
                    if m.level_id == group_level_id and m.semester_id == semester_obj.id
                ]
                for module_obj in group_modules:
                    module_teacher_ids = [
                        tma.teacher_id
                        for tma in tm_associations_instances
                        if tma.module_id == module_obj.id
                    ]
                    if not module_teacher_ids:
                        continue
                    for _ in range(random.randint(1, 2)):
                        time_slot_member = random.choice(time_slots_all)
                        session_data = {
                            "teacher_id": random.choice(module_teacher_ids),
                            "module_id": module_obj.id,
                            "group_id": group_obj.id,
                            "semester_id": semester_obj.id,
                            "salle_id": random.choice(salles_instances).id,
                            "time_slot": time_slot_member.value,
                            "weeks": semester_obj.duration,
                            "semester_index": semester_obj.semester_index,
                        }
                        sessions_instances.append(session_schema.load(session_data))
        if sessions_instances:
            db.session.add_all(sessions_instances)
        db.session.flush()
        logger(f"Created {len(sessions_instances)} sessions.")

    # Absences
    absences_instances = []
    created_absence_pairs = set()
    if sessions_instances and students_instances:
        num_absences_to_create = max(10, len(sessions_instances) // 10)
        attempts = 0
        max_attempts = num_absences_to_create * 5
        while (
            len(absences_instances) < num_absences_to_create and attempts < max_attempts
        ):
            attempts += 1
            if not sessions_instances:
                break
            session_obj = random.choice(sessions_instances)
            students_in_group = [
                s
                for s in students_instances
                if hasattr(s, "group_id") and s.group_id == session_obj.group_id
            ]
            if not students_in_group:
                continue
            student_obj = random.choice(students_in_group)
            absence_pair = (student_obj.id, session_obj.id)
            if absence_pair not in created_absence_pairs:
                if (
                    not db.session.query(Absence)
                    .filter_by(student_id=student_obj.id, session_id=session_obj.id)
                    .first()
                ):
                    absence_data = {
                        "student_id": student_obj.id,
                        "session_id": session_obj.id,
                        "justified": random.choice([True, False]),
                        "reason": (
                            "Doctor's appointment"
                            if random.random() > 0.7
                            else "Not specified"
                        ),
                    }
                    loaded_absence = absence_schema.load(absence_data)
                    absences_instances.append(loaded_absence)
                    created_absence_pairs.add(absence_pair)
                else:
                    created_absence_pairs.add(absence_pair)
    if absences_instances:
        db.session.add_all(absences_instances)
        logger(f"Prepared {len(absences_instances)} unique absence instances.")

    # Lessons (Cours)
    lessons_instances = []
    if modules_instances and tm_associations_instances:
        for module_obj in modules_instances:
            module_teacher_ids = [
                tma.teacher_id
                for tma in tm_associations_instances
                if tma.module_id == module_obj.id
            ]
            if not module_teacher_ids:
                continue
            for i in range(random.randint(2, 5)):
                lesson_data = {
                    "title": f"{module_obj.name} - Part {i+1}",
                    "content": f"Detailed content for {module_obj.name}, part {i+1}.",
                    "module_id": module_obj.id,
                    "teacher_id": random.choice(module_teacher_ids),
                }
                lessons_instances.append(lesson_schema.load(lesson_data))
    if lessons_instances:
        db.session.add_all(lessons_instances)

    # Notes
    notes_instances = []
    note_types_all = list(NoteType)
    if (
        students_instances
        and modules_instances
        and sessions_instances
        and tm_associations_instances
    ):
        for student_obj in students_instances:
            if not hasattr(student_obj, "group_id") or not student_obj.group_id:
                continue
            student_sessions = [
                s
                for s in sessions_instances
                if hasattr(s, "group_id") and s.group_id == student_obj.group_id
            ]
            if not student_sessions:
                continue
            student_modules_ids = {
                s.module_id for s in student_sessions if hasattr(s, "module_id")
            }
            for module_id_val in random.sample(
                list(student_modules_ids), k=min(len(student_modules_ids), 3)
            ):
                module_teacher_ids = [
                    tma.teacher_id
                    for tma in tm_associations_instances
                    if tma.module_id == module_id_val
                ]
                if not module_teacher_ids:
                    continue
                for note_type_member in note_types_all:
                    if (
                        not db.session.query(Note)
                        .filter_by(
                            student_id=student_obj.id,
                            module_id=module_id_val,
                            type=note_type_member,
                        )
                        .first()
                    ):
                        note_data = {
                            "student_id": student_obj.id,
                            "module_id": module_id_val,
                            "teacher_id": random.choice(module_teacher_ids),
                            "value": round(random.uniform(5.5, 19.5), 1),
                            "type": note_type_member.name,
                            "comment": random.choice(
                                ["Good work!", "Could improve.", "Excellent!"]
                            ),
                        }
                        notes_instances.append(note_schema.load(note_data))
    if notes_instances:
        db.session.add_all(notes_instances)

    # Fees
    fees_instances = []
    fee_status_all = list(FeeStatus)
    if parents_instances:
        for parent_obj in parents_instances:
            for _ in range(random.randint(0, 2)):
                due_date_val_obj = date.today() + timedelta(
                    days=random.randint(-30, 60)
                )
                status_member = random.choice(fee_status_all)
                fee_data = {
                    "parent_id": parent_obj.id,
                    "amount": round(random.uniform(50.0, 300.0), 2),
                    "description": f"Term {random.randint(1,3)} Fees",
                    "due_date": due_date_val_obj.isoformat(),
                    "status": status_member.value,
                }
                fee_instance = fee_schema.load(fee_data)
                if fee_instance.status == FeeStatus.PAID.value:
                    payment_date_obj = due_date_val_obj - timedelta(
                        days=random.randint(1, 10)
                    )
                    fee_instance.payment_date = payment_date_obj
                elif (
                    fee_instance.status == FeeStatus.UNPAID.value
                    and due_date_val_obj < date.today()
                ):
                    fee_instance.status = FeeStatus.OVERDUE
                fees_instances.append(fee_instance)
    if fees_instances:
        db.session.add_all(fees_instances)

    # Chats & Messages
    if parents_instances and teachers_instances:
        for i in range(min(len(parents_instances), len(teachers_instances), 10)):
            parent_obj, teacher_obj = parents_instances[i], teachers_instances[i]
            chat_data = {"parent_id": parent_obj.id, "teacher_id": teacher_obj.id}
            chat_instance = chat_schema.load(chat_data)
            db.session.add(chat_instance)
            db.session.flush()
            for j in range(random.randint(1, 5)):
                is_teacher_msg = random.choice([True, False])
                msg_sender_id = teacher_obj.id if is_teacher_msg else parent_obj.id
                msg_sender_role = "teacher" if is_teacher_msg else "parent"
                message_data = {
                    "chat_id": chat_instance.id,
                    "sender_id": msg_sender_id,
                    "sender_role": msg_sender_role,
                    "content": f"Hello from {msg_sender_role}, this is message #{j+1} in chat {chat_instance.id}.",
                }
                db.session.add(message_schema.load(message_data))

    # Notifications
    notifications_instances = []
    notification_types_all = list(NotificationType)
    all_user_instances = (
        admins_instances
        + teachers_instances
        + parents_instances
        + (students_instances if students_instances else [])
    )
    if all_user_instances:
        for _ in range(max(20, len(all_user_instances) // 2)):
            recipient_instance = random.choice(all_user_instances)
            if (
                not hasattr(recipient_instance, "id")
                or not recipient_instance.id
                or not hasattr(recipient_instance, "user_type")
            ):
                logger(
                    f"Skipping notification for recipient without ID or user_type: {recipient_instance}"
                )
                continue
            notification_type_member = random.choice(notification_types_all)
            notif_data = {
                "recipient_id": recipient_instance.id,
                "recipient_type": recipient_instance.user_type,
                "message": f"Important update for {getattr(recipient_instance, 'first_name', 'User')}: {random.choice(['New grade posted', 'Upcoming event', 'Fee reminder'])}",
                "notification_type": notification_type_member.name,
                "link": "/dashboard" if random.random() > 0.5 else None,
                "is_read": random.choice([True, False, False]),
                "type": "urgent" if random.random() > 0.8 else "info",
            }
            notifications_instances.append(notification_schema.load(notif_data))
    if notifications_instances:
        db.session.add_all(notifications_instances)
    logger("Prepared all other entity instances.")

    # --- Commit all changes ---
    try:
        db.session.commit()
        logger("Successfully populated the database with dummy data using schemas.")
        print("Successfully populated the database with dummy data using schemas.")
    except Exception as e:
        db.session.rollback()
        logger(f"Error during dummy data population: {e}")
        print(f"Error during dummy data population: {e}")
        import traceback

        print(traceback.format_exc())
        print("Rolling back changes.")
