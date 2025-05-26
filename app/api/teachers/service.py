from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash

from app import db
from app.models import Teacher, Session, Module, TeacherModuleAssociation # Removed Specialization

from app.models.Schemas import TeacherModuleAssociationSchema
from app.utils import err_resp, message, internal_err_resp, validation_error
from .utils import dump_data, load_data


class TeacherService:

    @staticmethod
    def _validate_foreign_keys(data, instance=None): # Removed specialization_id check
        errors = {}
        # Add other FK validations if Teacher model gets more relations
        return errors

    @staticmethod
    def _can_user_access_teacher_record(teacher: Teacher, current_user_id: int, current_user_role: str, allow_archived_view_for_admin=False) -> bool:
        if not teacher: return False

        if teacher.archived:
            if current_user_role == "admin" and allow_archived_view_for_admin:
                return True
            if current_user_role == "teacher" and teacher.id == int(current_user_id):
                return True
            current_app.logger.debug(f"Access denied to archived teacher {teacher.id} for user {current_user_id} ({current_user_role}).")
            return False

        if current_user_role == "admin": return True
        if current_user_role == "teacher": return True
        if current_user_role == "parent": return True

        current_app.logger.warning(f"User {current_user_id} ({current_user_role}) denied access to teacher {teacher.id}.")
        return False

    @staticmethod
    def get_teacher_data(teacher_id: int, current_user_id: int, current_user_role: str):
        teacher = Teacher.query.get(teacher_id)
        allow_archived_view = current_user_role == "admin" or \
                              (current_user_role == "teacher" and int(current_user_id) == teacher_id)

        if not teacher:
            return err_resp("Teacher not found!", "teacher_404", 404)

        if not TeacherService._can_user_access_teacher_record(teacher, current_user_id, current_user_role, allow_archived_view_for_admin=allow_archived_view):
            return err_resp("Forbidden or Teacher not found.", "access_denied_or_not_found", 403 if teacher.archived else 404)

        try:
            teacher_data = dump_data(teacher)
            # Removed specialization_name enrichment
            return {"status": True, "message": "Teacher data sent successfully.", "teacher": teacher_data}, 200
        except Exception as e:
            current_app.logger.error(f"Error getting teacher {teacher_id}: {e}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def get_all_teachers(
        module_id=None, archived=0, # Removed specialization_id
        page=None, per_page=None,
        current_user_role=None, current_user_id=None
    ):
        page = page or 1
        per_page = per_page or 10
        archived_bool = bool(archived)

        try:
            query = Teacher.query
            filters_applied = {"archived": archived_bool}

            if current_user_role != "admin" and archived_bool:
                current_app.logger.warning(f"Non-admin {current_user_id} ({current_user_role}) tried to list archived teachers. Showing non-archived.")
                query = query.filter(Teacher.archived == False)
                filters_applied["archived"] = False
            else:
                query = query.filter(Teacher.archived == archived_bool)

            # Removed specialization_id filter
            if module_id is not None:
                filters_applied["module_id"] = module_id
                query = query.join(TeacherModuleAssociation).filter(TeacherModuleAssociation.module_id == module_id)

            current_app.logger.debug(f"Teacher list filters applied: {filters_applied}")
            query = query.order_by(Teacher.last_name, Teacher.first_name)
            paginated_teachers = query.paginate(page=page, per_page=per_page, error_out=False)

            teachers_raw = paginated_teachers.items
            teachers_data = dump_data(teachers_raw, many=True)

            # Removed specialization_name enrichment logic

            resp = message(True, "Teachers list retrieved successfully.")
            resp.update({
                "teachers": teachers_data, "total": paginated_teachers.total, "pages": paginated_teachers.pages,
                "current_page": paginated_teachers.page, "per_page": paginated_teachers.per_page,
                "has_next": paginated_teachers.has_next, "has_prev": paginated_teachers.has_prev
            })
            return resp, 200
        except Exception as e:
            current_app.logger.error(f"Error getting all teachers: {e}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def create_teacher(data: dict):
        try:
            existing_teacher = Teacher.query.filter_by(email=data.get("email")).first()
            if existing_teacher:
                status = "archived" if existing_teacher.archived else "active"
                return err_resp(f"Email '{data.get('email')}' already used by an {status} teacher.", "duplicate_email", 409)

            # fk_errors = TeacherService._validate_foreign_keys(data) # No FKs to validate now
            # if fk_errors: return validation_error(False, fk_errors), 400

            new_teacher = load_data(data)
            new_teacher.archived = False
            new_teacher.password = generate_password_hash(data["password"])

            db.session.add(new_teacher)
            db.session.commit()
            teacher_data = dump_data(new_teacher)
            return {"status": True, "message": "Teacher created successfully.", "teacher": teacher_data}, 201
        except ValidationError as err:
            db.session.rollback(); return validation_error(False, err.messages), 400
        except IntegrityError:
            db.session.rollback(); return internal_err_resp()
        except Exception as e:
            db.session.rollback(); current_app.logger.error(f"Error creating teacher: {e}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def update_teacher_by_admin(teacher_id: int, data: dict):
        teacher = Teacher.query.filter_by(id=teacher_id, archived=False).first()
        if not teacher: return err_resp("Teacher not found or is archived.", "teacher_not_active_update", 404)
        if not data: return err_resp("Request body cannot be empty.", "empty_update_data", 400)

        data.pop("archived", None)
        data.pop("email", None)
        data.pop("password", None)
        # data.pop("specialization_id", None) # No longer needed

        # fk_errors = TeacherService._validate_foreign_keys(data, instance=teacher) # No FKs to validate now
        # if fk_errors: return validation_error(False, fk_errors), 400

        try:
            updated_teacher = load_data(data, partial=True, instance=teacher)
            db.session.commit()
            return {"status": True, "message": "Teacher updated successfully.", "teacher": dump_data(updated_teacher)}, 200
        except ValidationError as err:
            db.session.rollback(); return validation_error(False, err.messages), 400
        except Exception as e:
            db.session.rollback(); current_app.logger.error(f"Error updating teacher (admin) {teacher_id}: {e}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def update_own_profile(current_user_id: int, data: dict):
        teacher = Teacher.query.filter_by(id=current_user_id, archived=False).first()
        if not teacher: return err_resp("Teacher profile not found or is archived.", "teacher_profile_not_active", 403)
        if not data: return err_resp("Request body cannot be empty.", "empty_update_data", 400)

        data.pop("archived", None)
        data.pop("email", None)
        data.pop("password", None)
        # data.pop("specialization_id", None) # No longer needed

        try:
            updated_teacher = load_data(data, partial=True, instance=teacher)
            db.session.commit()
            return {"status": True, "message": "Profile updated successfully.", "teacher": dump_data(updated_teacher)}, 200
        except ValidationError as err:
            db.session.rollback(); return validation_error(False, err.messages), 400
        except Exception as e:
            db.session.rollback(); current_app.logger.error(f"Error teacher self-update {current_user_id}: {e}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def archive_teacher(teacher_id: int):
        teacher = Teacher.query.get(teacher_id)
        if not teacher: return err_resp("Teacher not found!", "teacher_404", 404)
        if teacher.archived:
            return {"status": True, "message": "Teacher is already archived.", "teacher": dump_data(teacher)}, 200

        try:
            teacher.archived = True
            # Consider implications: unassign from active sessions or modules?
            # For now, just marking as archived.
            # If TeacherModuleAssociation has a cascade on teacher delete, it might be an issue if you were hard deleting.
            # For soft delete, these associations would remain unless explicitly handled.
            db.session.commit()
            current_app.logger.info(f"Teacher archived: ID {teacher_id}")
            return {"status": True, "message": "Teacher archived successfully.", "teacher": dump_data(teacher)}, 200
        except Exception as e:
            db.session.rollback(); current_app.logger.error(f"Error archiving teacher {teacher_id}: {e}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def unarchive_teacher(teacher_id: int):
        teacher = Teacher.query.get(teacher_id)
        if not teacher: return err_resp("Teacher not found!", "teacher_404", 404)
        if not teacher.archived:
            return {"status": True, "message": "Teacher is already active.", "teacher": dump_data(teacher)}, 200

        try:
            existing_active_teacher = Teacher.query.filter(
                Teacher.email == teacher.email,
                Teacher.archived == False,
                Teacher.id != teacher_id
            ).first()
            if existing_active_teacher:
                return err_resp(f"Cannot unarchive. Email '{teacher.email}' is in use by another active teacher.", "email_conflict_unarchive_teacher", 409)

            teacher.archived = False
            db.session.commit()
            current_app.logger.info(f"Teacher unarchived: ID {teacher_id}")
            return {"status": True, "message": "Teacher unarchived successfully.", "teacher": dump_data(teacher)}, 200
        except Exception as e:
            db.session.rollback(); current_app.logger.error(f"Error unarchiving teacher {teacher_id}: {e}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def assign_module(teacher_id: int, module_id: int):
        teacher = Teacher.query.filter_by(id=teacher_id, archived=False).first() # Assign only to active teachers
        if not teacher: return err_resp("Teacher not found or is archived.", "teacher_not_active_assign", 404)

        module = Module.query.get(module_id)
        if not module: return err_resp("Module not found!", "module_404_assign", 404)

        existing_association = TeacherModuleAssociation.query.filter_by(teacher_id=teacher_id, module_id=module_id).first()
        if existing_association:
            return err_resp("Module already assigned to this teacher.", "duplicate_assignment", 409)

        try:
            association = TeacherModuleAssociationSchema().load({
                "teacher_id": teacher_id,
                "module_id": module_id
            })
            db.session.add(association)
            db.session.commit()
            return message(True, "Module assigned to teacher successfully."), 201
        except Exception as e:
            db.session.rollback(); current_app.logger.error(f"Error assigning module {module_id} to teacher {teacher_id}: {e}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def remove_module(teacher_id: int, module_id: int):
        teacher = Teacher.query.get(teacher_id) # Allow removal even if teacher is archived (cleanup)
        if not teacher: return err_resp("Teacher not found!", "teacher_404_remove_module", 404)

        association = TeacherModuleAssociation.query.filter_by(teacher_id=teacher_id, module_id=module_id).first()
        if not association:
            return err_resp("Module is not assigned to this teacher.", "assignment_not_found_remove", 404)

        try:
            db.session.delete(association)
            db.session.commit()
            return None, 204
        except Exception as e:
            db.session.rollback(); current_app.logger.error(f"Error removing module {module_id} from teacher {teacher_id}: {e}", exc_info=True)
            return internal_err_resp()
