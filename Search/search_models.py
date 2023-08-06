from flask_sqlalchemy import SQLAlchemy  # pylint: disable=import-error

db = SQLAlchemy()


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.String(200))

    def __repr__(self):
        return f"<Item {self.id}: {self.name}>"
