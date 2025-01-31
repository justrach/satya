from typing import Optional
from satya import Model, Field, List

# Enable pretty printing for this module
Model.PRETTY_REPR = True

class User(Model):
    id: int
    name: str = Field(default='John Doe')
    signup_ts: Optional[str] = Field(required=False)  # Using str for datetime
    friends: List[int] = Field(default=[])

external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
validator = User.validator()
result = validator.validate(external_data)
user = User(**result.value)
print(user)
#> User(id=123, name='John Doe', signup_ts='2017-06-01 12:22', friends=[1, 2, 3])
print(user.id)
#> 123