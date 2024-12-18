from marshmallow import Schema, fields


    
class User(Schema):
    email = fields.Email()
    name = fields.String()
    def __repr__(self):
        return f'<userData {self.email}>'
