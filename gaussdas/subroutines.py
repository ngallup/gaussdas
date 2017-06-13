import pandas
import numpy as np
import sys

class Iteration(object):
    '''
    This is a class specifically designed to keep track of geometric and
    iteration no. data as the parsing of a file continues.  Should be useful
    in the future for assisting in the recording of timeseries geometric data.
    Also necessary for distinguishing between different style of SCF methods
    '''
    def __init__(self):
        self.natoms = None
        self.niter = 0
        self._nbo_bits = 0b00 # 00

    # Some bitwise getters and setters
    def get_nbo_bits(self):
        return self._nbo_bits
    def set_nbo_bits(self, new_bits):
        self._nbo_bits = new_bits
     
class Subroutines(object):
    def __init__(self):
        # A more modular scheme would be nice in the future.  Maybe loading
        # in all classes/functions from a seperate file upon instantiation
        self._keys = {}
        self._keys['Zero-point correction'] = self.thermo_chem
        self._keys['Charge = '] = self.atoms_charge_mult
        self._keys['N A T U R A L   A T O M I C   O R B I T A L   A N D'] = \
            self.found_nbo_header
        self._keys['Atom  No    Charge         Core'] = self.npa
        
        self._iteration = Iteration()
        
    def find_token_indices(self, line):
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
        infile, df = func_call(infile, line, df)
        
        if not isinstance(df, pandas.DataFrame):
            raise TypeError("Whoa buddy!  You lost the DataFrame!  Make sure" +
                            " your function calls return the DataFrame if " + 
                            "you don't use it.")

        return infile, df
   
    def thermo_chem(self, filestream, line, df):
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
    
    def atoms_charge_mult(self, filestream, line, df):
        '''
        Get initial atom data, charge, and multiplicity for the system
        '''
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
    
        # Scan for atom data, term. at blank line or at instance of non atom
        # Need to handle both explicit atom info, and internal redundant
        line = filestream.next()
        if 'Redundant' in line: line = filestream.next() #When redundant coords
        delimiter = None
        if ',' in line: delimiter = ','
        line_split = line.lstrip().rstrip().split(delimiter)
        while line_split != [] and len(line_split[0]) < 3: #Check if atom or empty
            series['atom list'].append(line_split[0])
            series['frozen'].append(line_split[1])
            line = filestream.next()
            line_split = line.lstrip().rstrip().split(delimiter)
    
        fields['natoms'] = len(series['atom list'])

        self._iteration.natoms = fields['natoms']
    
        df = add_pandas_fields(df, fields)
        df = add_pandas_series(df, series, overwrite=False)
    
        return filestream, df

    def found_nbo_header(self, filestream, line, df):
        '''
        For triggering some bit logic contained in the Iteration class so that
        NPA charges can be correctly parsed
        '''
        old_bits = self._iteration.get_nbo_bits()
        new_bits = 0b10
        self._iteration.set_nbo_bits(new_bits)

        print(old_bits) #DELETE
        print(new_bits) #DELETE

        return filestream, df
    
    def npa(self, filestream, line, df):
        '''
        For parsing out NPA charges from the file.  Relies on some bitwise
        logic to correctly grab the sum NPA charges, and not the alpha or beta
        specific charges.
        '''
        old_bits = self._iteration.get_nbo_bits()
        if not old_bits == 0b10:
            print('ALPHA OR BETA FOUND') #DELETE
            return filestream, df

        new_bits = old_bits | 0b11
        self._iteration.set_nbo_bits(new_bits)

        print('FOUND NPA CHARGES')
        npa_df = pandas.DataFrame(columns=line.split())

        # Need to dump first line to get past header and into atom data
        line = filestream.next()
        for _ in range(self._iteration.natoms):
            line = filestream.next()
            print(line) #DELETE
            row_vals = line.split()
            npa_df['Atom'] = npa_df['Atom'].append(row_vals[0])

        print(npa_df) #DELETE
        return filestream, df

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

