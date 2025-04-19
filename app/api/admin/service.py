from flask import current_app

from app.utils import err_resp, message, internal_err_resp
from app.models.Admin import Admin


class AdminService:
    """ Admin service class """
    @staticmethod
    def get_user_data(email):
        """ Get user data by username """
        if not (admin := Admin.query.filter_by(email=email).first()):
            return err_resp("User not found!", "user_404", 404)

        from .utils import load_data

        try:
            admin_data = load_data(admin)

            resp = message(True, "User data sent")
            resp["admin"] = admin_data
            return resp, 200

        except Exception as error:
            current_app.logger.error(error)
            return internal_err_resp()
