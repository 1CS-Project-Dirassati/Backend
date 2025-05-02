# Added current_app
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError

# Import DB instance and models
from app import db
from app.models import Module, Teacher

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data


class ModuleService:

    # --- GET Single ---
    @staticmethod
    def get_module_data(module_id, current_user_id, current_user_role):
        """Get module data by ID"""
        module = Module.query.get(module_id)

        if not module:
            return err_resp("Module not found!", "module_404", 404)

        try:
            module_data = dump_data(module)
            resp = message(True, "Module data sent successfully")
            resp["module"] = module_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting module data for ID {module_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters ---
    @staticmethod
    def get_all_modules(
        name=None,
        description=None,
        teacher_id=None,
        page=None,
        per_page=None,
        current_user_id=None,
        current_user_role=None,
    ):
        """Get a list of modules, filtered and paginated"""
        page = page or 1
        per_page = per_page or 10

        try:
            query = Module.query

            # Apply filters
            if name:
                query = query.filter(Module.name.ilike(f"%{name}%"))
            if description:
                query = query.filter(Module.description.ilike(f"%{description}%"))
            if teacher_id:
                query = query.filter(Module.teacher_id == teacher_id)

            # Add ordering
            query = query.order_by(Module.name.asc())

            # Implement pagination
            paginated_modules = query.paginate(
                page=page, per_page=per_page, error_out=False
            )

            # Serialize results using dump_data
            modules_data = dump_data(paginated_modules.items, many=True)

            resp = message(True, "Modules list retrieved successfully")
            resp["modules"] = modules_data
            resp["total"] = paginated_modules.total
            resp["pages"] = paginated_modules.pages
            resp["current_page"] = paginated_modules.page
            resp["per_page"] = paginated_modules.per_page
            resp["has_next"] = paginated_modules.has_next
            resp["has_prev"] = paginated_modules.has_prev

            return resp, 200

        except Exception as error:
            current_app.logger.error(
                f"Error getting all modules with filters: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- CREATE ---
    @staticmethod
    def create_module(data, current_user_id, current_user_role):
        """Create a new module"""
        try:
            # Check foreign key
            teacher = Teacher.query.get(data["teacher_id"])
            if not teacher:
                return err_resp(
                    f"Teacher with ID {data['teacher_id']} not found.",
                    "teacher_404",
                    404,
                )

            # Create instance
            new_module = load_data (data)

            db.session.add(new_module)
            db.session.commit()

            module_data = dump_data(new_module)
            resp = message(True, "Module created successfully.")
            resp["module"] = module_data
            return resp, 201

        except ValidationError as err:
            current_app.logger.warning(
                f"Validation error creating module: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error creating module: {error}", exc_info=True
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating module: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating module: {error}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE ---
    @staticmethod
    def update_module(module_id, data, current_user_id, current_user_role):
        """Update an existing module"""
        module = Module.query.get(module_id)
        if not module:
            return err_resp("Module not found!", "module_404", 404)

        try:
            # Update fields
            if "name" in data:
                module.name = data["name"]
            if "description" in data:
                module.description = data["description"]

            db.session.commit()

            module_data = dump_data(module)
            resp = message(True, "Module updated successfully.")
            resp["module"] = module_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating module: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error updating module: {error}", exc_info=True)
            return internal_err_resp()

    # --- DELETE ---
    @staticmethod
    def delete_module(module_id, current_user_id, current_user_role):
        """Delete a module"""
        module = Module.query.get(module_id)
        if not module:
            return err_resp("Module not found!", "module_404", 404)

        try:
            db.session.delete(module)
            db.session.commit()
            return None, 204  # No Content

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting module: {error}", exc_info=True
            )
            return err_resp(
                "Could not delete module due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error deleting module: {error}", exc_info=True)
            return internal_err_resp()
