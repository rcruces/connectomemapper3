# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for building connectivity matrices and resulting CFF file
"""

# Global imports
import os

from traits.api import *

# import pickle
# import gzip


# Nipype imports
import nipype.pipeline.engine as pe
# from nipype.utils.filemanip import split_filename

# Own imports
import cmtklib.connectome
# import cmtklib as cmtk
from cmp.stages.common import Stage
from cmtklib.util import get_pipeline_dictionary_outputs


class ConnectomeConfig(HasTraits):
    apply_scrubbing = Bool(False)
    FD_thr = Float(0.2)
    DVARS_thr = Float(4.0)
    output_types = List(['gPickle', 'mat', 'cff', 'graphml'])
    log_visualization = Bool(True)
    circular_layout = Bool(False)
    subject = Str()


class ConnectomeStage(Stage):

    def __init__(self, bids_dir, output_dir):
        self.name = 'connectome_stage'
        self.bids_dir = bids_dir
        self.output_dir = output_dir

        self.config = ConnectomeConfig()
        self.inputs = ["roi_volumes_registered", "func_file", "FD", "DVARS",
                       "parcellation_scheme", "atlas_info", "roi_graphMLs"]
        self.outputs = ["connectivity_matrices", "avg_timeseries"]

    def create_workflow(self, flow, inputnode, outputnode):
        cmtk_cmat = pe.Node(interface=cmtklib.connectome.rsfmri_conmat(), name='compute_matrice')
        cmtk_cmat.inputs.output_types = self.config.output_types
        cmtk_cmat.inputs.apply_scrubbing = self.config.apply_scrubbing
        cmtk_cmat.inputs.FD_th = self.config.FD_thr
        cmtk_cmat.inputs.DVARS_th = self.config.DVARS_thr

        flow.connect([
            (inputnode, cmtk_cmat, [('func_file', 'func_file'), ("FD", "FD"), ("DVARS", "DVARS"),
                                    ('parcellation_scheme',
                                     'parcellation_scheme'), ('atlas_info', 'atlas_info'),
                                    ('roi_volumes_registered', 'roi_volumes'), ('roi_graphMLs', 'roi_graphmls')]),
            (cmtk_cmat, outputnode,
             [('connectivity_matrices', 'connectivity_matrices'), ("avg_timeseries", "avg_timeseries")])
        ])

    def define_inspect_outputs(self):
        func_sinker_dir = os.path.join(os.path.dirname(self.stage_dir), 'bold_sinker')
        func_sinker_report = os.path.join(func_sinker_dir, '_report', 'report.rst')

        if os.path.exists(func_sinker_report):

            func_outputs = get_pipeline_dictionary_outputs(func_sinker_report, self.output_dir)

            map_scale = "default"
            if self.config.log_visualization:
                map_scale = "log"

            if self.config.circular_layout:
                layout = 'circular'
            else:
                layout = 'matrix'

            mat = func_outputs['func.@connectivity_matrices']
            # print('con_results_path : ',con_results_path)

            if isinstance(mat, str):
                print("single scale")
                # print(mat)
                if 'gpickle' in mat:
                    con_name = os.path.basename(mat).split(".")[
                        0].split("_")[-1]
                    if os.path.exists(mat):
                        self.inspect_outputs_dict[
                            'ROI-average time-series correlation - Connectome %s' % os.path.basename(mat)] = [
                            "showmatrix_gpickle", layout, mat, "corr", "False",
                            self.config.subject + ' - ' + con_name + ' - Correlation', map_scale]
            else:
                print("multi scale")
                for mat in func_outputs['func.@connectivity_matrices']:
                    # print(mat)
                    if 'gpickle' in mat:
                        con_name = os.path.basename(mat).split(".")[
                            0].split("_")[-1]
                        if os.path.exists(mat):
                            self.inspect_outputs_dict['ROI-average time-series correlation - Connectome %s' % con_name] = [
                                "showmatrix_gpickle", layout, mat, "corr", "False",
                                self.config.subject + ' - ' + con_name + ' - Correlation', map_scale]

            self.inspect_outputs = sorted([key for key in list(self.inspect_outputs_dict.keys())],
                                          key=str.lower)

    def has_run(self):
        return os.path.exists(os.path.join(self.stage_dir, "compute_matrice", "result_compute_matrice.pklz"))
