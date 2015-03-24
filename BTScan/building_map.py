from PIL import Image
import StringIO

class Building(object):
    """This is a class that defines the building information that will be called by the tracking interface.  It contains a list of instances of the Floor class (defined below)."""

    def __init__(self,floors):

        self.floors = floors  #list of instances of object Floors
        self.floor_receivers = {i.name : None for i in self.floors}  #A dictionary to hold a complete list of all receivers within a building.  Will be built from data in self.floors

        self.update_receiver_list()

    def update_receiver_list(self):
        """Method that populates self.floor_receivers with the receivers known to each instance of Floor"""
        for i in self.floors:
            self.floor_receivers[i.name] = i.receivers


class Floor(object):
    """This is a class used to define a floor and its elements within a building."""
    
    def __init__(self,name,size,receivers,file_name):
        
        self.name = name  #name of the floor
        self.size = size #physical dimensions of the map. tuple(x,y) in meters
        self.receivers = receivers #list of receivers on a floor. receivers[i] = tuple(mac_addr,abs_pos).   abs_pos = tuple(x,y) in meters
        self.file_name = file_name #this is the filename of the image to be identified with a floor
        self.raw_image = None #holder for the raw image data
        
        self.store_image(self.file_name)
            
        
    def store_image(self,image_file):
        """This method takes image_file as a file name, and handles opening the image, converting to string format and storing it within the instance of Floors.  It is called by __init__, but can also be called later to replace the map file within the instance"""
        
        pilimage = Image.open(image_file) #open file as a PIL image
        output = StringIO.StringIO() #create memory location to hold image
        pilimage.save(output,pilimage.format) #saves image into memory 
        self.raw_image = output.getvalue() #saves image data as string
        output.close()

    def load_image(self,raw_image_file):
        """This method takes the raw_image_file created by store_image and handles loading the image string into a PIL image and then returns it."""

        image_buffer = StringIO.StringIO(raw_image_file) #create memory location with image data 
        image = Image.open(image_buffer) #opens the stored image
        
        return image
        
        

        
        
        
