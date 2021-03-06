# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" Common class for CMP Stages
"""

# Libraries imports
import os

from traits.api import *


class Stage(HasTraits):
    '''Stage master class.

    It will be inherited by the various stage subclasses.

    Inherits from HasTraits.'''
    bids_dir = Str
    output_dir = Str
    inspect_outputs = ['Outputs not available']
    inspect_outputs_enum = Enum(values='inspect_outputs')
    inspect_outputs_dict = Dict
    enabled = True
    config = Instance(HasTraits)

    def is_running(self):
        unfinished_files = [os.path.join(dirpath, f)
                            for dirpath, dirnames, files in os.walk(self.stage_dir)
                            for f in files if f.endswith('_unfinished.json')]
        return len(unfinished_files)
