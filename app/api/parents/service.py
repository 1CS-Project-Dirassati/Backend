from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm.dynamic import AppenderQuery

# from sqlalchemy.orm import aliased # Not used in this snippet
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash

from app import db
from app.models import (
    Parent,
    Student,
    Session,  # Used in _can_user_access_parent_record via teacher link
    Group,  # Used in get_all_parents via teacher_id filter
)

from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

from .utils import dump_data, load_data


class ParentService:

    @staticmethod
    def _can_user_access_parent_record(
        parent: Parent,
        current_user_id: int,
        current_user_role: str,
        allow_archived_view_for_admin=False,
    ) -> bool:
        """Checks if the current user can access THIS SPECIFIC parent record."""
        if not parent:
            return False

        # If parent is archived, special rules apply
        if parent.archived and not (
            current_user_role == "admin" and allow_archived_view_for_admin
        ):
            current_app.logger.debug(
                f"Access denied to archived parent {parent.id} for user {current_user_id} ({current_user_role})."
            )
            return False

        if current_user_role == "admin":
            return True
        if current_user_role == "parent" and parent.id == int(
            current_user_id
        ):  # Parent accessing own (active) profile
            return True
        if (
            current_user_role == "teacher"
        ):  # Teacher can access parent if they teach one of their (active) students
            # Check if parent has any active students taught by this teacher
            has_link = (
                db.session.query(Parent.id)
                .join(Parent.students)
                .filter(Student.archived == False)
                .join(Student.group)
                .join(Group.sessions)
                .filter(Session.teacher_id == current_user_id, Parent.id == parent.id)
                .first()
            )
            return bool(has_link)

        current_app.logger.warning(
            f"User {current_user_id} ({current_user_role}) denied access to parent {parent.id}."
        )
        return False

    @staticmethod
    def get_parent_data(parent_id: int, current_user_id: int, current_user_role: str):
        parent = Parent.query.get(parent_id)
        allow_archived_view = current_user_role == "admin"

        if not parent:
            return err_resp("Parent not found!", "parent_404", 404)

        if not ParentService._can_user_access_parent_record(
            parent,
            current_user_id,
            current_user_role,
            allow_archived_view_for_admin=allow_archived_view,
        ):
            return err_resp(
                "Forbidden or Parent not found.",
                "access_denied_or_not_found",
                403 if parent.archived else 404,
            )

        try:
            parent_data = dump_data(parent)
            resp = message(True, "Parent data sent successfully")
            resp["parent"] = parent_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error serializing parent {parent_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def get_all_parents(
        is_email_verified=None,
        is_phone_verified=None,
        student_id=None,
        teacher_id=None,
        archived=0,  # Default to 0 (not archived)
        page=None,
        per_page=None,
        current_user_role=None,  # current_user_id not strictly needed here if role is sufficient for scoping
    ):
        page = page or 1
        per_page = per_page or 10
        archived_bool = bool(archived)  # Convert int (0/1) to boolean

        try:
            query = Parent.query
            filters_applied = {"archived": archived_bool}  # Start with archived status

            # Apply archived filter first
            # Only admins can request a list of archived parents.
            # Teachers and other roles will always see non-archived parents by default.
            if current_user_role != "admin" and archived_bool:
                current_app.logger.warning(
                    f"Non-admin user ({current_user_role}) attempted to list archived parents. Overriding to non-archived."
                )
                query = query.filter(Parent.archived == False)
                filters_applied["archived"] = False  # Log what is actually applied
            else:
                query = query.filter(Parent.archived == archived_bool)

            if is_email_verified is not None:
                filters_applied["is_email_verified"] = is_email_verified
                query = query.filter(Parent.is_email_verified == is_email_verified)
            if is_phone_verified is not None:
                filters_applied["is_phone_verified"] = is_phone_verified
                query = query.filter(Parent.is_phone_verified == is_phone_verified)

            if student_id is not None:  # Filter by specific student
                filters_applied["student_id"] = student_id
                query = query.join(Parent.students).filter(
                    Student.id == student_id, Student.archived == False
                )  # Only consider active students for this link

            if (
                teacher_id is not None
            ):  # Filter by teacher of one of their active students
                filters_applied["teacher_id"] = teacher_id
                query = (
                    query.join(Parent.students)
                    .filter(Student.archived == False)
                    .join(Student.group)
                    .join(Group.sessions)
                    .filter(Session.teacher_id == teacher_id)
                    .distinct()
                )

            current_app.logger.debug(f"Applying parent list filters: {filters_applied}")
            query = query.order_by(Parent.last_name, Parent.first_name)
            paginated_parents = query.paginate(
                page=page, per_page=per_page, error_out=False
            )

            parents_data = dump_data(paginated_parents.items, many=True)
            resp = message(True, "Parents list retrieved successfully")
            resp.update(
                {
                    "parents": parents_data,
                    "total": paginated_parents.total,
                    "pages": paginated_parents.pages,
                    "current_page": paginated_parents.page,
                    "per_page": paginated_parents.per_page,
                    "has_next": paginated_parents.has_next,
                    "has_prev": paginated_parents.has_prev,
                }
            )
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting parents list: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def create_parent(data: dict):
        try:
            # Check if email already exists (active or archived)
            existing_parent = Parent.query.filter_by(email=data.get("email")).first()
            if existing_parent:
                status = "archived" if existing_parent.archived else "active"
                return err_resp(
                    f"Email '{data.get('email')}' already exists for an {status} parent.",
                    "duplicate_email",
                    409,
                )

            # load_data uses ParentSchema. ParentSchema should not allow loading 'archived'.
            new_parent_instance = load_data(data)  # Schema validates other fields
            new_parent_instance.archived = (
                False  # Explicitly set new parents as not archived
            )

            # Handle password (assuming schema has password as load_only or you get it from raw data)
            if "password" in data:
                new_parent_instance.password = generate_password_hash(data["password"])
            else:  # Should be caught by DTO validation if password is required
                return err_resp("Password is required.", "password_missing", 400)

            db.session.add(new_parent_instance)
            db.session.commit()
            parent_resp_data = dump_data(new_parent_instance)
            return {
                "status": True,
                "message": "Parent created successfully.",
                "parent": parent_resp_data,
            }, 201
        except ValidationError as err:
            db.session.rollback()
            return validation_error(False, err.messages), 400
        except IntegrityError:  # Mostly for email if somehow not caught by pre-check
            db.session.rollback()
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating parent: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def update_parent_by_admin(parent_id: int, data: dict):
        parent = Parent.query.filter_by(
            id=parent_id, archived=False
        ).first()  # Can only update non-archived
        if not parent:
            return err_resp(
                "Parent not found or is archived.", "parent_not_active_update", 404
            )
        if not data:
            return err_resp("Request body cannot be empty.", "empty_update_data", 400)

        data.pop("archived", None)  # Archived status not updatable here
        data.pop("email", None)  # Email typically not changed this way
        data.pop("password", None)  # Password change should be a separate flow

        try:
            updated_parent = load_data(
                data, partial=True, instance=parent
            )  # ParentSchema for admin update
            db.session.commit()
            return {
                "status": True,
                "message": "Parent updated successfully.",
                "parent": dump_data(updated_parent),
            }, 200
        except ValidationError as err:
            db.session.rollback()
            return validation_error(False, err.messages), 400
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error updating parent {parent_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def update_own_profile(current_user_id: int, data: dict):
        parent = Parent.query.filter_by(
            id=current_user_id, archived=False
        ).first()  # Can only update own non-archived profile
        if not parent:
            return err_resp(
                "Parent profile not found or is archived.",
                "parent_profile_not_active",
                403,
            )  # 403 as they are authenticated but profile is non-interactive
        if not data:
            return err_resp("Request body cannot be empty.", "empty_update_data", 400)

        data.pop("archived", None)
        data.pop("email", None)
        data.pop("password", None)
        data.pop("is_email_verified", None)  # Cannot change verification status
        data.pop("is_phone_verified", None)

        try:
            updated_parent = load_data(
                data, partial=True, instance=parent
            )  # ParentSelfUpdateSchema
            db.session.commit()
            return {
                "status": True,
                "message": "Profile updated successfully.",
                "parent": dump_data(updated_parent),
            }, 200
        except ValidationError as err:
            db.session.rollback()
            return validation_error(False, err.messages), 400
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error parent self-update {current_user_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def archive_parent(parent_id: int):
        """Archive a parent and all their associated active students."""
        parent = Parent.query.get(parent_id)
        if not parent:
            return err_resp("Parent not found!", "parent_404", 404)

        if parent.archived:
            # If parent is already archived, ensure all their students are also archived.
            # This handles cases where a student might have been unarchived independently.
            archived_student_count_during_recheck = 0
            if isinstance(parent.students, AppenderQuery):  # Check if lazy="dynamic"
                for student in parent.students.filter_by(archived=False).all():
                    student.archived = True
                    archived_student_count_during_recheck += 1
            else:  # Fallback for non-dynamic (InstrumentedList)
                for student in parent.students:
                    if not student.archived:
                        student.archived = True
                        archived_student_count_during_recheck += 1

            if archived_student_count_during_recheck > 0:
                db.session.commit()
                current_app.logger.info(
                    f"{archived_student_count_during_recheck} active student(s) of already archived parent {parent_id} were also archived."
                )
                msg = f"Parent is already archived. {archived_student_count_during_recheck} associated active student(s) have now also been archived."
            else:
                msg = "Parent is already archived. No active students found to re-archive."

            return {"status": True, "message": msg, "parent": dump_data(parent)}, 200

        try:
            parent.archived = True
            current_app.logger.info(f"Parent {parent_id} marked as archived.")

            archived_student_count = 0
            # Check if parent.students is a dynamic relationship (AppenderQuery)
            if isinstance(parent.students, AppenderQuery):
                students_to_archive = parent.students.filter_by(archived=False).all()
                for student in students_to_archive:
                    student.archived = True
                    archived_student_count += 1
                    current_app.logger.info(
                        f"Cascaded archive to student ID: {student.id} (child of parent {parent_id})"
                    )
            else:  # Fallback for non-dynamic (InstrumentedList) - less efficient for large numbers
                current_app.logger.warning(
                    f"Parent.students relationship for parent {parent_id} is not lazy='dynamic'. Iterating list for cascade archive."
                )
                for student in parent.students:
                    if not student.archived:
                        student.archived = True
                        archived_student_count += 1
                        current_app.logger.info(
                            f"Cascaded archive to student ID: {student.id} (child of parent {parent_id})"
                        )

            db.session.commit()
            msg = f"Parent and {archived_student_count} associated student(s) archived successfully."
            current_app.logger.info(msg)
            return {"status": True, "message": msg, "parent": dump_data(parent)}, 200
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error archiving parent {parent_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def unarchive_parent(parent_id: int):
        """Unarchive a parent. Does NOT automatically unarchive students."""
        parent = Parent.query.get(parent_id)
        if not parent:
            return err_resp("Parent not found!", "parent_404", 404)

        if not parent.archived:
            return {
                "status": True,
                "message": "Parent is already active.",
                "parent": dump_data(parent),
            }, 200

        try:
            existing_active_parent = Parent.query.filter(
                Parent.email == parent.email,
                Parent.archived == False,
                Parent.id != parent_id,
            ).first()
            if existing_active_parent:
                return err_resp(
                    f"Cannot unarchive. Email '{parent.email}' is already in use by an active parent.",
                    "email_conflict_unarchive",
                    409,
                )

            parent.archived = False
            db.session.commit()
            current_app.logger.info(f"Parent unarchived successfully: ID {parent_id}")
            return {
                "status": True,
                "message": "Parent unarchived successfully. Associated students remain archived if they were archived.",
                "parent": dump_data(parent),
            }, 200
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error unarchiving parent {parent_id}: {error}", exc_info=True
            )
            return internal_err_resp()

    @staticmethod
    def unarchive_parent(parent_id: int):
        """Unarchive a parent. Does NOT automatically unarchive students."""
        parent = Parent.query.get(parent_id)
        if not parent:
            return err_resp("Parent not found!", "parent_404", 404)

        if not parent.archived:
            return {
                "status": True,
                "message": "Parent is already active.",
                "parent": dump_data(parent),
            }, 200

        try:
            # Check for email conflict with another active parent before unarchiving
            # This is a safety measure, though unique constraint should handle it.
            existing_active_parent = Parent.query.filter(
                Parent.email == parent.email,
                Parent.archived == False,
                Parent.id != parent_id,
            ).first()
            if existing_active_parent:
                return err_resp(
                    f"Cannot unarchive. Email '{parent.email}' is already in use by an active parent.",
                    "email_conflict_unarchive",
                    409,
                )

            parent.archived = False
            # Students are NOT automatically unarchived here.
            # Admin must unarchive students individually if desired.
            db.session.commit()
            current_app.logger.info(f"Parent unarchived successfully: ID {parent_id}")
            return {
                "status": True,
                "message": "Parent unarchived successfully. Associated students remain archived if they were archived.",
                "parent": dump_data(parent),
            }, 200
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                f"Error unarchiving parent {parent_id}: {error}", exc_info=True
            )
            return internal_err_resp()
