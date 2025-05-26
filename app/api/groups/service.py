from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import ValidationError
from sqlalchemy.orm import joinedload

from app import db
# Ensure all necessary models are imported
from app.models import Group, Level, Session, Teacher, Module, Parent, Student

from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)
from .utils import dump_data, load_data


class GroupService:
    @staticmethod
    def get_group_data(group_id: int, current_user_id: int, current_user_role: str):
        group = Group.query.options(joinedload(Group.level)).get(group_id)
        if not group:
            current_app.logger.info(f"Group with ID {group_id} not found.")
            return err_resp("Group not found!", "group_404", 404)

        can_access = False
        if current_user_role == "admin":
            can_access = True
        elif current_user_role == "teacher":
            if Session.query.filter_by(teacher_id=current_user_id, group_id=group_id).first():
                can_access = True
        elif current_user_role == "student":
            student = Student.query.filter_by(user_id=current_user_id).first()
            if student and student.group_id == group_id and not student.archived:
                can_access = True
        elif current_user_role == "parent":
            parent = Parent.query.get(current_user_id)
            if parent:
                for student_child in parent.students:
                    if student_child.group_id == group_id and not student_child.archived:
                        can_access = True
                        break

        if not can_access:
            current_app.logger.warning(f"User {current_user_id} ({current_user_role}) forbidden to access group {group_id}")
            return err_resp("Forbidden: You do not have permission to access this group.", "group_access_denied", 403)

        try:
            group_data = dump_data(group)
            if group.level:
                group_data["level_name"] = group.level.name
            resp = message(True, "Group data sent successfully")
            resp["group"] = group_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(f"Error serializing group data for ID {group_id}: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def get_all_groups(
        level_id=None, teacher_id=None, module_id=None,
        page=None, per_page=None,
        current_user_id=None, current_user_role=None
    ):
        page = page or 1
        per_page = per_page or 10

        try:
            # Start with Group query and eagerly load level
            query = Group.query.options(joinedload(Group.level))

            # Apply join with Session only if teacher_id or module_id is provided
            if teacher_id is not None or module_id is not None:
                # Join with Session using the relationship (assumes Group.sessions relationship exists)
                query = query.join(Group.sessions)

            # Apply teacher_id filter
            if teacher_id is not None:
                if current_user_role == "admin" and not Teacher.query.get(teacher_id):
                    return err_resp(f"Teacher with ID {teacher_id} not found for filtering.", "teacher_filter_404", 404)
                current_app.logger.debug(f"Filtering groups by teacher_id: {teacher_id}")
                query = query.filter(Session.teacher_id == teacher_id)

            # Apply module_id filter
            if module_id is not None:
                if not Module.query.get(module_id):
                    return err_resp(f"Module with ID {module_id} not found for filtering.", "module_filter_404", 404)
                current_app.logger.debug(f"Filtering groups by module_id: {module_id}")
                query = query.filter(Session.module_id == module_id)

            # Apply level_id filter
            if level_id is not None:
                current_app.logger.debug(f"Filtering groups by level_id: {level_id}")
                if not Level.query.get(level_id):
                    return err_resp("Level specified in filter not found", "level_filter_404", 404)
                query = query.filter(Group.level_id == level_id)

            # Apply distinct to avoid duplicate groups when joining with Session
            if teacher_id is not None or module_id is not None:
                query = query.distinct()

            # Order and paginate
            query = query.order_by(Group.name)
            paginated_groups = query.paginate(page=page, per_page=per_page, error_out=False)

            groups_list_data = []
            for group_obj in paginated_groups.items:
                group_item_data = dump_data(group_obj)
                if group_obj.level:
                    group_item_data["level_name"] = group_obj.level.name
                groups_list_data.append(group_item_data)

            resp = message(True, "Groups list retrieved successfully")
            resp["groups"] = groups_list_data
            resp["total"] = paginated_groups.total
            resp["pages"] = paginated_groups.pages
            resp["current_page"] = paginated_groups.page
            resp["per_page"] = paginated_groups.per_page
            resp["has_next"] = paginated_groups.has_next
            resp["has_prev"] = paginated_groups.has_prev

            return resp, 200
        except SQLAlchemyError as error:
            log_msg = f"Database error getting groups"
            if level_id is not None:
                log_msg += f" with level_id {level_id}"
            if teacher_id is not None:
                log_msg += f" for teacher {teacher_id}"
            if module_id is not None:
                log_msg += f" for module {module_id}"
            if page is not None:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()
        except Exception as error:
            log_msg = f"Unexpected error getting groups"
            if level_id is not None:
                log_msg += f" with level_id {level_id}"
            if teacher_id is not None:
                log_msg += f" for teacher {teacher_id}"
            if module_id is not None:
                log_msg += f" for module {module_id}"
            if page is not None:
                log_msg += f", page {page}"
            current_app.logger.error(f"{log_msg}: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def create_group(data: dict):
        try:
            if not Level.query.get(data["level_id"]):
                return validation_error(False, {"level_id": ["Level ID does not exist."]})

            existing_group = Group.query.filter_by(name=data["name"], level_id=data["level_id"]).first()
            if existing_group:
                return err_resp(f"Group with name '{data['name']}' already exists in this level.", "duplicate_group_name_in_level", 409)

            new_group = load_data(data)
            db.session.add(new_group)
            db.session.commit()

            group_data_resp = dump_data(new_group)
            if new_group.level_id:
                level_obj = Level.query.get(new_group.level_id)
                if level_obj:
                    group_data_resp["level_name"] = level_obj.name

            resp = message(True, "Group created successfully")
            resp["group"] = group_data_resp
            return resp, 201
        except ValidationError as err:
            db.session.rollback()
            return validation_error(False, err.messages), 400
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error creating group: {e}", exc_info=True)
            return internal_err_resp(message=f"Database error: {e}")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error creating group: {e}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def update_group(group_id: int, data: dict):
        group = Group.query.options(joinedload(Group.level)).get(group_id)
        if not group:
            return err_resp("Group not found!", "group_404_update", 404)
        try:
            if "level_id" in data and data["level_id"] is not None:
                if not Level.query.get(data["level_id"]):
                    return validation_error(False, {"level_id": ["New Level ID does not exist."]})

            new_name = data.get("name")
            target_level_id = data.get("level_id", group.level_id)
            if new_name and new_name != group.name:
                existing_group = Group.query.filter(
                    Group.name == new_name, Group.level_id == target_level_id, Group.id != group_id
                ).first()
                if existing_group:
                    return err_resp(f"Group with name '{new_name}' already exists in the target level.", "duplicate_group_name_update", 409)

            updated_group = load_data(data, partial=True, instance=group)
            db.session.commit()

            group_data_resp = dump_data(updated_group)
            if updated_group.level_id:
                level_obj = Level.query.get(updated_group.level_id)
                if level_obj:
                    group_data_resp["level_name"] = level_obj.name

            resp = message(True, "Group updated successfully")
            resp["group"] = group_data_resp
            return resp, 200
        except ValidationError as err:
            db.session.rollback()
            return validation_error(False, err.messages), 400
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error updating group {group_id}: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def delete_group(group_id: int):
        group = Group.query.get(group_id)
        if not group:
            return err_resp("Group not found!", "group_404_delete", 404)
        try:
            if group.students.first() or group.sessions.first():
                return err_resp("Cannot delete group: It has associated students or sessions.", "delete_group_conflict_dependencies", 409)

            db.session.delete(group)
            db.session.commit()
            return None, 204
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error deleting group {group_id}: {e}", exc_info=True)
            return err_resp("Could not delete group due to a database error or existing dependencies.", "delete_group_db_error", 500)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error deleting group {group_id}: {e}", exc_info=True)
            return internal_err_resp()
