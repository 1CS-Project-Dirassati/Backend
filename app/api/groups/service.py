from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import ValidationError # Import Marshmallow's validation error

# Import your DB instance and Group model
from app import db
from app.models import Group
# Import shared utilities and the schema
from app.models.Schemas import GroupSchema # Assuming GroupSchema is here
from app.utils import err_resp, message, internal_err_resp # Assuming you have a validation_error helper

# Initialize the schema once for the service class
# Use `partial=True` on load for updates to allow partial data
group_schema = GroupSchema()
group_update_schema = GroupSchema(partial=True) # Schema instance for partial updates

# Assuming load_data uses group_schema.dump() internally
from .utils import load_data

class GroupService:
    @staticmethod
    def get_group_data(group_id):
        """ Get group data by its ID """
        group = Group.query.get(group_id)
        if not group:
            return err_resp("Group not found!", "group_404", 404)
        try:
            group_data = load_data(group) # Uses schema.dump() via load_data
            resp = message(True, "Group data sent successfully")
            resp["group"] = group_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(f"Error getting group data for ID {group_id}: {error}", exc_info=True)
            return internal_err_resp()

    @staticmethod
    def get_all_groups():
        """ Get a list of all groups """
        try:
            groups = Group.query.order_by(Group.name).all()
            groups_data = load_data(groups, many=True) # Uses schema.dump(many=True) via load_data
            resp = message(True, "Groups list retrieved successfully")
            resp["groups"] = groups_data
            return resp, 200
        except Exception as error:
            current_app.logger.error(f"Error getting all groups: {error}", exc_info=True)
            return internal_err_resp()

    # --- CREATE (Using schema.load for validation) ---
    @staticmethod
    def create_group(data):
        """ Create a new group after validating input data """
        try:
            # Validate the input data using the Marshmallow schema
            # load() raises ValidationError if validation fails
            validated_data = group_schema.load(data)

            # Optional: Add checks not covered by schema (e.g., foreign key existence)
            # from app.models.level import Level
            # if not Level.query.get(validated_data['level_id']):
            #     return err_resp("Level not found!", "level_404", 400)

            # Create the Group instance using validated data
            new_group = Group(**validated_data) # Use validated data

            db.session.add(new_group)
            db.session.commit()

            # Serialize the newly created object for the response
            group_data = load_data(new_group) # Uses schema.dump()
            resp = message(True, "Group created successfully")
            resp["group"] = group_data
            return resp, 201 # 201 Created

        except ValidationError as err:
            # Handle Marshmallow validation errors
            current_app.logger.warning(f"Validation error creating group: {err.messages}")
            # Use your validation_error helper if you have one, otherwise use err_resp
            # return validation_error(False, err.messages), 400
            return err_resp(f"Validation failed: {err.messages}", "validation_error", 400)

        except SQLAlchemyError as error:
             db.session.rollback()
             current_app.logger.error(f"Database error creating group: {error}", exc_info=True)
             return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error creating group: {error}", exc_info=True)
            return internal_err_resp()

    # --- UPDATE (Using schema.load(partial=True) for validation) ---
    @staticmethod
    def update_group(group_id, data):
        """ Update an existing group by ID after validating input data """
        group = Group.query.get(group_id)
        if not group:
            return err_resp("Group not found!", "group_404", 404)

        try:
            # Validate the incoming partial data using the partial schema instance
            # load() raises ValidationError if validation fails
            # Pass existing model instance to load into via `instance=` if schema is configured for it
            # validated_data = group_update_schema.load(data, instance=group, partial=True) # Option 1: Load into instance
            validated_data = group_update_schema.load(data) # Option 2: Get validated dict

            # --- Update the model fields using the validated data ---
            # Option 1 (if loaded into instance): The 'group' object might already be updated by load()
            # Option 2 (if load returned a dict): Update manually
            for key, value in validated_data.items():
                 setattr(group, key, value)

            # Optional: Add checks not covered by schema (e.g., foreign key existence)
            # if 'level_id' in validated_data:
            #    from app.models.level import Level
            #    if not Level.query.get(validated_data['level_id']):
            #        return err_resp("New Level not found!", "level_404", 400)

            db.session.add(group) # Add potentially modified group to session
            db.session.commit()

            # Serialize the updated object for the response
            group_data = load_data(group) # Uses schema.dump()
            resp = message(True, "Group updated successfully")
            resp["group"] = group_data
            return resp, 200 # 200 OK

        except ValidationError as err:
            # Handle Marshmallow validation errors
            db.session.rollback() # Rollback any potential changes made by load(instance=...)
            current_app.logger.warning(f"Validation error updating group {group_id}: {err.messages}")
            # return validation_error(False, err.messages), 400
            return err_resp(f"Validation failed: {err.messages}", "validation_error", 400)

        except SQLAlchemyError as error:
             db.session.rollback()
             current_app.logger.error(f"Database error updating group {group_id}: {error}", exc_info=True)
             return internal_err_resp()
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error updating group {group_id}: {error}", exc_info=True)
            return internal_err_resp()

    # --- DELETE (No input validation needed typically) ---
    @staticmethod
    def delete_group(group_id):
        """ Delete a group by ID """
        group = Group.query.get(group_id)
        if not group:
            return err_resp("Group not found!", "group_404", 404)

        try:
            # Optional: Add checks before deletion (e.g., prevent deleting if related records exist)
            # if group.students:
            #    return err_resp("Cannot delete group with assigned students.", "delete_conflict", 409)

            db.session.delete(group)
            db.session.commit()
            return None, 204 # 204 No Content

        except SQLAlchemyError as error:
             db.session.rollback()
             current_app.logger.error(f"Database error deleting group {group_id}: {error}", exc_info=True)
             return err_resp(f"Could not delete group due to a database constraint or error.", "delete_error_db", 500)
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(f"Error deleting group {group_id}: {error}", exc_info=True)
            return internal_err_resp()
