# Backendv2
backendv2 for dirassati
# Features

* Full featured framework for fast, easy, and documented API with [Flask-RESTX](https://flask-restx.readthedocs.io/en/latest/)
* JSON Web Token Authentication with [Flask-JWT-Extended](https://flask-jwt-extended.readthedocs.io/en/stable/)
* Swagger Documentation (Part of Flask-RESTX).
* Unit Testing.
* Database ORM with [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/en/2.x/)
* Database Migrations using [Flask-Migrate](https://github.com/miguelgrinberg/flask-migrate)
* Object serialization/deserialization with [Flask-Marshmallow](https://flask-marshmallow.readthedocs.io/en/latest/)
* Data validations with Marshmallow [Marshmallow](https://marshmallow.readthedocs.io/en/stable/quickstart.html#validation)


## Usage
poetry is used to manage the dependencies of the project. To install the dependencies, run the following command:
```bash
poetry install
eval "$(poetry env activate)"
# and run it using
flask run --debug
```
auth Documentation is available at /
and the api documentation is available at /api
dont forget to set the .env file with the following variables:
```bash
export FLASK_APP=dirassati
export FLASK_ENV=development
#to create the database run the following command
flask db init
flask db migrate
flask db upgrade
```
# to run the tests
```bash
flask test
```

to run unit tests
```bash
flask test tests.test_auth_api tests.test_user_model ...
```

