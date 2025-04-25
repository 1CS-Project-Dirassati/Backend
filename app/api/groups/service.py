from flask import current_app

# Import the specific Group model
from models import Group

# Import shared utilities
from app.utils import err_resp, message, internal_err_resp

# Import the group-specific utility for loading data
from .utils import load_data  # Assumes load_data uses GroupSchema matching the model


class GroupService:
    @staticmethod
    def get_group_data(group_id):
        """Get group data by its ID"""
        # Use query.get() for primary key lookup
        group = Group.query.get(group_id)

        if not group:
            return err_resp("Group not found!", "group_404", 404)

        try:
            # Use the utility function to serialize the DB object
            group_data = load_data(group)

            resp = message(True, "Group data sent successfully")
            resp["group"] = group_data
            return resp, 200

        except Exception as error:
            # Log the detailed error
            current_app.logger.error(
                f"Error getting group data for ID {group_id}: {error}", exc_info=True
            )
            # Return a generic internal error response to the client
            return internal_err_resp()

    @staticmethod
    def get_all_groups():
        """Get a list of all groups"""
        # Basic query, add filtering/pagination later as needed
        # Consider adding ordering, e.g., groups = Group.query.order_by(Group.name).all()
        groups = Group.query.all()

        # It's better to return an empty list than a 404 if the collection is just empty
        # if not groups:
        #     resp = message(True, "No groups found.")
        #     resp["groups"] = []
        #     return resp, 200

        try:
            # Use the utility function with many=True
            groups_data = load_data(groups, many=True)

            resp = message(True, "Groups list retrieved successfully")
            resp["groups"] = groups_data
            return resp, 200

        except Exception as error:
            current_app.logger.error(
                f"Error getting all groups: {error}", exc_info=True
            )
            return internal_err_resp()

    # --- Add methods for create_group, update_group, delete_group later ---
    # These would interact with db.session (add, commit, delete)
    # Example placeholder:
    # @staticmethod
    # def create_group(data):
    #     try:
    #         new_group = Group(name=data['name'], level_id=data['level_id'])
    #         db.session.add(new_group)
    #         db.session.commit()
    #         group_data = load_data(new_group)
    #         resp = message(True, "Group created successfully")
    #         resp["group"] = group_data
    #         return resp, 201 # 201 Created status
    #     except Exception as error:
    #         db.session.rollback()
    #         current_app.logger.error(f"Error creating group: {error}", exc_info=True)
    #         return internal_err_resp()
