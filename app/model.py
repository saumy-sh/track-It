from marshmallow import Schema, fields


    
class User(Schema):
    email = fields.Email()
    name = fields.String()
    def __repr__(self):
        return f'<userData {self.email}>'
    

class userSearch(Schema):
    email = fields.Email()
    source = fields.String()
    destinaton = fields.String()
    date = fields.Date()
    take_off = fields.String()
    landing_at = fields.String()
    flight_no = fields.String()
    price = fields.String()
