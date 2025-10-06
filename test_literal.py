from satya import Model, Field
from typing import Literal

class Test(Model):
    x: Literal['a', 'b']

t = Test(x='a')
print('Success:', t.x)
