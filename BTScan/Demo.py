'Demo'

#Demo
from PIL import Image
import StringIO
from building_map import *
import pickle

testgrid=Floor('test-grid', (400,400), [], 'test-grid.gif')
conference=Floor('conference', (700,710), [], 'conf.jpg')

Demo=Building([testgrid, conference])

pickle.dump(Demo, open('Demo.p', 'wb'))
