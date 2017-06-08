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
        self.routines = Subroutines()

    def get_df(self, file_path, df=None):
        if df == None:
            df = pandas.DataFrame()

        path = os.path.abspath(file_path)

        #self.indices = self._get_indices(path)
        #print(self.indices) #DELETE
        df_copy = df.copy()
        new_df = self._search_and_parse(path, df_copy)
        
        return new_df 
                
    def _get_indices(self, path):
        '''
        For a scheme involving reading the file twice.  First pass to obtain
        the data token indices, or potential indices.  A followup pass would
        parse out the relevant data at those indices.
        '''
        indices = []
        with open(path) as infile:
            for i, line in enumerate(infile):
                print('LINE: ', line) #DELETE
                char_inds, func_call = self.routines.find_token_indices(line)
                for cind in char_inds:
                    cind = [i, cind, func_call]

                for each in char_inds:
                    indices.append(each)

        return indices  

    def _search_and_parse(self, path, df):
        '''
        Perform a linear scanning of the output file to determine if keywords
        exist within the current line.  If so, perform the appropriate
        subroutine, reading in the necessary amount text, and update the
        pandas dataframe and begin scanning from a later point in the file
        stream
        '''
        with open(path) as infile:
            for line in infile:
                #print(line, infile, self.routines.brute_search) #DELETE
                infile, df = self.routines.brute_search(infile, line, df)
        
        return df
