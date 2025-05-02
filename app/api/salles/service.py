# Added current_app
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from marshmallow import ValidationError

# Import DB instance and models
from app import db
from app.models import Salle

# Import shared utilities
from app.utils import (
    err_resp,
    message,
    internal_err_resp,
    validation_error,
)

# Import serialization/deserialization utilities from local utils.py
from .utils import dump_data, load_data


class SalleService:

    # --- GET Single ---
    @staticmethod
    def get_salle_data(salle_id, current_user_id, current_user_role):
        """Get salle data by ID"""
        salle = Salle.query.get(salle_id)

        if not salle:
            return err_resp("Salle not found!", "salle_404", 404)

        try:
            salle_data = dump_data(salle)
            resp = message(True, "Salle data sent successfully")
            resp["salle"] = salle_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(
                f"Error getting salle data for ID {salle_id}: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- GET List with Filters ---
    @staticmethod
    def get_all_salles(
        name=None,
        min_capacity=None,
        max_capacity=None,
        page=None,
        per_page=None,
        current_user_id=None,
        current_user_role=None,
    ):
        """Get a list of salles, filtered and paginated"""
        page = page or 1
        per_page = per_page or 10

        try:
            query = Salle.query

            # Apply filters
            if name:
                query = query.filter(Salle.name.ilike(f"%{name}%"))
            if min_capacity:
                query = query.filter(Salle.capacity >= min_capacity)
            if max_capacity:
                query = query.filter(Salle.capacity <= max_capacity)

            # Add ordering
            query = query.order_by(Salle.name.asc())

            # Implement pagination
            paginated_salles = query.paginate(
                page=page, per_page=per_page, error_out=False
            )

            # Serialize results using dump_data
            salles_data = dump_data(paginated_salles.items, many=True)

            resp = message(True, "Salles list retrieved successfully")
            resp["salles"] = salles_data
            resp["total"] = paginated_salles.total
            resp["pages"] = paginated_salles.pages
            resp["current_page"] = paginated_salles.page
            resp["per_page"] = paginated_salles.per_page
            resp["has_next"] = paginated_salles.has_next
            resp["has_prev"] = paginated_salles.has_prev

            return resp, 200

        except Exception as error:
            current_app.logger.error(
                f"Error getting all salles with filters: {error}",
                exc_info=True,
            )
            return internal_err_resp()

    # --- CREATE ---
    @staticmethod
    def create_salle(data, current_user_id, current_user_role):
        """Create a new salle"""
        try:
            # Check for unique name
            if Salle.query.filter_by(name=data["name"]).first():
                return err_resp(
                    f"Salle with name '{data['name']}' already exists.",
                    "salle_duplicate",
                    409,
                )

            # Create instance

            new_salle = load_data(data)
            db.session.add(new_salle)
            db.session.commit()

            salle_data = dump_data(new_salle)
            resp = message(True, "Salle created successfully.")
            resp["salle"] = salle_data
            return resp, 201

        except ValidationError as err:
            current_app.logger.warning(
                f"Validation error creating salle: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except IntegrityError as error:
            db.session.rollback()
            current_app.logger.warning(
                f"Integrity error creating salle: {error}", exc_info=True
            )
            return internal_err_resp()
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating salle: {error}", exc_info=True
            )
            return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating salle: {error}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE ---
    @staticmethod
    def update_salle(salle_id, data, current_user_id, current_user_role):
        """Update an existing salle"""
        salle = Salle.query.get(salle_id)
        if not salle:
            return err_resp("Salle not found!", "salle_404", 404)

        try:
            # Update fields
            if "name" in data:
                salle.name = data["name"]
            if "capacity" in data:
                salle.capacity = data["capacity"]
            if "location" in data:
                salle.location = data["location"]

            db.session.commit()

            salle_data = dump_data(salle)
            resp = message(True, "Salle updated successfully.")
            resp["salle"] = salle_data
            return resp, 200

        except ValidationError as err:
            db.session.rollback()
            current_app.logger.warning(
                f"Validation error updating salle: {err.messages}"
            )
            return validation_error(False, err.messages), 400
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error updating salle: {error}", exc_info=True)
            return internal_err_resp()

    # --- DELETE ---
    @staticmethod
    def delete_salle(salle_id, current_user_id, current_user_role):
        """Delete a salle"""
        salle = Salle.query.get(salle_id)
        if not salle:
            return err_resp("Salle not found!", "salle_404", 404)

        try:
            db.session.delete(salle)
            db.session.commit()
            return None, 204  # No Content

        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.error(
                f"Database error deleting salle: {error}", exc_info=True
            )
            return err_resp(
                "Could not delete salle due to a database constraint or error.",
                "delete_error_db",
                500,
            )
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error deleting salle: {error}", exc_info=True)
            return internal_err_resp()
