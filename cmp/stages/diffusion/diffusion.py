# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for Diffusion reconstruction and tractography
"""

# General imports
import os

from traits.api import *

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util

# Own imports
from cmp.stages.common import Stage
from cmtklib.interfaces.misc import ExtractImageVoxelSizes
from .reconstruction import *
from .tracking import *


class DiffusionConfig(HasTraits):
    diffusion_imaging_model_editor = List(['DSI', 'DTI', 'HARDI'])
    diffusion_imaging_model = Str('DTI')
    dilate_rois = Bool(True)
    dilation_kernel = Enum(['Box', 'Gauss', 'Sphere'])
    dilation_radius = Enum([1, 2, 3, 4])
    # recon_processing_tool_editor = List(['Dipy', 'MRtrix', 'Custom'])
    # tracking_processing_tool_editor = List(['Dipy', 'MRtrix', 'Custom'])
    # processing_tool_editor = List(['Dipy', 'MRtrix', 'Custom'])
    recon_processing_tool_editor = List(['Dipy', 'MRtrix'])
    tracking_processing_tool_editor = List(['Dipy', 'MRtrix'])
    processing_tool_editor = List(['Dipy', 'MRtrix'])
    recon_processing_tool = Str('MRtrix')
    tracking_processing_tool = Str('MRtrix')
    custom_track_file = File
    dipy_recon_config = Instance(HasTraits)
    mrtrix_recon_config = Instance(HasTraits)
    # camino_recon_config = Instance(HasTraits)
    # fsl_recon_config = Instance(HasTraits)
    # gibbs_recon_config = Instance(HasTraits)
    dipy_tracking_config = Instance(HasTraits)
    mrtrix_tracking_config = Instance(HasTraits)
    # camino_tracking_config = Instance(HasTraits)
    # fsl_tracking_config = Instance(HasTraits)
    # gibbs_tracking_config = Instance(HasTraits)
    diffusion_model_editor = List(['Deterministic', 'Probabilistic'])
    diffusion_model = Str('Probabilistic')

    # TODO import custom DWI and tractogram (need to register anatomical data to DWI to project parcellated ROIs onto the tractogram)

    def __init__(self):
        # self.dtk_recon_config = DTK_recon_config(imaging_model=self.diffusion_imaging_model)
        self.dipy_recon_config = Dipy_recon_config(imaging_model=self.diffusion_imaging_model,
                                                   recon_mode=self.diffusion_model,
                                                   tracking_processing_tool=self.tracking_processing_tool)
        self.mrtrix_recon_config = MRtrix_recon_config(imaging_model=self.diffusion_imaging_model,
                                                       recon_mode=self.diffusion_model)
        # self.camino_recon_config = Camino_recon_config(imaging_model=self.diffusion_imaging_model)
        # self.fsl_recon_config = FSL_recon_config()
        # self.gibbs_recon_config = Gibbs_recon_config()
        # self.dtk_tracking_config = DTK_tracking_config()
        # self.dtb_tracking_config = DTB_tracking_config(imaging_model=self.diffusion_imaging_model)
        self.dipy_tracking_config = Dipy_tracking_config(imaging_model=self.diffusion_imaging_model,
                                                         tracking_mode=self.diffusion_model,
                                                         SD=self.mrtrix_recon_config.local_model)
        self.mrtrix_tracking_config = MRtrix_tracking_config(tracking_mode=self.diffusion_model,
                                                             SD=self.mrtrix_recon_config.local_model)
        # self.camino_tracking_config = Camino_tracking_config(imaging_model=self.diffusion_imaging_model,tracking_mode=self.diffusion_model)
        # self.fsl_tracking_config = FSL_tracking_config()
        # self.gibbs_tracking_config = Gibbs_tracking_config()

        self.mrtrix_recon_config.on_trait_change(
            self.update_mrtrix_tracking_SD, 'local_model')
        self.dipy_recon_config.on_trait_change(
            self.update_dipy_tracking_SD, 'local_model')
        self.dipy_recon_config.on_trait_change(
            self.update_dipy_tracking_sh_order, 'lmax_order')

        # self.camino_recon_config.on_trait_change(self.update_camino_tracking_model,'model_type')
        # self.camino_recon_config.on_trait_change(self.update_camino_tracking_model,'local_model')
        # self.camino_recon_config.on_trait_change(self.update_camino_tracking_inversion,'inversion')
        # self.camino_recon_config.on_trait_change(self.update_camino_tracking_inversion,'fallback_index')

    def _tracking_processing_tool_changed(self, new):
        if new == 'MRtrix':
            self.mrtrix_recon_config.tracking_processing_tool = new
        elif new == 'Dipy':
            self.dipy_recon_config.tracking_processing_tool = new

    def _diffusion_imaging_model_changed(self, new):
        # self.dtk_recon_config.imaging_model = new
        self.mrtrix_recon_config.imaging_model = new
        self.dipy_recon_config.imaging_model = new
        self.dipy_tracking_config.imaging_model = new
        # self.camino_recon_config.diffusion_imaging_model = new
        # self.dtk_tracking_config.imaging_model = new
        # self.dtb_tracking_config.imaging_model = new
        # Remove MRtrix from recon and tracking methods and Probabilistic from diffusion model if diffusion_imaging_model is DSI
        if (new == 'DSI'): # and (self.recon_processing_tool != 'Custom'):
            self.recon_processing_tool = 'Dipy'
            # self.recon_processing_tool_editor = ['Dipy', 'Custom']
            # self.tracking_processing_tool_editor = ['Dipy', 'MRtrix', 'Custom']
            self.recon_processing_tool_editor = ['Dipy']
            self.tracking_processing_tool_editor = ['Dipy', 'MRtrix']
            self.diffusion_model_editor = ['Deterministic', 'Probabilistic']
        else:
            # self.processing_tool_editor = ['DTK','MRtrix','Camino','FSL','Gibbs']
            # self.processing_tool_editor = ['Dipy','MRtrix']
            # self.recon_processing_tool_editor = ['Dipy', 'MRtrix', 'Custom']
            # self.tracking_processing_tool_editor = ['Dipy', 'MRtrix', 'Custom']
            self.recon_processing_tool_editor = ['Dipy', 'MRtrix']
            self.tracking_processing_tool_editor = ['Dipy', 'MRtrix']

            if self.tracking_processing_tool == 'DTK':
                self.diffusion_model_editor = ['Deterministic']
            else:
                self.diffusion_model_editor = [
                    'Deterministic', 'Probabilistic']

    def _recon_processing_tool_changed(self, new):
        # print("recon_processing_tool_changed : %s"%new)
        #
        if new == 'Dipy' and self.diffusion_imaging_model != 'DSI':
            tracking_processing_tool = self.tracking_processing_tool
            self.tracking_processing_tool_editor = ['Dipy', 'MRtrix']
            if tracking_processing_tool == 'Dipy' or tracking_processing_tool == 'MRtrix':
                self.tracking_processing_tool = tracking_processing_tool
        elif new == 'Dipy' and self.diffusion_imaging_model == 'DSI':
            tracking_processing_tool = self.tracking_processing_tool
            self.tracking_processing_tool_editor = ['Dipy', 'MRtrix']
            if tracking_processing_tool == 'Dipy' or tracking_processing_tool == 'MRtrix':
                self.tracking_processing_tool = tracking_processing_tool
        elif new == 'MRtrix':
            self.tracking_processing_tool_editor = ['MRtrix']
        # elif new == 'Custom':
        #     self.tracking_processing_tool_editor = ['Custom']

    def _tracking_processing_tool_changed(self, new):
        # print("tracking_processing_tool changed: %s"%new)
        if new == 'Dipy' and self.recon_processing_tool == 'Dipy':
            self.dipy_recon_config.tracking_processing_tool = 'Dipy'
        elif new == 'MRtrix' and self.recon_processing_tool == 'Dipy':
            self.dipy_recon_config.tracking_processing_tool = 'MRtrix'

    def _diffusion_model_changed(self, new):
        print("diffusion model changed")

        # self.mrtrix_recon_config.recon_mode = new # Probabilistic tracking only available for Spherical Deconvoluted data
        if self.tracking_processing_tool == 'MRtrix':
            self.mrtrix_tracking_config.tracking_mode = new
            print('tracking tool mrtrix')
            if new == 'Deterministic':
                print('det mode')
                # Make sure backtrack is disable for MRtrix Deterministic (ACT) Tractography
                print('Disable backtrack for deterministic ACT')
                self.mrtrix_tracking_config.backtrack = False
            else:
                print('prob mode')
        elif self.tracking_processing_tool == 'Dipy':
            print('tracking tool dipy')
            self.dipy_tracking_config.tracking_mode = new

        # self.camino_tracking_config.tracking_mode = new
        # self.update_camino_tracking_model()

    def update_dipy_tracking_sh_order(self, new):
        if new != 'Auto':
            self.dipy_tracking_config.sh_order = new
        else:
            self.dipy_tracking_config.sh_order = 8

    def update_mrtrix_tracking_SD(self, new):
        self.mrtrix_tracking_config.SD = new

    def update_dipy_tracking_SD(self, new):
        self.dipy_tracking_config.SD = new

    # def update_camino_tracking_model(self):
    #     if self.diffusion_model == 'Probabilistic':
    #         self.camino_tracking_config.tracking_model = 'pico'
    #     elif (self.camino_recon_config.model_type == 'Single-Tensor' or
    #           self.camino_recon_config.local_model == 'restore' or self.camino_recon_config.local_model == 'adc'):
    #         self.camino_tracking_config.tracking_model = 'dt'
    #     elif self.camino_recon_config.local_model == 'ball_stick':
    #         self.camino_tracking_config.tracking_model = 'ballstick'
    #     else:
    #         self.camino_tracking_config.tracking_model = 'multitensor'
    #
    # def update_camino_tracking_inversion(self):
    #     self.camino_tracking_config.inversion_index = self.camino_recon_config.inversion
    #     self.camino_tracking_config.fallback_index = self.camino_recon_config.fallback_index


def strip_suffix(file_input, prefix):
    import os
    from nipype.utils.filemanip import split_filename
    path, _, _ = split_filename(file_input)
    return os.path.join(path, prefix + '_')


class DiffusionStage(Stage):

    def __init__(self, bids_dir, output_dir):
        self.name = 'diffusion_stage'
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.config = DiffusionConfig()
        self.inputs = ["diffusion", "partial_volumes", "wm_mask_registered", "brain_mask_registered",
                       "act_5tt_registered", "gmwmi_registered", "roi_volumes", "grad", "bvals", "bvecs"]
        self.outputs = ["diffusion_model", "track_file", "fod_file", "FA", "ADC", "RD", "AD", "skewness", "kurtosis",
                        "P0", "roi_volumes", "shore_maps", "mapmri_maps"]

    def create_workflow(self, flow, inputnode, outputnode):

        if self.config.dilate_rois:

            dilate_rois = pe.MapNode(interface=fsl.DilateImage(), iterfield=[
                                     'in_file'], name='dilate_rois')
            dilate_rois.inputs.operation = 'modal'

            if self.config.dilation_kernel == 'Box':
                kernel_size = 2 * self.config.dilation_radius + 1
                dilate_rois.inputs.kernel_shape = 'boxv'
                dilate_rois.inputs.kernel_size = kernel_size
            else:
                extract_sizes = pe.Node(
                    interface=ExtractImageVoxelSizes(), name='extract_sizes')
                flow.connect([
                    (inputnode, extract_sizes, [("diffusion", "in_file")])
                ])
                extract_sizes.run()
                print("Voxel sizes : ", extract_sizes.outputs.voxel_sizes)

                min_size = 100
                for voxel_size in extract_sizes.outputs.voxel_sizes:
                    if voxel_size < min_size:
                        min_size = voxel_size

                print("voxel size (min): %g" % min_size)
                if self.confi.dilation_kernel == 'Gauss':
                    kernel_size = 2 * extract_sizes.outputs.voxel_sizes + 1
                    # FWHM criteria, i.e. sigma = FWHM / 2(sqrt(2ln(2)))
                    sigma = kernel_size / 2.355
                    dilate_rois.inputs.kernel_shape = 'gauss'
                    dilate_rois.inputs.kernel_size = sigma
                elif self.config.dilation_kernel == 'Sphere':
                    radius = 0.5 * min_size + self.config.dilation_radius * min_size
                    dilate_rois.inputs.kernel_shape = 'sphere'
                    dilate_rois.inputs.kernel_size = radius

            flow.connect([
                (inputnode, dilate_rois, [("roi_volumes", "in_file")]),
                (dilate_rois, outputnode, [("out_file", "roi_volumes")])
            ])
        else:
            flow.connect([
                (inputnode, outputnode, [("roi_volumes", "roi_volumes")])
            ])

        if self.config.recon_processing_tool == 'Dipy':
            recon_flow = create_dipy_recon_flow(self.config.dipy_recon_config)

            flow.connect([
                (inputnode, recon_flow, [
                 ('diffusion', 'inputnode.diffusion')]),
                (inputnode, recon_flow, [('bvals', 'inputnode.bvals')]),
                (inputnode, recon_flow, [('bvecs', 'inputnode.bvecs')]),
                (inputnode, recon_flow, [
                 ('diffusion', 'inputnode.diffusion_resampled')]),
                (inputnode, recon_flow, [
                 ('wm_mask_registered', 'inputnode.wm_mask_resampled')]),
                (inputnode, recon_flow, [
                 ('brain_mask_registered', 'inputnode.brain_mask_resampled')]),
                (recon_flow, outputnode, [("outputnode.FA", "FA")]),
                (recon_flow, outputnode, [("outputnode.MD", "ADC")]),
                (recon_flow, outputnode, [("outputnode.AD", "AD")]),
                (recon_flow, outputnode, [("outputnode.RD", "RD")]),
                (recon_flow, outputnode, [
                 ("outputnode.shore_maps", "shore_maps")]),
                (recon_flow, outputnode, [
                 ("outputnode.mapmri_maps", "mapmri_maps")]),
            ])

        elif self.config.recon_processing_tool == 'MRtrix':
            # TODO modify nipype tensormetric interface to get AD and RD maps
            recon_flow = create_mrtrix_recon_flow(
                self.config.mrtrix_recon_config)
            flow.connect([
                (inputnode, recon_flow, [
                 ('diffusion', 'inputnode.diffusion')]),
                (inputnode, recon_flow, [('grad', 'inputnode.grad')]),
                (inputnode, recon_flow, [
                 ('diffusion', 'inputnode.diffusion_resampled')]),
                (inputnode, recon_flow, [
                 ('brain_mask_registered', 'inputnode.wm_mask_resampled')]),
                (recon_flow, outputnode, [("outputnode.FA", "FA")]),
                (recon_flow, outputnode, [("outputnode.ADC", "ADC")]),
                (recon_flow, outputnode, [("outputnode.tensor", "tensor")]),
                # (recon_flow,outputnode,[("outputnode.AD","AD")]),
                # (recon_flow,outputnode,[("outputnode.RD","RD")]),
            ])

        # elif self.config.recon_processing_tool == 'Camino':
        #     recon_flow = create_camino_recon_flow(self.config.camino_recon_config)
        #     flow.connect([
        #                 (inputnode,recon_flow,[('diffusion','inputnode.diffusion')]),
        #                 (inputnode,recon_flow,[('diffusion','inputnode.diffusion_resampled')]),
        #                 (inputnode, recon_flow,[('wm_mask_registered','inputnode.wm_mask_resampled')]),
        #                 (recon_flow,outputnode,[("outputnode.FA","FA")])
        #                 ])
        #
        # elif self.config.recon_processing_tool == 'FSL':
        #     recon_flow = create_fsl_recon_flow(self.config.fsl_recon_config)
        #     flow.connect([
        #                 (inputnode,recon_flow,[('diffusion','inputnode.diffusion_resampled')]),
        #                 (inputnode, recon_flow,[('wm_mask_registered','inputnode.wm_mask_resampled')])
        #                 ])

        if self.config.tracking_processing_tool == 'Dipy':
            track_flow = create_dipy_tracking_flow(
                self.config.dipy_tracking_config)
            # print "Dipy tracking"

            if self.config.diffusion_imaging_model != 'DSI':
                flow.connect([
                    (recon_flow, outputnode, [('outputnode.DWI', 'fod_file')]),
                    (recon_flow, track_flow, [
                     ('outputnode.model', 'inputnode.model')]),
                    (inputnode, track_flow, [('bvals', 'inputnode.bvals')]),
                    (recon_flow, track_flow, [
                     ('outputnode.bvecs', 'inputnode.bvecs')]),
                    # Diffusion resampled
                    (inputnode, track_flow, [('diffusion', 'inputnode.DWI')]),
                    (inputnode, track_flow, [
                     ('partial_volumes', 'inputnode.partial_volumes')]),
                    (inputnode, track_flow, [
                     ('wm_mask_registered', 'inputnode.wm_mask_resampled')]),
                    # (inputnode, track_flow,[('diffusion','inputnode.DWI')]),
                    (recon_flow, track_flow, [
                     ("outputnode.FA", "inputnode.FA")]),
                    (dilate_rois, track_flow, [
                     ('out_file', 'inputnode.gm_registered')])
                    # (recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
                ])
            else:
                flow.connect([
                    (recon_flow, outputnode, [('outputnode.fod', 'fod_file')]),
                    (recon_flow, track_flow, [
                     ('outputnode.fod', 'inputnode.fod_file')]),
                    (recon_flow, track_flow, [
                     ('outputnode.model', 'inputnode.model')]),
                    (inputnode, track_flow, [('bvals', 'inputnode.bvals')]),
                    (recon_flow, track_flow, [
                     ('outputnode.bvecs', 'inputnode.bvecs')]),
                    # Diffusion resampled
                    (inputnode, track_flow, [('diffusion', 'inputnode.DWI')]),
                    (inputnode, track_flow, [
                     ('partial_volumes', 'inputnode.partial_volumes')]),
                    (inputnode, track_flow, [
                     ('wm_mask_registered', 'inputnode.wm_mask_resampled')]),
                    # (inputnode, track_flow,[('diffusion','inputnode.DWI')]),
                    (recon_flow, track_flow, [
                     ("outputnode.FA", "inputnode.FA")]),
                    (dilate_rois, track_flow, [
                     ('out_file', 'inputnode.gm_registered')])
                    # (recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
                ])

            if self.config.dipy_tracking_config.use_act and self.config.dipy_tracking_config.seed_from_gmwmi:
                flow.connect([
                    (inputnode, track_flow, [
                     ('gmwmi_registered', 'inputnode.gmwmi_file')]),
                ])

            flow.connect([
                (track_flow, outputnode, [
                 ('outputnode.track_file', 'track_file')])
            ])

        elif self.config.tracking_processing_tool == 'MRtrix' and self.config.recon_processing_tool == 'MRtrix':
            track_flow = create_mrtrix_tracking_flow(
                self.config.mrtrix_tracking_config)
            # print "MRtrix tracking"

            flow.connect([
                (inputnode, track_flow, [
                 ('wm_mask_registered', 'inputnode.wm_mask_resampled')]),
                (recon_flow, outputnode, [('outputnode.DWI', 'fod_file')]),
                (recon_flow, track_flow, [
                 ('outputnode.DWI', 'inputnode.DWI'), ('outputnode.grad', 'inputnode.grad')]),
                # (recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
            ])

            if self.config.dilate_rois:
                flow.connect([
                    (dilate_rois, track_flow, [
                     ('out_file', 'inputnode.gm_registered')])
                ])
            else:
                flow.connect([
                    (inputnode, track_flow, [
                     ('roi_volumes', 'inputnode.gm_registered')])
                ])

            flow.connect([
                (inputnode, track_flow, [
                 ('act_5tt_registered', 'inputnode.act_5tt_registered')]),
                (inputnode, track_flow, [
                 ('gmwmi_registered', 'inputnode.gmwmi_registered')])
            ])

            flow.connect([
                (track_flow, outputnode, [
                 ('outputnode.track_file', 'track_file')])
            ])

        elif self.config.tracking_processing_tool == 'MRtrix' and self.config.recon_processing_tool == 'Dipy':
            track_flow = create_mrtrix_tracking_flow(
                self.config.mrtrix_tracking_config)
            # print "MRtrix tracking"

            if self.config.diffusion_imaging_model != 'DSI':
                flow.connect([
                    (inputnode, track_flow, [('wm_mask_registered', 'inputnode.wm_mask_resampled'),
                                             ('grad', 'inputnode.grad')]),
                    (recon_flow, outputnode, [('outputnode.DWI', 'fod_file')]),
                    (recon_flow, track_flow, [
                     ('outputnode.DWI', 'inputnode.DWI')]),
                    # (recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
                ])
            else:
                flow.connect([
                    (inputnode, track_flow, [('wm_mask_registered', 'inputnode.wm_mask_resampled'),
                                             ('grad', 'inputnode.grad')]),
                    (recon_flow, outputnode, [('outputnode.fod', 'fod_file')]),
                    (recon_flow, track_flow, [
                     ('outputnode.fod', 'inputnode.DWI')]),
                    # (recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
                ])

            if self.config.dilate_rois:
                flow.connect([
                    (dilate_rois, track_flow, [
                     ('out_file', 'inputnode.gm_registered')])
                ])
            else:
                flow.connect([
                    (inputnode, track_flow, [
                     ('roi_volumes', 'inputnode.gm_registered')])
                ])

            flow.connect([
                (inputnode, track_flow, [
                 ('act_5tt_registered', 'inputnode.act_5tt_registered')]),
                (inputnode, track_flow, [
                 ('gmwmi_registered', 'inputnode.gmwmi_registered')])
            ])

            #  if self.config.diffusion_model == 'Probabilistic':
            #      flow.connect([
            # (dilate_rois,track_flow,[('out_file','inputnode.gm_registered')]),
            # ])

            flow.connect([
                (track_flow, outputnode, [
                 ('outputnode.track_file', 'track_file')])
            ])

        # elif self.config.tracking_processing_tool == 'Camino':
        #     track_flow = create_camino_tracking_flow(self.config.camino_tracking_config)
        #     flow.connect([
        #                 (inputnode, track_flow,[('wm_mask_registered','inputnode.wm_mask_resampled')]),
        #                 (recon_flow, track_flow,[('outputnode.DWI','inputnode.DWI'), ('outputnode.grad','inputnode.grad')])
        #                 ])
        #     if self.config.diffusion_model == 'Probabilistic':
        #         flow.connect([
        #             (dilate_rois,track_flow,[('out_file','inputnode.gm_registered')]),
        #             ])
        #     flow.connect([
        #                 (track_flow,outputnode,[('outputnode.track_file','track_file')])
        #                 ])
        #
        # elif self.config.tracking_processing_tool == 'FSL':
        #     track_flow = create_fsl_tracking_flow(self.config.fsl_tracking_config)
        #     flow.connect([
        #                 (inputnode, track_flow,[('wm_mask_registered','inputnode.wm_mask_resampled')]),
        #                 (dilate_rois,track_flow,[('out_file','inputnode.gm_registered')]),
        #                 (recon_flow,track_flow,[('outputnode.fsamples','inputnode.fsamples')]),
        #                 (recon_flow,track_flow,[('outputnode.phsamples','inputnode.phsamples')]),
        #                 (recon_flow,track_flow,[('outputnode.thsamples','inputnode.thsamples')]),
        #                 ])
        #     flow.connect([
        #                 (track_flow,outputnode,[("outputnode.targets","track_file")]),
        #                 ])

        temp_node = pe.Node(interface=util.IdentityInterface(
            fields=["diffusion_model"]), name='diffusion_model')
        temp_node.inputs.diffusion_model = self.config.diffusion_model
        flow.connect([
            (temp_node, outputnode, [("diffusion_model", "diffusion_model")])
        ])

        # if self.config.tracking_processing_tool == 'Custom':
        #     # FIXME make sure header of TRK / TCK are consistent with DWI
        #     custom_node = pe.Node(interface=util.IdentityInterface(fields=["custom_track_file"]),
        #                           name='read_custom_track')
        #     custom_node.inputs.custom_track_file = self.config.custom_track_file
        #     if nib.streamlines.detect_format(self.config.custom_track_file) is nib.streamlines.TrkFile:
        #         print("> load TRK tractography file")
        #         flow.connect([
        #             (custom_node, outputnode, [
        #              ("custom_track_file", "track_file")])
        #         ])
        #     elif nib.streamlines.detect_format(self.config.custom_track_file) is nib.streamlines.TckFile:
        #         print("> load TCK tractography file and convert to TRK format")
        #         converter = pe.Node(interface=Tck2Trk(), name='trackvis')
        #         converter.inputs.out_tracks = 'converted.trk'

        #         flow.connect([
        #             (custom_node, converter, [
        #              ('custom_track_file', 'in_tracks')]),
        #             (inputnode, converter, [
        #              ('wm_mask_registered', 'in_image')]),
        #             (converter, outputnode, [('out_tracks', 'track_file')])
        #         ])
        #     else:
        #         print(
        #             "Invalid tractography input format. Valid formats are .tck (MRtrix) and .trk (DTK/Trackvis)")

    def define_inspect_outputs(self):
        # print "stage_dir : %s" % self.stage_dir

        self.inspect_outputs_dict = {}

        # RECON outputs
        # Dipy
        if self.config.recon_processing_tool == 'Dipy':
            if self.config.dipy_recon_config.local_model or self.config.diffusion_imaging_model == 'DSI':  # SHORE or CSD models

                if self.config.diffusion_imaging_model == 'DSI':

                    recon_dir = os.path.join(self.stage_dir, "reconstruction", "dipy_SHORE")

                    gfa_res = os.path.join(recon_dir, 'shore_gfa.nii.gz')
                    if os.path.exists(gfa_res):
                        self.inspect_outputs_dict[self.config.recon_processing_tool + ' gFA image'] = ['mrview',
                                                                                                       gfa_res]
                    msd_res = os.path.join(recon_dir, 'shore_msd.nii.gz')
                    if os.path.exists(msd_res):
                        self.inspect_outputs_dict[self.config.recon_processing_tool + ' MSD image'] = ['mrview',
                                                                                                       msd_res]
                    rtop_res = os.path.join(recon_dir, 'shore_rtop_signal.nii.gz')
                    if os.path.exists(rtop_res):
                        self.inspect_outputs_dict[self.config.recon_processing_tool + ' RTOP image'] = ['mrview',
                                                                                                        rtop_res]
                    dodf_res = os.path.join(recon_dir, 'shore_dodf.nii.gz')
                    if os.path.exists(dodf_res):
                        self.inspect_outputs_dict[
                            self.config.recon_processing_tool + ' Diffusion ODF (SHORE) image'] = ['mrview', gfa_res,
                                                                                               '-odf.load_sh',
                                                                                               dodf_res]
                    shm_coeff_res = os.path.join(recon_dir, 'shore_fodf.nii.gz')
                    if os.path.exists(shm_coeff_res):
                        self.inspect_outputs_dict[self.config.recon_processing_tool + ' Fiber ODF (SHORE) image'] = [
                            'mrview', gfa_res, '-odf.load_sh', shm_coeff_res]
                else:
                    recon_tensor_dir = os.path.join(self.stage_dir, "reconstruction", "dipy_tensor")

                    fa_res = os.path.join(recon_tensor_dir,'diffusion_preproc_resampled_fa.nii.gz')
                    if os.path.exists(fa_res):
                        self.inspect_outputs_dict[self.config.recon_processing_tool + ' FA image'] = ['mrview',
                                                                                                      fa_res]

                    recon_dir = os.path.join(self.stage_dir, "reconstruction", "dipy_CSD")
                    shm_coeff_res = os.path.join(recon_dir, 'diffusion_shm_coeff.nii.gz')
                    if os.path.exists(shm_coeff_res):
                        if os.path.exists(fa_res):
                            self.inspect_outputs_dict[self.config.recon_processing_tool + ' ODF (CSD) image'] = [
                                'mrview', fa_res, '-odf.load_sh', shm_coeff_res]
                        else:
                            shm_coeff_res = recon_results.outputs.out_shm_coeff
                            self.inspect_outputs_dict[self.config.recon_processing_tool + ' ODF (CSD) image'] = [
                                'mrview', shm_coeff_res, '-odf.load_sh', shm_coeff_res]

        # TODO: add Tensor image in case of DTI+Tensor modeling
        # MRtrix
        if self.config.recon_processing_tool == 'MRtrix':
            metrics_dir = os.path.join(self.stage_dir, "reconstruction", "mrtrix_tensor_metrics")

            fa_res = os.path.join(metrics_dir, 'FA.mif')
            if os.path.exists(fa_res):
                self.inspect_outputs_dict[self.config.recon_processing_tool +
                                          ' FA image'] = ['mrview', fa_res]

            adc_res = os.path.join(metrics_dir, 'ADC.mif')
            if os.path.exists(adc_res):
                self.inspect_outputs_dict[self.config.recon_processing_tool +
                                      ' ADC image'] = ['mrview', adc_res]

            # Tensor model (DTI)
            if not self.config.mrtrix_recon_config.local_model:
                recon_dir = os.path.join(self.stage_dir, "reconstruction", "mrtrix_make_tensor")

                tensor_res = os.path.join(recon_dir, 'diffusion_preproc_resampled_tensor.mif')
                if (os.path.exists(fa_res) and os.path.exists(tensor_res)):
                    self.inspect_outputs_dict[self.config.recon_processing_tool + ' SH image'] = ['mrview', fa_res,
                                                                                                  '-odf.load_tensor',
                                                                                                  tensor_res]

            else:  # CSD model

                RF_dir = os.path.join(self.stage_dir, "reconstruction", "mrtrix_rf")
                RF_resp = os.path.join(RF_dir, 'diffusion_preproc_resampled_ER.mif')
                if (os.path.exists(RF_resp)):
                    self.inspect_outputs_dict['MRTRIX Response function'] = ['shview', '-response',
                                                                             RF_resp]

                recon_dir = os.path.join(self.stage_dir, "reconstruction", "mrtrix_CSD")
                shm_coeff_res = os.path.join(recon_dir, 'diffusion_preproc_resampled_CSD.mif')
                if (os.path.exists(fa_res) and os.path.exists(shm_coeff_res)):
                    self.inspect_outputs_dict[self.config.recon_processing_tool + ' SH image'] = ['mrview', fa_res,
                                                                                                  '-odf.load_sh',
                                                                                                  shm_coeff_res]

        # Tracking outputs
        # Dipy
        if (self.config.tracking_processing_tool == 'Dipy'):
            # print('Dipy tracking: true')
            if self.config.dipy_recon_config.local_model or self.config.diffusion_imaging_model == 'DSI':

                if self.config.diffusion_model == 'Deterministic':
                    diff_dir = os.path.join(self.stage_dir, "tracking", "dipy_deterministic_tracking")
                    streamline_res = os.path.join(diff_dir,"tract.trk")
                else:
                    diff_dir = os.path.join(self.stage_dir, "tracking", "dipy_probabilistic_tracking")
                    streamline_res = os.path.join(diff_dir,"tract.trk")

                if os.path.exists(streamline_res):
                    self.inspect_outputs_dict[
                        self.config.tracking_processing_tool + ' ' + self.config.diffusion_model + ' streamline'] = [
                        'trackvis', streamline_res]

            else:

                diff_dir = os.path.join(self.stage_dir, "tracking", "dipy_dtieudx_tracking")
                streamline_res = os.path.join(diff_dir,"tract.trk")
                if os.path.exists(streamline_res):
                    self.inspect_outputs_dict[
                        self.config.tracking_processing_tool + ' Tensor-based EuDX streamline'] = ['trackvis',
                                                                                                   streamline_res]

        # MRtrix
        if self.config.tracking_processing_tool == 'MRtrix':

            diff_dir = os.path.join(self.stage_dir, "tracking", "trackvis")
            streamline_res = os.path.join(diff_dir,"tract.trk")

            if os.path.exists(streamline_res):
               self.inspect_outputs_dict[
                    self.config.tracking_processing_tool + ' ' + self.config.diffusion_model + ' streamline'] = [
                    'trackvis', streamline_res]

        self.inspect_outputs = sorted([key for key in list(self.inspect_outputs_dict.keys())],
                                      key=str.lower)

    def has_run(self):
        if self.config.tracking_processing_tool == 'Dipy':
            if self.config.diffusion_model == 'Deterministic':
                return os.path.exists(os.path.join(self.stage_dir, "tracking", "dipy_deterministic_tracking",
                                                   "result_dipy_deterministic_tracking.pklz"))
            elif self.config.diffusion_model == 'Probabilistic':
                return os.path.exists(os.path.join(self.stage_dir, "tracking", "dipy_probabilistic_tracking",
                                                   "result_dipy_probabilistic_tracking.pklz"))
        elif self.config.tracking_processing_tool == 'MRtrix':
            return os.path.exists(os.path.join(self.stage_dir, "tracking", "trackvis", "result_trackvis.pklz"))
