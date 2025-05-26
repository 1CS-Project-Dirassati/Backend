from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError

from app import db
from app.models import (
    Session,
    Teacher,
    Module,
    Group,
    Semester,
    Salle,
    Student,  # Keep Student if used for role-based filtering
    TeacherModuleAssociation,  # Keep if get_group_time_slots uses it
)
from app.models.TimeSlot import TimeSlot as TimeSlotEnum  # Rename to avoid conflict

from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

from .utils import dump_data, load_data


class SessionService:

    @staticmethod
    def _validate_foreign_keys(data: dict, check_semester_index, target_semester):
        errors = {}
        if data.get("teacher_id") is not None and not Teacher.query.get(
            data["teacher_id"]
        ):
            errors["teacher_id"] = f"Teacher with ID {data['teacher_id']} not found."
        if data.get("module_id") is not None and not Module.query.get(
            data["module_id"]
        ):
            errors["module_id"] = f"Module with ID {data['module_id']} not found."
        if data.get("group_id") is not None and not Group.query.get(data["group_id"]):
            errors["group_id"] = f"Group with ID {data['group_id']} not found."

        # Semester validation is now more complex due to semester_index
        semester_id = data.get("semester_id")
        input_semester_index = data.get("semester_index")

        if semester_id is not None:
            semester = target_semester or Semester.query.get(
                semester_id
            )  # Use target_semester if provided (from create context)
            if not semester:
                errors["semester_id"] = f"Semester with ID {semester_id} not found."
            elif check_semester_index and input_semester_index is not None:
                # Ensure the Session's semester_index matches the actual Semester's semester_index
                if semester.semester_index != input_semester_index:
                    errors["semester_index"] = (
                        f"Provided semester_index {input_semester_index} does not match "
                        f"the index ({semester.semester_index}) of Semester ID {semester_id}."
                    )
        elif check_semester_index and input_semester_index is not None:
            # If semester_id is not given but semester_index is, it's an issue for session creation
            errors["semester_id"] = (
                "semester_id is required when semester_index is provided for a session."
            )

        if (
            data.get("salle_id") is not None
            and data["salle_id"] != ""
            and not Salle.query.get(data["salle_id"])
        ):  # Check for empty string too
            errors["salle_id"] = f"Salle with ID {data['salle_id']} not found."

        # Validate time_slot enum value
        if data.get("time_slot") and data.get("time_slot") not in [
            ts.value for ts in TimeSlotEnum
        ]:
            errors["time_slot"] = f"Invalid time_slot value: {data.get('time_slot')}."

        return errors

    @staticmethod
    def get_group_time_slots(group_id):
        try:
            group = Group.query.get(group_id)
            if not group:
                return err_resp("Group not found!", "group_404", 404)

            # Assuming Semester has level_id and semester_index
            # We might need to infer the "current" or relevant semester for the group
            # For simplicity, let's assume we are looking for availability in any relevant semester
            # This logic might need refinement based on how "active" semester is determined for a group.

            level_modules = Module.query.filter_by(level_id=group.level_id).all()
            if not level_modules:
                return message(True, "No modules found for this group's level"), 200

            time_slots_availability = {slot.value: [] for slot in TimeSlotEnum}

            for module in level_modules:
                teacher_associations = TeacherModuleAssociation.query.filter_by(
                    module_id=module.id
                ).all()
                for assoc in teacher_associations:
                    teacher = Teacher.query.get(assoc.teacher_id)
                    if not teacher:
                        continue

                    # Check teacher's existing sessions FOR THIS GROUP'S POTENTIAL SEMESTERS
                    # This is complex: which semester(s) are we checking against?
                    # For now, let's simplify: find slots where this teacher ISN'T teaching ANY group.
                    # A more precise check would be for the specific semester(s) the group is in.

                    teacher_group_sessions = Session.query.filter_by(
                        teacher_id=teacher.id,
                        # semester_id=current_semester_for_group.id # This needs defining
                        # group_id=group_id # Could also check if teacher is busy with THIS group already
                    ).all()

                    occupied_slots_for_teacher = {
                        session.time_slot.value for session in teacher_group_sessions
                    }

                    for slot_enum in TimeSlotEnum:
                        slot_value = slot_enum.value
                        if slot_value not in occupied_slots_for_teacher:
                            # Check if this group already has a session at this time slot
                            group_has_session_at_slot = Session.query.filter_by(
                                group_id=group_id,
                                time_slot=slot_enum,  # Use the enum member here
                                # semester_id=current_semester_for_group.id # Again, needs specific semester
                            ).first()

                            if not group_has_session_at_slot:
                                time_slots_availability[slot_value].append(
                                    {
                                        "teacher_id": teacher.id,
                                        "teacher_name": f"{teacher.first_name} {teacher.last_name}",
                                        "module_id": module.id,
                                        "module_name": module.name,
                                    }
                                )

            # Filter out duplicates if a teacher can teach multiple modules they are free for at the same slot
            for slot, L in time_slots_availability.items():
                time_slots_availability[slot] = [
                    dict(t) for t in {tuple(d.items()) for d in L}
                ]

            resp = message(True, "Time slot map retrieved successfully")
            resp["time_slots"] = time_slots_availability
            return resp, 200

        except Exception as error:
            current_app.logger.error(
                f"Error getting time slots for group {group_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def get_session_data(session_id: int):
        session = Session.query.get(session_id)
        if not session:
            current_app.logger.info(f"Session with ID {session_id} not found.")
            return err_resp("Session not found!", "session_404", 404)
        try:
            session_data = dump_data(
                session
            )  # Assumes SessionSchema handles all fields

            # Add related names if SessionSchema doesn't include them via relationships
            if not session_data.get("teacher_name") and session.teacher:
                session_data["teacher_name"] = (
                    f"{session.teacher.first_name} {session.teacher.last_name}"
                )
            if not session_data.get("module_name") and session.module:
                session_data["module_name"] = session.module.name
            if not session_data.get("group_name") and session.group:
                session_data["group_name"] = session.group.name
            if not session_data.get("semester_name") and session.semester:
                session_data["semester_name"] = session.semester.name
            if not session_data.get("salle_name") and session.salle:
                session_data["salle_name"] = session.salle.name
            # semester_index should be directly on session_data from dump_data

            resp = message(True, "Session data sent successfully")
            resp["session"] = session_data
            current_app.logger.debug(f"Successfully retrieved session ID {session_id}")
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing session data for ID {session_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def get_all_sessions(
        group_id=None,
        teacher_id=None,
        semester_id=None,
        semester_index=None,
        week=None,  # ADDED semester_index
        page=None,
        per_page=None,
        current_user_id=None,
        current_user_role=None,
    ):
        page = page or 1
        per_page = per_page or 10

        try:
            query = Session.query
            filters_applied = {}

            if current_user_role == "teacher" and (
                teacher_id is None or int(teacher_id) == int(current_user_id)
            ):
                filters_applied["teacher_id_role"] = current_user_id
                query = query.filter(Session.teacher_id == current_user_id)
            elif teacher_id is not None:
                filters_applied["teacher_id"] = teacher_id
                query = query.filter(Session.teacher_id == teacher_id)

            if current_user_role == "student":
                student = Student.query.get(current_user_id)
                if (
                    student
                    and student.group_id
                    and (group_id is None or int(group_id) == student.group_id)
                ):
                    filters_applied["group_id_role"] = student.group_id
                    query = query.filter(Session.group_id == student.group_id)
                elif (
                    group_id is None
                ):  # If student has no group and no explicit group_id filter, return empty
                    current_app.logger.warning(
                        f"Student {current_user_id} has no group; returning no sessions."
                    )
                    return {
                        "status": True,
                        "message": "No sessions found for student (not in a group).",
                        "sessions": [],
                        "total": 0,
                        "pages": 0,
                        "current_page": 1,
                        "per_page": per_page,
                        "has_next": False,
                        "has_prev": False,
                    }, 200
            elif group_id is not None:
                filters_applied["group_id"] = group_id
                query = query.filter(Session.group_id == group_id)

            if semester_id is not None:
                filters_applied["semester_id"] = semester_id
                query = query.filter(Session.semester_id == semester_id)
            if semester_index is not None:  # ADDED filter logic
                filters_applied["semester_index"] = semester_index
                query = query.filter(Session.semester_index == semester_index)
            if week is not None:  # 'week' here refers to Session.weeks
                filters_applied["week"] = week
                query = query.filter(Session.weeks == week)

            if filters_applied:
                current_app.logger.debug(
                    f"Applying session list filters: {filters_applied}"
                )

            query = query.order_by(
                Session.semester_id,
                Session.semester_index,
                Session.weeks,
                Session.time_slot,
            )

            paginated_sessions = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.debug(
                f"Paginated sessions items count: {len(paginated_sessions.items)}"
            )

            # Efficiently fetch related data to avoid N+1 queries
            # (Your previous preloading logic was good, adapting it slightly)
            items = paginated_sessions.items
            teacher_ids = {s.teacher_id for s in items if s.teacher_id}
            module_ids = {s.module_id for s in items if s.module_id}
            group_ids = {s.group_id for s in items if s.group_id}
            semester_ids = {s.semester_id for s in items if s.semester_id}
            salle_ids = {s.salle_id for s in items if s.salle_id}

            teachers = (
                {
                    t.id: t
                    for t in Teacher.query.filter(Teacher.id.in_(teacher_ids)).all()
                }
                if teacher_ids
                else {}
            )
            modules = (
                {m.id: m for m in Module.query.filter(Module.id.in_(module_ids)).all()}
                if module_ids
                else {}
            )
            groups = (
                {g.id: g for g in Group.query.filter(Group.id.in_(group_ids)).all()}
                if group_ids
                else {}
            )
            semesters = (
                {
                    s.id: s
                    for s in Semester.query.filter(Semester.id.in_(semester_ids)).all()
                }
                if semester_ids
                else {}
            )
            salles = (
                {s.id: s for s in Salle.query.filter(Salle.id.in_(salle_ids)).all()}
                if salle_ids
                else {}
            )

            sessions_data = dump_data(items, many=True)  # dump_data uses SessionSchema

            for session_data_item in sessions_data:
                teacher = teachers.get(session_data_item.get("teacher_id"))
                module = modules.get(session_data_item.get("module_id"))
                group = groups.get(session_data_item.get("group_id"))
                semester = semesters.get(session_data_item.get("semester_id"))
                salle = salles.get(session_data_item.get("salle_id"))

                session_data_item["teacher_name"] = (
                    f"{teacher.first_name} {teacher.last_name}" if teacher else None
                )
                session_data_item["module_name"] = module.name if module else None
                session_data_item["group_name"] = group.name if group else None
                session_data_item["semester_name"] = semester.name if semester else None
                # session_data_item["semester_index"] is already in session_data_item from dump_data
                session_data_item["salle_name"] = salle.name if salle else None

            current_app.logger.debug(f"Serialized {len(sessions_data)} sessions")
            resp = message(True, "Sessions list retrieved successfully")
            resp["sessions"] = sessions_data
            resp["total"] = paginated_sessions.total
            resp["pages"] = paginated_sessions.pages
            resp["current_page"] = paginated_sessions.page
            resp["per_page"] = paginated_sessions.per_page
            resp["has_next"] = paginated_sessions.has_next
            resp["has_prev"] = paginated_sessions.has_prev

            current_app.logger.debug(
                f"Successfully retrieved sessions page {page}. Total: {paginated_sessions.total}"
            )
            return resp, 200

        except Exception as error:
            log_msg = f"Error getting sessions"
            if filters_applied:
                log_msg += f" with filters {filters_applied}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def create_session(data: dict):
        try:
            # 1. Validate Semester and its semester_index
            semester_id = data.get("semester_id")
            input_session_semester_index = data.get("semester_index")

            if semester_id is None:
                return err_resp("semester_id is required.", "missing_semester_id", 400)
            if input_session_semester_index is None:
                return err_resp(
                    "semester_index is required for the session.",
                    "missing_semester_index",
                    400,
                )
            if (
                not isinstance(input_session_semester_index, int)
                or input_session_semester_index <= 0
            ):
                return err_resp(
                    "Session semester_index must be a positive integer.",
                    "invalid_session_semester_index",
                    400,
                )

            semester = Semester.query.get(semester_id)
            if not semester:
                return err_resp(
                    f"Semester with ID {semester_id} not found!", "semester_404", 400
                )
            if not semester.duration or semester.duration <= 0:
                return err_resp(
                    f"Semester ID {semester_id} has an invalid or missing duration.",
                    "semester_duration_invalid",
                    400,
                )

            # Crucial Check: Ensure the session's semester_index matches the parent Semester's index
            if semester.semester_index != input_session_semester_index:
                return err_resp(
                    f"Provided session semester_index ({input_session_semester_index}) "
                    f"does not match the index ({semester.semester_index}) of Semester ID {semester_id}.",
                    "semester_index_mismatch",
                    400,
                )

            # 2. Foreign Key Validation (excluding semester_index as it's validated against the Semester object)
            # Pass the fetched semester to _validate_foreign_keys to use it directly
            fk_errors = SessionService._validate_foreign_keys(
                data, check_semester_index=False, target_semester=semester
            )
            if fk_errors:
                current_app.logger.warning(
                    f"Foreign key validation failed creating session: {fk_errors}. Data: {data}"
                )
                return validation_error(False, fk_errors), 400

            # 3. Create sessions for each week of the semester's duration
            created_session_objects = []
            base_session_data = data.copy()  # Use the validated input data as a base

            for week_num in range(1, semester.duration + 1):
                # Create a new Session instance for each week
                # load_data should ideally handle creating a new instance from dict.
                # SessionSchema should map all fields including semester_index.
                session_instance_data = base_session_data.copy()
                session_instance_data["weeks"] = (
                    week_num  # Set the specific week for this session instance
                )

                # The `semester_index` from input `data` is already validated against the chosen `Semester`
                # and will be part of `session_instance_data` passed to `load_data`.

                # Validate for conflicts (teacher, group, or salle busy at this time_slot for this specific week and semester_index)
                # This check needs to be robust.
                conflict_check = (
                    Session.query.filter_by(
                        time_slot=session_instance_data.get("time_slot"),
                        semester_id=semester.id,  # Filter by the specific semester
                        semester_index=input_session_semester_index,  # Filter by specific semester_index
                        weeks=week_num,  # Filter by specific week
                    )
                    .filter(
                        db.or_(
                            Session.teacher_id
                            == session_instance_data.get("teacher_id"),
                            Session.group_id == session_instance_data.get("group_id"),
                            (
                                Session.salle_id
                                == session_instance_data.get("salle_id")
                                if session_instance_data.get("salle_id")
                                else False
                            ),
                        )
                    )
                    .first()
                )

                if conflict_check:
                    db.session.rollback()  # Rollback if any conflict is found during the loop
                    entity = "Teacher"
                    if conflict_check.group_id == session_instance_data.get("group_id"):
                        entity = "Group"
                    elif (
                        conflict_check.salle_id
                        and conflict_check.salle_id
                        == session_instance_data.get("salle_id")
                    ):
                        entity = "Salle"
                    current_app.logger.warning(
                        f"Conflict: {entity} busy at {session_instance_data.get('time_slot')} for week {week_num}, semester_index {input_session_semester_index}."
                    )
                    return err_resp(
                        f"{entity} is already scheduled at this time slot for week {week_num} of semester index {input_session_semester_index}.",
                        "schedule_conflict",
                        409,
                    )

                new_session_obj_for_week = load_data(
                    session_instance_data
                )  # Create new instance
                db.session.add(new_session_obj_for_week)
                created_session_objects.append(new_session_obj_for_week)

            db.session.commit()
            current_app.logger.info(
                f"Created {len(created_session_objects)} session instances for semester ID {semester.id}, index {input_session_semester_index}."
            )

            sessions_data_resp = dump_data(created_session_objects, many=True)
            # Enrich with names if not handled by dump_data's schema
            for s_data in sessions_data_resp:
                if not s_data.get("teacher_name") and s_data.get("teacher_id"):
                    t = Teacher.query.get(s_data.get("teacher_id"))
                    s_data["teacher_name"] = (
                        f"{t.first_name} {t.last_name}" if t else None
                    )
                # ... similar enrichment for module, group, semester, salle ...

            resp = message(
                True,
                f"Created {len(created_session_objects)} session instances successfully.",
            )
            resp["sessions"] = sessions_data_resp  # Return the list of created sessions
            return resp, 201

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error creating session(s): {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"DB integrity error creating session(s): {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"DB error creating session(s): {error}. Data: {data}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error creating session(s): {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def update_session(session_id: int, data: dict):
        session = Session.query.get(session_id)
        if not session:
            current_app.logger.info(
                f"Attempted to update non-existent session ID: {session_id}"
            )
            return err_resp("Session not found!", "session_404", 404)

        if not data:
            current_app.logger.warning(
                f"Attempted update for session {session_id} with empty data."
            )
            return err_resp(
                "Request body cannot be empty for update.", "empty_update_data", 400
            )

        try:
            # Validate semester_index if provided and changed
            # The target semester_id for the session usually does not change in an update.
            # If semester_id or semester_index changes, it implies moving the session, which is complex.
            # For now, assume semester_id is fixed for a session, and semester_index on session must match its Semester.

            target_semester_id = data.get("semester_id", session.semester_id)
            target_semester_index = data.get("semester_index", session.semester_index)

            if not isinstance(target_semester_index, int) or target_semester_index <= 0:
                return err_resp(
                    "Session semester_index must be a positive integer.",
                    "invalid_session_semester_index_update",
                    400,
                )

            target_semester = Semester.query.get(target_semester_id)
            if not target_semester:
                return err_resp(
                    f"Target semester with ID {target_semester_id} not found.",
                    "target_semester_404",
                    400,
                )

            if target_semester.semester_index != target_semester_index:
                return err_resp(
                    f"Provided session semester_index ({target_semester_index}) "
                    f"does not match the index ({target_semester.semester_index}) of the target Semester ID {target_semester_id}.",
                    "semester_index_mismatch_update",
                    400,
                )

            # FK validation for other fields being updated
            fk_errors = SessionService._validate_foreign_keys(
                data, check_semester_index=False, target_semester=target_semester
            )  # No need to re-check semester_index against itself here
            if fk_errors:
                return validation_error(False, fk_errors), 400

            # Conflict check for the updated values
            # Construct a query for potential conflicts, excluding the current session
            new_time_slot_value = data.get(
                "time_slot", session.time_slot.value
            )  # Use .value for comparison if session.time_slot is enum
            new_teacher_id = data.get("teacher_id", session.teacher_id)
            new_group_id = data.get("group_id", session.group_id)
            new_salle_id = data.get("salle_id", session.salle_id)
            # semester_id, semester_index, and weeks are part of the unique context of a session instance

            conflict_query = Session.query.filter(
                Session.id != session_id,  # Exclude current session
                Session.time_slot
                == TimeSlotEnum(
                    new_time_slot_value
                ),  # Convert string to enum for query
                Session.semester_id == target_semester_id,
                Session.semester_index == target_semester_index,
                Session.weeks
                == data.get("weeks", session.weeks),  # Check against the specific week
            )

            # Check for teacher conflict
            if (
                new_teacher_id
                and conflict_query.filter(Session.teacher_id == new_teacher_id).first()
            ):
                return err_resp(
                    f"Teacher is already scheduled at this time slot for this specific week and semester index.",
                    "teacher_conflict_update",
                    409,
                )
            # Check for group conflict
            if (
                new_group_id
                and conflict_query.filter(Session.group_id == new_group_id).first()
            ):
                return err_resp(
                    f"Group is already scheduled at this time slot for this specific week and semester index.",
                    "group_conflict_update",
                    409,
                )
            # Check for salle conflict
            if (
                new_salle_id
                and conflict_query.filter(Session.salle_id == new_salle_id).first()
            ):
                return err_resp(
                    f"Salle is already booked at this time slot for this specific week and semester index.",
                    "salle_conflict_update",
                    409,
                )

            updated_session = load_data(data, partial=True, instance=session)
            current_app.logger.debug(
                f"Session data validated. Committing changes for ID: {session_id}"
            )

            db.session.commit()
            current_app.logger.info(
                f"Session updated successfully for ID: {session_id}"
            )

            session_resp_data = dump_data(updated_session)
            # Enrich with names
            if not session_resp_data.get("teacher_name") and updated_session.teacher:
                session_resp_data["teacher_name"] = (
                    f"{updated_session.teacher.first_name} {updated_session.teacher.last_name}"
                )
            # ... similar enrichment ...

            resp = message(True, "Session updated successfully")
            resp["session"] = session_resp_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Schema validation error updating session {session_id}: {err.messages}. Data: {data}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"DB integrity error updating session {session_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"DB error updating session {session_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating session {session_id}: {error}. Data: {data}",
                exc_info=True,
            )
            return internal_err_resp()

    @staticmethod
    def delete_session(session_id: int):
        session = Session.query.get(session_id)
        if not session:
            current_app.logger.info(
                f"Attempted to delete non-existent session ID: {session_id}"
            )
            return err_resp("Session not found!", "session_404", 404)
        try:
            current_app.logger.debug(f"Deleting session ID: {session_id}")
            db.session.delete(session)
            db.session.commit()
            current_app.logger.info(f"Session deleted successfully: ID {session_id}")
            return None, 204
        except (
            IntegrityError
        ) as e:  # Catch integrity errors if sessions are linked (e.g. absences) and cascade isn't set
            db.session.rollback()
            current_app.logger.error(
                f"Integrity error deleting session {session_id}: {e}", exc_info=True
            )
            return err_resp(
                "Cannot delete session due to existing related records (e.g., absences).",
                "delete_conflict_related_records",
                409,
            )
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting session {session_id}: {error}", exc_info=True
            )
            return err_resp(
                "Could not delete session due to a database error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error deleting session {session_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()
