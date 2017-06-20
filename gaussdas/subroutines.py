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
        self._keys['Alpha  occ. eigenvalues'] = self.homo_lumo
        self._keys['Frequencies'] = self.frequencies
        self._keys['termination'] = self.g_terminations
        self._keys['Standard basis'] = self.basis
        self._keys['SCF Done'] = self.scf_functional
        self._keys['Standard orientation'] = self.coordinates
        
        self._iteration = Iteration()

        # Make sure there won't be any partial keyword collisions
        self._check_keys()

    def _check_keys(self):
        '''
        For making sure there aren't any partial string collisions that would
        compromise the current keyword-mapping strategy.  Could be made more
        efficient, but shouldn't be too much of a problem.
        '''
        key_list = [key for key in self._keys]
        for i in range(len(key_list)):
            count = 0
            for j in range(i+1, len(key_list)):
                smaller = min(key_list[i], key_list[j])
                larger = max(key_list[i], key_list[j])
                if smaller in larger:
                    count += 1
                if count > 0:
                    raise Warning(
                        'There are partial string collisions in the naming ' +
                        'of the key mappings.  This could cause parsing ' +
                        'errors.  Keys: \n %s\n %s' % (smaller, larger)
                    )

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
        series['atom no.'] = []
    
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
        series['atom no.'] = range(1, fields['natoms']+1)

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
    
    def npa(self, filestream, line, df, overwrite=True):
        '''
        For parsing out NPA charges from the file.  Relies on some bitwise
        logic to correctly grab the sum NPA charges, and not the alpha or beta
        specific charges.
        '''
        spin_mask = 0b01
        header_mask = 0b10
        old_bits = self._iteration.get_nbo_bits()

        if old_bits & spin_mask == 0b01:
            print('ALPHA OR BETA FOUND') #DELETE
            return filestream, df

        new_bits = old_bits | spin_mask
        self._iteration.set_nbo_bits(new_bits)

        print('FOUND NPA CHARGES') #DELETE
        cols = line.split()
        col_dict = {}
        for col in cols:
            col_dict[col] = []
        print(cols) #DELETE

        # Need to dump first line to get past header and into atom data
        # Keep big dict object incase I want the extra data later. Can easily
        # converte to DataFrame if I want to change data handling
        line = filestream.next()
        for i in range(self._iteration.natoms):
            line = filestream.next()
            row_vals = line.split()
            for col, val in zip(cols, row_vals):
                col_dict[col].append(val)
            
        # Need to rename charge column to prevent clash with system charge col
        new_str = 'npa charges'
        df = add_pandas_series(
            df, 
            {new_str : np.float64(col_dict['Charge'])}, 
            overwrite=overwrite
        )

        return filestream, df

    def homo_lumo(self, filestream, line, df, overwrite=True):
        homo = ['homo', 0]
        lumo = ['lumo', 0]
        gap = ['h-l gap', 0]

        # OMO levels always come before UMOs
        while 'Alpha  occ. eigenvalues' in line:
            homo[1] = line.split()[-1]
            line = filestream.next()

        homo[1] = np.float64(homo[1])

        # Now get the LUMO, which will be the first numerical value
        lumo[1] = np.float64(line.split()[4])

        # Calculate HOMO-LUMO gap
        gap[1] = lumo[1] - homo[1]

        df = add_pandas_fields(
                df, 
                [homo, lumo, gap], 
                overwrite=overwrite
        )

        return filestream, df

    def frequencies(self, filestream, line, df, overwrite=True):
        nfreqs = []
        imag_freqs = 0
        df_len = len(df)

        # Want to terminate while loop at blank line
        line_split = line.split()
        while line_split:
            if "Frequencies" in line_split:
                for freq in line_split[2:]:
                    if len(nfreqs) >= df_len:
                        break

                    nfreqs.append(np.float64(freq))
                    if freq < 0:
                        imag_freqs += 1
            line_split = filestream.next().split()

        df = add_pandas_series(
                df, 
                {'first_freqs': nfreqs}, 
                overwrite=overwrite
        )

        df = add_pandas_fields(
                df, 
                [['nimag_freqs', imag_freqs]], 
                overwrite=overwrite
        )

        return filestream, df

    def g_terminations(self, filestream, line, df, overwrite=True):
        '''
        Tabulate termination status of the output file, recording the error
        number if there is one
        '''
        fields = []
        term = ['termination', None]
        err = ['error no.', None]

        if 'Normal' in line:
            term[1] = 'normal'
        elif 'Error' in line:
            term[1] = 'error'
            err_no = line.split()[-1]
            err_no = err_no.rstrip('.')
            err[1] = err_no
            fields.append(err)

            filestream.next() # Throw away next line

        fields.append(term)

        df = add_pandas_fields(
            df,
            fields,
            overwrite=overwrite
        )

        return filestream, df

    def basis(self, filestream, line, df, overwrite=True):
        '''
        For recording the basis set used.  Not supporting multiple basis sets
        yet
        '''
        basis = ['basis', None]
        basis[1] = line.split()[2]

        df = add_pandas_fields(
            df,
            [basis],
            overwrite=overwrite
        )

        return filestream, df

    def scf_functional(self, filestream, line, df, overwrite=True):
        '''
        For grabbing functional data.  Get SCF energies in line with iteration
        number in the future.  Will currently overwrite previous functional,
        as would be the case in composite methods
        '''
        func = ['functional', None]
        
        elems = line.split()
        raw_func = elems[2]
        energy = elems[4]

        # Functional will always be of the form 'E(...)'
        func[1] = raw_func[2:-1]
        
        df = add_pandas_fields(
            df,
            [func],
            overwrite=overwrite
        )

        return filestream, df

    def coordinates(self, filestream, line, df, overwrite=True):
        '''
        Acquire the coordinates of the system on a rolling basis
        '''
        coords = []

        # Need to throw away the header
        for _ in range(4):
            line = filestream.next()

        for _ in range(self._iteration.natoms):
            line = filestream.next()
            line_split = line.split()
            xyz = [float(line_split[i]) for i in [3,4,5]]
            coords.append(xyz)

        df = add_pandas_series(
                df,
                {'coords' : coords},
                overwrite=overwrite
        )

        return filestream, df

def add_pandas_fields(df, data, multi_label=None, overwrite=True):
    '''
    Add fields and data to the DataFrame.  And overwrite=false method has
    not been written yet.  Added multi_label kwarg in case want to implement
    grouping multiple fields under a multiindex structure in the future
    '''
    if multi_label != None:
        raise NotImplementedError('multi_label has not yet been implemented')
    if overwrite == False:
        raise NotImplementedError('overwrite == False has not yet been implemented')

    print(data) #DELEE
    if isinstance(data, dict):
        #for field in data: df[field] = pandas.Series(data[field])
        for field in data: 
            print(df.index) #DELETE
            #tmp = df.assign(field=data[field])
            df[field] = data[field]
            print(df) #DELETE
            #tmp = pandas.DataFrame({field : data[field]}, index=df.index)
            #print(tmp) #DELETE
            #df = df.add(tmp)
        return df
    elif isinstance(data[0], list):
        #for field in data: df[field[0]] = pandas.Series(field[1])
        for field in data:
            label, val = field[0], field[1]
            df[label] = val
        return df
    
    data_series = pandas.Series(data[1])
    print(data_series) #DELETE
    df[data[0]] = data_series
    return df

def add_pandas_series(df, data, overwrite=True):
    '''
    Add some kind of series data to the DataFrame.  Method is currently
    only suited to take in dicts because of the way the resulting data is
    assigned to the final DataFrame.  This should be generalized to utilize
    a temporary DataFrame to make the method more robust in the future.
    '''
    tmp_df = pandas.DataFrame(data)
    len1 = len(df)
    len2 = len(tmp_df)
    if len1 < len2:
        df = df.reindex(df.index[0] for _ in range(len2))
        
    for col in tmp_df.columns:
        series_df = pandas.DataFrame(tmp_df[col])
        if col in df.columns:
            # This will need more testing
            if overwrite == False:
                print("DON'T OVERWRITE ME!!!!") #delete
                continue
            #df[col] = series_df
            df[col] = data[col]
        else:
            #df = pandas.concat([df, series_df], axis=1)
            #df[col] = series_df
            df[col] = data[col]
    
    return df

