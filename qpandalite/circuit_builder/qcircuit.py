'''
Definition of quantum circuit (Circuit)

Author: Agony5757
'''

import warnings
from .basic_gates import *

def _check_qubit_overflow(qubits, n):    
    '''Check if any qubit in qubits (list) is overflow.
    
    Args:
        qubits (list):
        n (int):
    Returns:
        bool: True (if ok) or False (if overflow)
    '''
    for qubit in qubits:
        if qubit >= n:
            return False
        
    return True

def _check_qubit_key(qubit_key: str):
    '''check if qubit_key match ''q+any integer'' format (q1, q2, etc.) 
    
    Returns:
        int : if the qubit_key is available, return this qubit; or None : if not match this style.
    '''
    if not qubit_key.startswith('q'):
        return None
    
    try:
        q = int(qubit_key[1:])
        return q
    except:
        return None

class Circuit:
    '''Quantum circuit.

    Args:
        n_qubit (int) : number of qubits in the circuit
        name (str, optional) : the name of this circuit

    Notes:
        A template of circuit object. By assigning the qubit, we can create a concrete insertable circuit.    
        The qubit/cbit in the gate template is represented by {q1}/{q2}/{q3}... instead of q1/q2/q3.
        It allows users to format the gate template and assign it to the circuit.

    Examples:
        .. code-block:: python

            toffoli = GateTemplate(n_qubit = 3)
            # (... some definitions)
            toffoli_123   = toffoli.assign(q1 = 1, q2 = 2, q3 = 3) # to assign the corresponding qubits, returning a 'Gate'
            toffoli_214   = toffoli.assign(q1 = 2, q2 = 1, q3 = 4) # to assign the corresponding qubits, returning a 'Gate'
            toffoli_fix_1 = toffoli.assign(q1 = 1) # to assign partially, returning another 'GateTemplate'

            c = Circuit()
            c.gate(toffoli_123)                             # good
            c.gate(toffoli)                                 # bad, because it is not fully converted to a gate
            c.gate(toffoli_fix_1.format(q2 = 2, q3 = 3))    # good
                
    '''

    def __init__(self, name = None):   
        self.gate_list = []
        if not name:
            self.name = None
        else:
            self.name = name

        self.involved_qubits = []
        self.fragment = False
        self.expand = True
        self.mapping = None

    def circuit_str(self) -> str:       
        ret = '' 
        for gate in self.gate_list:
            ret += '{};\n'.format(gate)
        return ret
    
    def __repr__(self) -> str:
        if self.fragment:
            if not self.name:
                raise RuntimeError('Fatal: Unexpected noname fragment.')
            ret = '---{:^25s}---\n'.format(f'Fragment {self.name}')
            ret += self.circuit_str()
        elif not self.expand:
            if self.mapping:
                if self.name:
                    ret = f'{self.name} qubit_mapping: {self.mapping}'
                else:
                    ret = f'{hex(id(self.name))} qubit_mapping: {self.mapping}'
            else:
                if self.name:
                    ret = f'{self.name} q{self.involved_qubits}'
                else:
                    ret = f'{hex(id(self.name))} q{self.involved_qubits}'

        else:
            ret = self.circuit_str()
        return ret
    
    def _check_qubit_map(self, qubit_map):
        for qubit in self.involved_qubits:
            if qubit not in qubit_map:
                return False
            
        return True


    def assign_by_map(self, qubit_map):
        ret = Circuit(self.name)

        if not self._check_qubit_map(qubit_map):
            raise RuntimeError('Qubit map does not cover all involved qubits. '
                               'Every involved qubits must be a key in qubit_map.\n' 
                               f'Expect: {ret.involved_qubits}, Get: {qubit_map}')
        ret.mapping = qubit_map
        
        for gate in self.gate_list:
            assigned_gate = gate.assign_by_map(qubit_map)
            ret._append_gate(assigned_gate)
        
        return ret

    def _parse_qubit_map_from_kwargs(self, **kwargs):
        '''
        Implementation of assign (kwargs case).

        Raises:
            RuntimeError: Error in parsing kwargs

        Returns:
            dict: qubit map
        '''
        keys = kwargs.keys()
        qubit_map = dict()
        for key in keys:
            if key == 'n_qubit': continue
            q = _check_qubit_key(key)
            if q is None:
                # do not match q+integer style
                raise RuntimeError('Input must be q+integer=integer style (e.g. q1=1, etc.). User input: {}'.format(key))
            
            assigned_q = kwargs[key]
            if not isinstance(assigned_q, int):
                raise RuntimeError('Input must be q+integer=integer style (e.g. q1=1, etc.). User input: {}, assigned_q: {}'.format(key, assigned_q))
            
            qubit_map[q] = assigned_q

        return qubit_map
    
    def _parse_qubit_map_from_list(self, *args):
        if len(args) == 0:
            raise RuntimeError('Fatal!!! Unexpected error.')
        if isinstance(args[0], list):
            qubit_list = args[0]
        else:
            qubit_list = args
        qubit_map = dict()
        for i, qubit in enumerate(qubit_list):
            qubit_map[i] = qubit
        
        return qubit_map

    def assign(self, *args, **kwargs):  
        '''Reassign the qubits with the given input.

        Args:
            n_qubit (int, optional): The number of qubits in the newly generated circuit.
            args (list, optional): A given qubit list in *args form.
            kwargs (optional): A kwarg dict like (q1=1, q2=3, q3=2)

        Raises:
            RuntimeError: Cannot assign an unlimited circuit. (when self.n_qubit is None)
            RuntimeError: Cannot shrink circuit size. (when self.n_qubit > n_qubit)
            
        Returns:
            BigGate: Return a new BigGate instance.

        Examples:
            Three types of inputs are accepted.

            List-arg-type:

            .. code-block:: python

                c = BigGate()
                # some definitions ...
                c.assign(1,2,3)
                
            List-type:

            .. code-block:: python

                c = BigGate()
                # some definitions ...
                c.assign([1,2,3])
                
            Kwargs-type:

            .. code-block:: python

                c = BigGate()
                # some definitions ...
                c.assign(q0=1,q1=2,q2=3)

            The above three types share the same semantic.
        '''
        if len(args) > 0:
            # _assign_list mode
            qubit_map = self._parse_qubit_map_from_list(*args)
        else:
            # _assign_kwargs mode
            qubit_map = self._parse_qubit_map_from_kwargs(**kwargs)

        ret = self.assign_by_map(qubit_map)
        return ret
            
    def _append_gate(self, gate_object : Gate):
        '''Add gate to the quantum circuit.
        '''
        # check overflow
        qubits = gate_object.involved_qubits()
              
        self.gate_list.append(gate_object)
        for qubit in qubits:
            if qubit not in self.involved_qubits:
                self.involved_qubits.append(qubit)

    def _append_circuit(self, new_circuit, expand = True):
        '''Connect two circuits.
        When the append circuit is another object, it modifies self without affecting new_circuit.
        When the append circuit is self, it appends a copy of self.
        '''
        if isinstance(new_circuit, Fragment):
            raise RuntimeError('Append a fragment circuit without assigning qubits.')

        if id(new_circuit) == id(self):
            # check if self-appending
            new_circuit = deepcopy(new_circuit)

        for qubit in new_circuit.involved_qubits:
            if qubit not in self.involved_qubits:
                self.involved_qubits.append(qubit)

        if expand or new_circuit.expand:
            for gate in new_circuit.gate_list:
                self.gate_list.append(gate)
        else:
            self.gate_list.append(new_circuit)

    def append(self, object, **kwargs):
        '''Append an object (Gate/Circuit)
        '''
        if isinstance(object, Circuit):
            if 'expand' in kwargs:
                expand = kwargs['expand']
            else:
                expand = False
            self._append_circuit(object, expand)
        elif isinstance(object, Gate):
            self._append_gate(object)
        else:
            raise NotImplementedError

    def rx(self, qubit, angle):    
        '''Append a Rx gate

        Args:
            qubit (int, str): the qubit id
            angle (float, str): the angle

        Returns:
            Circuit: self
        '''
        self._append_gate(Rx(qubit, angle))
        return self

    def ry(self, qubit, angle):   
        '''Append a Ry gate

        Args:
            qubit (int, str): the qubit id
            angle (float, str): the angle

        Returns:
            Circuit: self
        '''
        self._append_gate(Ry(qubit, angle))
        return self

    def rz(self, qubit, angle):   
        '''Append a Rz gate

        Args:
            qubit (int, str): the qubit id
            angle (float, str): the angle

        Returns:
            Circuit: self
        '''
        self._append_gate(Rz(qubit, angle))

class Fragment(Circuit):
    def __init__(self, name):
        super().__init__(name)
        self.fragment = True
        self.expand = False

    def assign(self, *args, **kwargs):
        ret = super().assign(*args, **kwargs)
        ret.expand = False
        return ret

class QProg:
    '''An abstract representation of a quantum circuit.
    Attributes:
        - n_qubit : number of qubits
        - n_cbit : number of cbits
        - gate_list (Python list) : a list of gates
    '''

    def __init__(self, n_qubit = 1, n_cbit = 0):
        '''Constructing an empty circuit.
        Args:
            n_qubit (int): number of qubits
            n_cbit (int): number of cbits
        '''
        self.n_qubit = n_qubit
        self.n_cbit = n_cbit
        self.gate_list = []
        self.has_measure = False
        if (not n_qubit) and (not n_cbit):
            warnings.warn('A completely empty circuit instance is created. (n_qubit = n_cbit = 0)')

    def __repr__(self) -> str:
        return ('{} qubits\n'
                '{} cbits\n'
                '{} gates\n'
                ).format(self.n_qubit, self.n_cbit, len(self.gate_list))
    
    def append(self, gate):
        self.gate_list.append(gate)

    def dagger(self):
        if self.has_measure:
            raise RuntimeError('Cannot inverse a classical-involved circuit.')
        

    def to_originir(self) -> str:
        '''Convert to originir
        '''
        pass
        