import subroutines
import os.path
import pandas
from subroutines import Subroutines


class Processor(object):
    '''
    The Processor class will act as the only class the user should interact
    with for parsing Gaussian files.  The user should pass the path of a
    Gaussian output to the Processor, and get back a pandas dataframe
    of all relevent chemical data
    '''

    def __init__(self):
        self.indices = []

    def get_df(self, file_path):
        df = None
        path = os.path.abspath(file_path)

        routines = Subroutines

        self.indices = get_indices(path)
        print(self.indices) #DELETE
        
        return df
                
    def _get_indices(self, path):
        '''
        There are probably some ways to optimize this to prevent reading the
        file twice, but this should work for now
        '''
        indices = []
        with open(path) as infile:
            for i, line in enumerate(infile):
                char_inds, func_call = routines.find_token_indices(line)
                for cind in char_inds:
                    cind = [i, cind]

                for each in char_inds:
                    indices.append(each)

        return indices
