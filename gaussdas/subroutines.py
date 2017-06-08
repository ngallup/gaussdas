import pandas

class Subroutines(object):
    def __init__(self):
        self._keys = {}
        self._keys['Zero-point correction'] = thermo_chem
        
    def find_token_indices(self, line):
        #for char in line:
        #    pass
        pass

    def brute_search(self, infile, line, df):
        '''
        This is a fairly rudimentary algorithm just to get gaussdas up and
        running.  It is extremely inefficient at finding the keywords and
        the subsequent parsing schemes and needs to be replaced with an
        efficient algorithm for multiple keyword matching.  There are
        efficient schemes that exist for this but are fairly sophisticated.
        '''
        for keyword in self._keys:
            if keyword in line:
                infile, df = self._exec_parse(keyword, line, infile, df)
        
        return infile, df 

    def _exec_parse(self, key, line, infile, df):
        '''
        For executing a function that maps to a keyword and appending the
        resulting data to the dataframe before handing back the dataframe
        and file stream -- or performing some other function
        '''
        func_call = self._keys[key]
        infile, new_df = func_call(infile, line, df)

        # Check if function is void type or making changes to the DataFrame
        if new_df != None:
            df = new_df

        return infile, df
            
def thermo_chem(filestream, line, df):
    '''
    Gather all thermochemistry data in the event of successful freq
    '''
    print(line)
    print("I'm the thermo_chem function")
    pass
