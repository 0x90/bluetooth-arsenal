'NE47'

##Building 2
from PIL import Image
import StringIO
from building_map import *
import pickle

floor4=Floor('Floor 4', (1030, 396), [], 'NE47_4.jpg')
floor5=Floor('Floor 5', (1030, 306), [], 'NE47_5.jpg')

NE47=Building([floor4, floor5])

pickle.dump(NE47, open('NE47.p', 'wb'))
