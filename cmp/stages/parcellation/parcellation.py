# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for Parcellation
"""

# General imports
import os
from traits.api import *
import pkg_resources

# Nipype imports
import nipype.pipeline.engine as pe  # pypeline engine
# import nipype.interfaces.cmtk as cmtk
import nipype.interfaces.utility as util

from cmtklib.parcellation import Parcellate, ParcellateBrainstemStructures, \
    ParcellateHippocampalSubfields, ParcellateThalamus, \
    CombineParcellations, ComputeParcellationRoiVolumes
from cmtklib.util import get_pipeline_dictionary_outputs

# Own imports
from cmp.stages.common import Stage


class ParcellationConfig(HasTraits):
    pipeline_mode = Enum(["Diffusion", "fMRI"])
    parcellation_scheme = Str('Lausanne2008')
    # parcellation_scheme_editor = List(
    #     ['NativeFreesurfer', 'Lausanne2008', 'Lausanne2018', 'Custom'])
    parcellation_scheme_editor = List(
        ['NativeFreesurfer', 'Lausanne2008', 'Lausanne2018'])
    include_thalamic_nuclei_parcellation = Bool(True)
    ants_precision_type = Enum(['double', 'float'])
    # template_thalamus = File()
    # thalamic_nuclei_maps = File()
    segment_hippocampal_subfields = Bool(True)
    segment_brainstem = Bool(True)
    pre_custom = Str('Lausanne2008')
    # atlas_name = Str()
    number_of_regions = Int()
    atlas_nifti_file = File(exists=True)
    csf_file = File(exists=True)
    brain_file = File(exists=True)
    graphml_file = File(exists=True)
    atlas_info = Dict()

    def update_atlas_info(self):
        atlas_name = os.path.basename(self.atlas_nifti_file)
        atlas_name = os.path.splitext(os.path.splitext(atlas_name)[0])[
            0].encode('ascii')
        self.atlas_info = {
            atlas_name: {'number_of_regions': self.number_of_regions, 'node_information_graphml': self.graphml_file}}

    def _atlas_nifti_file_changed(self, new):
        self.update_atlas_info()

    def _number_of_regions_changed(self, new):
        self.update_atlas_info()

    def _graphml_file_changed(self, new):
        self.update_atlas_info()

    # def _parcellation_scheme_changed(self, old, new):
    #     if new == 'Custom':
    #         self.pre_custom = old


class ParcellationStage(Stage):

    def __init__(self, pipeline_mode, bids_dir, output_dir):
        self.name = 'parcellation_stage'
        self.bids_dir = bids_dir
        self.output_dir = output_dir
        self.config = ParcellationConfig()
        # self.config.template_thalamus =
        #    os.path.abspath(pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation',
        #                                                    'thalamus2018', 'mni_icbm152_t1_tal_nlin_sym_09b_hires_1.nii.gz')))
        # self.config.thalamic_nuclei_maps =
        #    os.path.abspath(pkg_resources.resource_filename('cmtklib', os.path.join('data', 'segmentation', 'thalamus2018',
        #                                                    'Thalamus_Nuclei-HCP-4DSPAMs.nii.gz')))
        self.config.pipeline_mode = pipeline_mode
        self.inputs = ["subjects_dir", "subject_id", "custom_wm_mask"]
        self.outputs = [  # "aseg_file",
            "T1", "brain", "aseg", "brain_mask",
            "wm_mask_file",
            "wm_eroded",
            "csf_eroded",
            "brain_eroded",
            "gm_mask_file",
            "csf_mask_file",
            "aseg", "aparc_aseg",
            # "cc_unknown_file","ribbon_file","roi_files",
            "roi_volumes", "roi_colorLUTs", "roi_graphMLs", "roi_volumes_stats",
            "parcellation_scheme", "atlas_info"]

    def create_workflow(self, flow, inputnode, outputnode):
        # from nipype.interfaces.fsl.maths import MathsCommand

        outputnode.inputs.parcellation_scheme = self.config.parcellation_scheme

        def get_basename(path):
            import os
            path = os.path.basename(path)
            print(path)
            return path

        if self.config.parcellation_scheme != "Custom":

            parc_node = pe.Node(interface=Parcellate(
            ), name="%s_parcellation" % self.config.parcellation_scheme)
            parc_node.inputs.parcellation_scheme = self.config.parcellation_scheme
            parc_node.inputs.erode_masks = True

            flow.connect([
                (inputnode, parc_node,
                 [("subjects_dir", "subjects_dir"), (("subject_id",  get_basename), "subject_id")]),
                (parc_node, outputnode, [  # ("aseg_file","aseg_file"),("cc_unknown_file","cc_unknown_file"),
                    # ("ribbon_file","ribbon_file"),("roi_files","roi_files"),
                    ("white_matter_mask_file", "wm_mask_file"),
                    ("csf_mask_file", "csf_mask_file"),
                    # ("gray_matter_mask_file","gm_mask_file"),
                    # ("roi_files_in_structural_space","roi_volumes"),
                    ("wm_eroded", "wm_eroded"), ("csf_eroded",
                                                 "csf_eroded"), ("brain_eroded", "brain_eroded"),
                    ("T1", "T1"), ("brain", "brain"), ("brain_mask", "brain_mask")])
            ])

            flow.connect([
                (parc_node, outputnode, [("aseg", "aseg")]),
            ])

            # threshold_roi = pe.Node(interface=fsl.MathsCommand(out_file='T1w_class-GM.nii.gz'),name='make_gm_mask')
            #
            # flow.connect([
            #             (threshold_roi,outputnode,[("out_file","gm_mask_file")]),
            #             ])

            if self.config.parcellation_scheme == 'Lausanne2018':
                parcCombiner = pe.Node(
                    interface=CombineParcellations(), name="parcCombiner")
                parcCombiner.inputs.create_colorLUT = True
                parcCombiner.inputs.create_graphml = True

                flow.connect([
                    (inputnode, parcCombiner,
                     [("subjects_dir", "subjects_dir"), (("subject_id",  get_basename), "subject_id")]),
                    (parc_node, parcCombiner, [
                     ("roi_files_in_structural_space", "input_rois")]),
                ])

                if self.config.segment_brainstem:
                    parcBrainStem = pe.Node(
                        interface=ParcellateBrainstemStructures(), name="parcBrainStem")

                    flow.connect([
                        (inputnode, parcBrainStem,
                         [("subjects_dir", "subjects_dir"), (("subject_id",  get_basename), "subject_id")]),
                        (parcBrainStem, parcCombiner, [
                         ("brainstem_structures", "brainstem_structures")]),
                    ])

                if self.config.segment_hippocampal_subfields:
                    parcHippo = pe.Node(
                        interface=ParcellateHippocampalSubfields(), name="parcHippo")

                    flow.connect([
                        (inputnode, parcHippo,
                         [("subjects_dir", "subjects_dir"), (("subject_id",  get_basename), "subject_id")]),
                        (parcHippo, parcCombiner, [
                         ("lh_hipposubfields", "lh_hippocampal_subfields")]),
                        (parcHippo, parcCombiner, [
                         ("rh_hipposubfields", "rh_hippocampal_subfields")]),
                    ])

                if self.config.include_thalamic_nuclei_parcellation:
                    parcThal = pe.Node(
                        interface=ParcellateThalamus(), name="parcThal")
                    parcThal.inputs.template_image = os.path.abspath(pkg_resources.resource_filename('cmtklib',
                                                                                                     os.path.join(
                                                                                                         'data',
                                                                                                         'segmentation',
                                                                                                         'thalamus2018',
                                                                                                         'mni_icbm152_t1_tal_nlin_sym_09b_hires_1.nii.gz')))
                    parcThal.inputs.thalamic_nuclei_maps = os.path.abspath(pkg_resources.resource_filename('cmtklib',
                                                                                                           os.path.join(
                                                                                                               'data',
                                                                                                               'segmentation',
                                                                                                               'thalamus2018',
                                                                                                               'Thalamus_Nuclei-HCP-4DSPAMs.nii.gz')))
                    parcThal.inputs.ants_precision_type = self.config.ants_precision_type

                    flow.connect([
                        (inputnode, parcThal,
                         [("subjects_dir", "subjects_dir"), (("subject_id",  get_basename), "subject_id")]),
                        (parc_node, parcThal, [("T1", "T1w_image")]),
                        (parcThal, parcCombiner, [
                         ("max_prob_registered", "thalamus_nuclei")]),
                    ])

                flow.connect([
                    (parc_node, outputnode, [
                     ("gray_matter_mask_file", "gm_mask_file")]),
                    (parcCombiner, outputnode, [("aparc_aseg", "aparc_aseg")]),
                    (parcCombiner, outputnode, [
                     ("output_rois", "roi_volumes")]),
                    (parcCombiner, outputnode, [
                     ("colorLUT_files", "roi_colorLUTs")]),
                    (parcCombiner, outputnode, [
                     ("graphML_files", "roi_graphMLs")]),
                ])

                computeROIVolumetry = pe.Node(
                    interface=ComputeParcellationRoiVolumes(), name='computeROIVolumetry')
                computeROIVolumetry.inputs.parcellation_scheme = self.config.parcellation_scheme

                flow.connect([
                    (parcCombiner, computeROIVolumetry,
                     [("output_rois", "roi_volumes")]),
                    (parcCombiner, computeROIVolumetry, [
                     ("graphML_files", "roi_graphMLs")]),
                    (computeROIVolumetry, outputnode, [
                     ("roi_volumes_stats", "roi_volumes_stats")]),
                ])

                # create_atlas_info = pe.Node(interface=CreateLausanne2018AtlasInfo(),name="create_atlas_info")
                # flow.connect([
                #             (parcCombiner,create_atlas_info,[("output_rois","roi_volumes")]),
                #             (parcCombiner,create_atlas_info,[("graphML_files","roi_graphMLs")]),
                #             (create_atlas_info,outputnode,[("atlas_info","atlas_info")]),
                #         ])
            elif self.config.parcellation_scheme == 'Lausanne2008':

                roi_colorLUTs = [os.path.join(pkg_resources.resource_filename('cmtklib',
                                                                              os.path.join('data', 'parcellation',
                                                                                           'lausanne2008',
                                                                                           'resolution83',
                                                                                           'resolution83_LUT.txt'))),
                                 os.path.join(pkg_resources.resource_filename('cmtklib',
                                                                              os.path.join('data', 'parcellation',
                                                                                           'lausanne2008',
                                                                                           'resolution150',
                                                                                           'resolution150_LUT.txt'))),
                                 os.path.join(pkg_resources.resource_filename('cmtklib',
                                                                              os.path.join('data', 'parcellation',
                                                                                           'lausanne2008',
                                                                                           'resolution258',
                                                                                           'resolution258_LUT.txt'))),
                                 os.path.join(pkg_resources.resource_filename('cmtklib',
                                                                              os.path.join('data', 'parcellation',
                                                                                           'lausanne2008',
                                                                                           'resolution500',
                                                                                           'resolution500_LUT.txt'))),
                                 os.path.join(pkg_resources.resource_filename('cmtklib',
                                                                              os.path.join('data', 'parcellation',
                                                                                           'lausanne2008',
                                                                                           'resolution1015',
                                                                                           'resolution1015_LUT.txt')))
                                 ]

                roi_graphMLs = [os.path.join(pkg_resources.resource_filename('cmtklib',
                                                                             os.path.join('data', 'parcellation',
                                                                                          'lausanne2008',
                                                                                          'resolution83',
                                                                                          'resolution83.graphml'))),
                                os.path.join(pkg_resources.resource_filename('cmtklib',
                                                                             os.path.join('data', 'parcellation',
                                                                                          'lausanne2008',
                                                                                          'resolution150',
                                                                                          'resolution150.graphml'))),
                                os.path.join(pkg_resources.resource_filename('cmtklib',
                                                                             os.path.join('data', 'parcellation',
                                                                                          'lausanne2008',
                                                                                          'resolution258',
                                                                                          'resolution258.graphml'))),
                                os.path.join(pkg_resources.resource_filename('cmtklib',
                                                                             os.path.join('data', 'parcellation',
                                                                                          'lausanne2008',
                                                                                          'resolution500',
                                                                                          'resolution500.graphml'))),
                                os.path.join(pkg_resources.resource_filename('cmtklib',
                                                                             os.path.join('data', 'parcellation',
                                                                                          'lausanne2008',
                                                                                          'resolution1015',
                                                                                          'resolution1015.graphml')))
                                ]

                parc_files = pe.Node(interface=util.IdentityInterface(fields=["roi_colorLUTs", "roi_graphMLs"]),
                                     name="parcellation_files")
                parc_files.inputs.roi_colorLUTs = [
                    '{}'.format(p) for p in roi_colorLUTs]
                parc_files.inputs.roi_graphMLs = [
                    '{}'.format(p) for p in roi_graphMLs]

                # print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
                # print("^^^^ Lausanne2008 color LUT / graphML ^^^^")
                # print(outputnode.outputs.roi_colorLUTs)
                # print(outputnode.outputs.roi_graphMLs)
                # print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")

                flow.connect([
                    (parc_node, outputnode, [
                     ("gray_matter_mask_file", "gm_mask_file")]),
                    (parc_node, outputnode, [("aparc_aseg", "aparc_aseg")]),
                    (parc_node, outputnode, [
                     ("roi_files_in_structural_space", "roi_volumes")]),
                    (parc_files, outputnode, [
                     ("roi_colorLUTs", "roi_colorLUTs")]),
                    (parc_files, outputnode, [
                     ("roi_graphMLs", "roi_graphMLs")]),
                    # (parc_node,outputnode,[(("roi_files_in_structural_space",get_atlas_LUTs),"roi_colorLUTs")]),
                    # (parc_node,outputnode,[(("roi_files_in_structural_space",get_atlas_graphMLs),"roi_graphMLs")]),
                ])

                computeROIVolumetry = pe.Node(
                    interface=ComputeParcellationRoiVolumes(), name='computeROIVolumetry')
                computeROIVolumetry.inputs.parcellation_scheme = self.config.parcellation_scheme

                flow.connect([
                    (parc_node, computeROIVolumetry, [
                     ("roi_files_in_structural_space", "roi_volumes")]),
                    (parc_files, computeROIVolumetry, [
                     ("roi_graphMLs", "roi_graphMLs")]),
                    (computeROIVolumetry, outputnode, [
                     ("roi_volumes_stats", "roi_volumes_stats")]),
                ])
            else:
                # def get_atlas_LUTs(paths):
                #     colorLUTs = [os.path.join(pkg_resources.resource_filename('
                #                     cmtklib',os.path.join('data','parcellation','nativefreesurfer','
                #                                           freesurferaparc','FreeSurferColorLUT_adapted.txt'))),
                #                  ]
                #     return colorLUTs
                #
                # def get_atlas_graphMLs(paths):
                #     graphMLs = [os.path.join(pkg_resources.resource_filename(
                #                   'cmtklib',os.path.join('data','parcellation','nativefreesurfer',
                #                                          'freesurferaparc','resolution83.graphml'))),
                #                  ]
                #     return graphMLs

                roi_colorLUTs = [os.path.join(pkg_resources.resource_filename('cmtklib',
                                                                              os.path.join('data', 'parcellation',
                                                                                           'nativefreesurfer',
                                                                                           'freesurferaparc',
                                                                                           'FreeSurferColorLUT_adapted.txt')))]

                roi_graphMLs = [os.path.join(pkg_resources.resource_filename('cmtklib',
                                                                             os.path.join('data', 'parcellation',
                                                                                          'nativefreesurfer',
                                                                                          'freesurferaparc',
                                                                                          'freesurferaparc.graphml')))]

                parc_files = pe.Node(interface=util.IdentityInterface(fields=["roi_colorLUTs", "roi_graphMLs"]),
                                     name="parcellation_files")
                parc_files.inputs.roi_colorLUTs = [
                    '{}'.format(p) for p in roi_colorLUTs]
                parc_files.inputs.roi_graphMLs = [
                    '{}'.format(p) for p in roi_graphMLs]

                flow.connect([
                    (parc_node, outputnode, [
                     ("gray_matter_mask_file", "gm_mask_file")]),
                    (parc_node, outputnode, [("aparc_aseg", "aparc_aseg")]),
                    (parc_node, outputnode, [
                     ("roi_files_in_structural_space", "roi_volumes")]),
                    (parc_files, outputnode, [
                     ("roi_colorLUTs", "roi_colorLUTs")]),
                    (parc_files, outputnode, [
                     ("roi_graphMLs", "roi_graphMLs")]),
                    # (parc_node,outputnode,[(("roi_files_in_structural_space",get_atlas_LUTs),"roi_colorLUTs")]),
                    # (parc_node,outputnode,[(("roi_files_in_structural_space",get_atlas_graphMLs),"roi_graphMLs")]),
                ])

                computeROIVolumetry = pe.Node(
                    interface=ComputeParcellationRoiVolumes(), name='computeROIVolumetry')
                computeROIVolumetry.inputs.parcellation_scheme = self.config.parcellation_scheme

                flow.connect([
                    (parc_node, computeROIVolumetry, [
                     ("roi_files_in_structural_space", "roi_volumes")]),
                    (parc_files, computeROIVolumetry, [
                     ("roi_graphMLs", "roi_graphMLs")]),
                    (computeROIVolumetry, outputnode, [
                     ("roi_volumes_stats", "roi_volumes_stats")]),
                ])

            # TODO
            # if self.config.pipeline_mode == "fMRI":
            #     erode_wm = pe.Node(interface=cmtk.Erode(),name="erode_wm")
            #     flow.connect([
            #                 (inputnode,erode_wm,[("custom_wm_mask","in_file")]),
            #                 (erode_wm,outputnode,[("out_file","wm_eroded")]),
            #                 ])
            #     if os.path.exists(self.config.csf_file):
            #         erode_csf = pe.Node(interface=cmtk.Erode(in_file = self.config.csf_file),name="erode_csf")
            #         flow.connect([
            #                     (erode_csf,outputnode,[("out_file","csf_eroded")])
            #                     ])
            #     if os.path.exists(self.config.brain_file):
            #         erode_brain = pe.Node(interface=cmtk.Erode(in_file = self.config.brain_file),name="erode_brain")
            #         flow.connect([
            #                     (erode_brain,outputnode,[("out_file","brain_eroded")])
            #                     ])
        # Custom parcellation (CMP2)
        # else:
        #     temp_node = pe.Node(interface=util.IdentityInterface(fields=["roi_volumes", "atlas_info"]),
        #                         name="custom_parcellation")
        #     temp_node.inputs.roi_volumes = self.config.atlas_nifti_file
        #     temp_node.inputs.atlas_info = self.config.atlas_info
        #     flow.connect([
        #         (temp_node, outputnode, [("roi_volumes", "roi_volumes")]),
        #         (temp_node, outputnode, [("atlas_info", "atlas_info")]),
        #         (inputnode, outputnode, [("custom_wm_mask", "wm_mask_file")])
        #     ])

        #     threshold_roi = pe.Node(
        #         interface=fsl.BinaryThreshold(
        #             thresh=0.0, binarize=True, out_file='T1w_class-GM.nii.gz'),
        #         name='threshold_roi_bin')

        #     def get_first(roi_volumes):
        #         if len(roi_volumes) > 1:
        #             return roi_volumes[0]
        #         else:
        #             return roi_volumes

        #     flow.connect([
        #         (temp_node, threshold_roi, [
        #          (("roi_volumes", get_first), "in_file")]),
        #         (threshold_roi, outputnode, [("out_file", "gm_mask_file")]),
        #     ])

        #     if self.config.pipeline_mode == "fMRI":
        #         erode_wm = pe.Node(interface=cmtk.Erode(), name="erode_wm")
        #         flow.connect([
        #             (inputnode, erode_wm, [("custom_wm_mask", "in_file")]),
        #             (erode_wm, outputnode, [("out_file", "wm_eroded")]),
        #         ])
        #         if os.path.exists(self.config.csf_file):
        #             erode_csf = pe.Node(interface=cmtk.Erode(
        #                 in_file=self.config.csf_file), name="erode_csf")
        #             flow.connect([
        #                 (erode_csf, outputnode, [("out_file", "csf_eroded")])
        #             ])
        #         if os.path.exists(self.config.brain_file):
        #             erode_brain = pe.Node(interface=cmtk.Erode(
        #                 in_file=self.config.brain_file), name="erode_brain")
        #             flow.connect([
        #                 (erode_brain, outputnode, [
        #                  ("out_file", "brain_eroded")])
        #             ])

    def define_inspect_outputs(self):
        print("stage_dir : %s" % self.stage_dir)
        print("parcellation scheme : %s" % self.config.parcellation_scheme)

        anat_sinker_dir = os.path.join(os.path.dirname(self.stage_dir), 'anatomical_sinker')
        anat_sinker_report = os.path.join(anat_sinker_dir, '_report', 'report.rst')
        # print "atlas info : "
        # print self.config.atlas_info

        if self.config.parcellation_scheme != "Custom":
            if (os.path.exists(anat_sinker_report)):
                anat_outputs = get_pipeline_dictionary_outputs(anat_sinker_report, self.output_dir)

                white_matter_file = anat_outputs['anat.@wm_mask']

                if isinstance(anat_outputs['anat.@roivs'], str):
                    # print "str: %s" % parc_results.outputs.roi_files_in_structural_space
                    lut_file = pkg_resources.resource_filename('cmtklib',
                                                               os.path.join('data', 'parcellation', 'nativefreesurfer',
                                                                            'freesurferaparc',
                                                                            'FreeSurferColorLUT_adapted.txt'))
                    roi_v = anat_outputs['anat.@roivs']

                    # print "roi_v : %s" % os.path.basename(roi_v)
                    if (os.path.exists(white_matter_file) and os.path.exists(roi_v)):
                        self.inspect_outputs_dict[os.path.basename(roi_v)] = ['freeview', '-v',
                                                                              white_matter_file + ':colormap=GEColor',
                                                                              roi_v + ":colormap=lut:lut=" + lut_file]
                elif isinstance(anat_outputs['anat.@roivs'], list):
                    # print parc_results.outputs.roi_files_in_structural_space
                    if self.config.parcellation_scheme == 'Lausanne2008':
                        resolution = {'1': 'resolution83', '2': 'resolution150', '3': 'resolution258',
                                      '4': 'resolution500', '5': 'resolution1015'}
                        for roi_v in anat_outputs['anat.@roivs']:
                            roi_basename = os.path.basename(roi_v)
                            print(roi_basename)
                            scale = roi_basename[23:-7]
                            print(scale)

                            # print scale
                            lut_file = pkg_resources.resource_filename('cmtklib', os.path.join('data', 'parcellation',
                                                                                               'lausanne2008',
                                                                                               resolution[scale],
                                                                                               resolution[
                                                                                                   scale] + '_LUT.txt'))
                            if (os.path.exists(white_matter_file) and os.path.exists(roi_v)):
                                self.inspect_outputs_dict[roi_basename] = ['freeview', '-v',
                                                                            white_matter_file + ':colormap=GEColor',
                                                                            roi_v + ":colormap=lut:lut=" + lut_file]
                    elif self.config.parcellation_scheme == 'Lausanne2018':
                        # resolution = {'1':'resolution1','2':'resolution2','3':'resolution3','4':'resolution4','5':'resolution5'}

                        for roi_v, lut_file in zip(anat_outputs['anat.@roivs'],
                                                   anat_outputs['anat.@luts']):
                            roi_basename = os.path.basename(roi_v)

                            if (os.path.exists(white_matter_file) and os.path.exists(roi_v)):
                                self.inspect_outputs_dict[roi_basename] = ['freeview', '-v',
                                                                            white_matter_file + ':colormap=GEColor',
                                                                            roi_v + ":colormap=lut:lut=" + lut_file]

                # self.inspect_outputs = self.inspect_outputs_dict.keys()
        # else:
        #     self.inspect_outputs_dict["Custom atlas"] = [
        #         'fsleyes', self.config.atlas_nifti_file, "-cm", "random"]

        self.inspect_outputs = sorted([key for key in list(self.inspect_outputs_dict.keys())],
                                      key=str.lower)

    def has_run(self):
        if self.config.parcellation_scheme != "Custom":
            if self.config.parcellation_scheme == 'Lausanne2018':
                return os.path.exists(os.path.join(self.stage_dir, "parcCombiner", "result_parcCombiner.pklz"))
            else:
                return os.path.exists(os.path.join(self.stage_dir, "%s_parcellation" % self.config.parcellation_scheme,
                                                   "result_%s_parcellation.pklz" % self.config.parcellation_scheme))
        # else:
        #     return os.path.exists(self.config.atlas_nifti_file)
