import pandas
import numpy as np
import sys

class Subroutines(object):
    def __init__(self):
        # A more modular scheme would be nice in the future.  Maybe loading
        # in all classes/functions from a seperate file upon instantiation
        self._keys = {}
        self._keys['Zero-point correction'] = thermo_chem
        self._keys['Charge = '] = atoms_charge_mult
        
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
        if not isinstance(df, pandas.DataFrame):
            new_df = pandas.DataFrame()

        df = new_df

        return infile, df
    
def add_pandas_fields(df, data, overwrite=True):
    '''
    Add fields and data to the DataFrame.  And overwrite=false method has
    not been writen yet
    '''
    if isinstance(data, dict):
        for field in data: df[field] = pandas.Series(data[field])
        return df
    elif isinstance(data[0], list):
        for field in data: df[field[0]] = pandas.Series(field[1])
        return df
    
    df[data[0]] = pandas.Series(data[1])
    return df

def add_pandas_series(df, data, overwrite=True):
    '''
    Add some kind of series data to the DataFrame.
    '''
    tmp_df = pandas.DataFrame(data)
    print('------ADD PANDAS SERIES') #DELETE
    print(df)

    for col in tmp_df.columns:
        series_df = pandas.DataFrame(tmp_df[col])
        if col in df.columns:
            # This will need more testing
            if overwrite == False:
                print("DON'T OVERWRITE ME!!!!") #delete
                continue
            df[col] = series_df
        else:
            df = pandas.concat([df, series_df], axis=1)
        
    return df

def thermo_chem(filestream, line, df):
    '''
    Gather all thermochemistry data in the event of successful freq
    '''
    fields = []
    fields.append(['zpe_corr', None])
    fields.append(['e_corr', None])
    fields.append(['h_corr', None])
    fields.append(['g_corr', None])
    fields.append(['E', None])
    fields.append(['H', None])
    fields.append(['G', None])

    # The next 7 lines contain all the other thermo data
    lines = [line]
    for i in range(7):
        lines.append(filestream.next())
    for field, line in zip(fields, lines):
        if 'Zero-point' in line: # ZPE line needs special handling
            field[1] = np.float64(line.split()[-2])
        else: 
            field[1] = np.float64(line.split()[-1])

    df = add_pandas_fields(df, fields)
    
    return filestream, df

def atoms_charge_mult(filestream, line, df):
    '''
    Get initial atom data, charge, and multiplicity for the system
    '''
    print('----------ATOMS CHARGE MULT IS CALLED')  #delete
    #print('LINE: ', line) #DELETE
    fields = {}
    fields['natoms'] = None
    fields['charge'] = None
    fields['multiplicity'] = None
    
    series = {}
    series['atom list'] = []
    series['frozen'] = []

    # Initial line will have charge and mult data
    elems = line.split()
    charge = elems[2]
    mult = elems[5]
    fields['charge'] = np.int(charge)
    fields['multiplicity'] = np.int(mult)

    # Scan for atom data, terminating at blank line or at instance of non atom
    line = filestream.next()
    if 'Redundant' in line: line = filestream.next() #When redundant coords
    line_split = line.split()
    while line_split != [] and len(line_split[0]) < 3: #Check if atom or empty
        series['atom list'].append(line_split[0])
        series['frozen'].append(line_split[1])
        line = filestream.next()
        line_split = line.split()

    fields['natoms'] = len(series['atom list'])

    df = add_pandas_fields(df, fields)
    df = add_pandas_series(df, series, overwrite=False)

    return filestream, df
