import bpy
import time
import logging
from . import ifcopenshell
from . import export_ifc
from . import import_ifc
from bpy_extras.io_utils import ImportHelper
from itertools import cycle

class ExportIFC(bpy.types.Operator):
    bl_idname = "export.ifc"
    bl_label = "Export .ifc file"
    filename_ext = ".ifc"
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = bpy.path.ensure_ext(bpy.data.filepath, ".ifc")
        WindowManager = context.window_manager
        WindowManager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        start = time.time()
        ifc_export_settings = export_ifc.IfcExportSettings()
        logging.basicConfig(
            filename=bpy.context.scene.BIMProperties.data_dir + 'process.log',
            filemode='a', level=logging.DEBUG)
        ifc_export_settings.logger = logging.getLogger('ExportIFC')
        ifc_export_settings.logger.info('Starting export')
        ifc_export_settings.data_dir = bpy.context.scene.BIMProperties.data_dir
        ifc_export_settings.schema_dir = bpy.context.scene.BIMProperties.schema_dir
        ifc_export_settings.output_file = bpy.path.ensure_ext(self.filepath, '.ifc')
        ifc_export_settings.has_representations = bpy.context.scene.BIMProperties.export_has_representations
        ifc_parser = export_ifc.IfcParser(ifc_export_settings)
        ifc_schema = export_ifc.IfcSchema(ifc_export_settings)
        qto_calculator = export_ifc.QtoCalculator()
        ifc_exporter = export_ifc.IfcExporter(ifc_export_settings, ifc_schema, ifc_parser, qto_calculator)
        ifc_exporter.export()
        ifc_export_settings.logger.info('Export finished in {:.2f} seconds'.format(time.time() - start))
        return {'FINISHED'}

class ImportIFC(bpy.types.Operator, ImportHelper):
    bl_idname = "import.ifc"
    bl_label = "Import .ifc file"

    filename_ext = ".ifc"
    filter_glob: bpy.props.StringProperty(default="*.ifc", options={'HIDDEN'})

    def execute(self, context):
        start = time.time()
        ifc_import_settings = import_ifc.IfcImportSettings()
        logging.basicConfig(
            filename=bpy.context.scene.BIMProperties.data_dir + 'process.log',
            filemode='a', level=logging.DEBUG)
        ifc_import_settings.logger = logging.getLogger('ImportIFC')
        ifc_import_settings.logger.info('Starting import')
        ifc_import_settings.input_file = self.filepath
        ifc_importer = import_ifc.IfcImporter(ifc_import_settings)
        ifc_importer.execute()
        ifc_import_settings.logger.info('Import finished in {:.2f} seconds'.format(time.time() - start))
        return {'FINISHED'}

class SelectGlobalId(bpy.types.Operator):
    bl_idname = 'bim.select_global_id'
    bl_label = 'Select GlobalId'

    def execute(self, context):
        for object in bpy.context.visible_objects:
            index = object.BIMObjectProperties.attributes.find('GlobalId')
            if index != -1 \
                and object.BIMObjectProperties.attributes[index].string_value == bpy.context.scene.BIMProperties.global_id:
                object.select_set(True)
                break
        return {'FINISHED'}

class AssignClass(bpy.types.Operator):
    bl_idname = 'bim.assign_class'
    bl_label = 'Assign IFC Class'

    def execute(self, context):
        for object in bpy.context.selected_objects:
            existing_class = None
            if '/' in object.name \
                and object.name[0:3] == 'Ifc':
                existing_class = object.name.split('/')[0]
            if existing_class:
                object.name = '{}/{}'.format(
                    bpy.context.scene.BIMProperties.ifc_class,
                    object.name.split('/')[1])
            else:
                object.name = '{}/{}'.format(
                    bpy.context.scene.BIMProperties.ifc_class,
                    object.name)
            predefined_type_index = object.BIMObjectProperties.attributes.find('PredefinedType')
            if predefined_type_index >= 0:
                object.BIMObjectProperties.attributes.remove(predefined_type_index)
            object_type_index = object.BIMObjectProperties.attributes.find('ObjectType')
            if object_type_index >= 0:
                object.BIMObjectProperties.attributes.remove(object_type_index)
            if bpy.context.scene.BIMProperties.ifc_predefined_type:
                predefined_type = object.BIMObjectProperties.attributes.add()
                predefined_type.name = 'PredefinedType'
                predefined_type.string_value = bpy.context.scene.BIMProperties.ifc_predefined_type # TODO: make it an enum
            if bpy.context.scene.BIMProperties.ifc_predefined_type == 'USERDEFINED':
                object_type = object.BIMObjectProperties.attributes.add()
                object_type.name = 'ObjectType'
                object_type.string_value = bpy.context.scene.BIMProperties.ifc_userdefined_type
        return {'FINISHED'}

class SelectClass(bpy.types.Operator):
    bl_idname = 'bim.select_class'
    bl_label = 'Select IFC Class'

    def execute(self, context):
        for object in bpy.context.visible_objects:
            if '/' in object.name \
                and object.name[0:3] == 'Ifc' \
                and object.name.split('/')[0] == bpy.context.scene.BIMProperties.ifc_class:
                object.select_set(True)
        return {'FINISHED'}

class SelectType(bpy.types.Operator):
    bl_idname = 'bim.select_type'
    bl_label = 'Select IFC Type'

    def execute(self, context):
        for object in bpy.context.visible_objects:
            if '/' in object.name \
                and object.name[0:3] == 'Ifc' \
                and object.name.split('/')[0] == bpy.context.scene.BIMProperties.ifc_class \
                and 'IfcPredefinedType' in object.keys() \
                and object['IfcPredefinedType'] == bpy.context.scene.BIMProperties.ifc_predefined_type:
                if bpy.context.scene.BIMProperties.ifc_predefined_type != 'USERDEFINED':
                    object.select_set(True)
                elif object['IfcObjectType'] == bpy.context.scene.BIMProperties.ifc_userdefined_type:
                    object.select_set(True)
        return {'FINISHED'}

class ColourByClass(bpy.types.Operator):
    bl_idname = 'bim.colour_by_class'
    bl_label = 'Colour by Class'

    def execute(self, context):
        colour_list = [
            (.651, .81, .892, 1),
            (.121, .471, .706, 1),
            (.699, .876, .54, 1),
            (.199, .629, .174, 1),
            (.983, .605, .602, 1),
            (.89, .101, .112, 1),
            (.989, .751, .427, 1),
            (.986, .497, .1, 1),
            (.792, .699, .839, 1),
            (.414, .239, .603, 1),
            (.993, .999, .6, 1),
            (.693, .349, .157, 1)]
        colours = cycle(colour_list)
        ifc_classes = {}
        for object in bpy.context.selected_objects:
            if '/' not in object.name:
                continue
            ifc_class = object.name.split('/')[0]
            if ifc_class not in ifc_classes:
                ifc_classes[ifc_class] = next(colours)
            object.color = ifc_classes[ifc_class]
        return {'FINISHED'}

class ResetObjectColours(bpy.types.Operator):
    bl_idname = 'bim.reset_object_colours'
    bl_label = 'Reset Colours'

    def execute(self, context):
        for object in bpy.context.selected_objects:
            object.color = (1, 1, 1, 1)
        return {'FINISHED'}

class ApproveClass(bpy.types.Operator):
    bl_idname = 'bim.approve_class'
    bl_label = 'Approve Class'

    def execute(self, context):
        with open(bpy.context.scene.BIMProperties.data_dir + 'audit.txt', 'a') as file:
            for object in bpy.context.selected_objects:
                file.write('Then the element {} is an {}\n'.format(
                    object['IfcGlobalId'], object.name.split('/')[0]))
        return {'FINISHED'}

class RejectClass(bpy.types.Operator):
    bl_idname = 'bim.reject_class'
    bl_label = 'Reject Class'

    def execute(self, context):
        with open(bpy.context.scene.BIMProperties.data_dir + 'audit.txt', 'a') as file:
            for object in bpy.context.selected_objects:
                file.write('Then the element {} is an {}\n'.format(
                    object['IfcGlobalId'], bpy.context.scene.BIMProperties.ifc_class))
        return {'FINISHED'}

class RejectElement(bpy.types.Operator):
    bl_idname = 'bim.reject_element'
    bl_label = 'Reject Element'

    def execute(self, context):
        with open(bpy.context.scene.BIMProperties.data_dir + 'audit.txt', 'a') as file:
            for object in bpy.context.selected_objects:
                file.write('Then the element {} should not exist because {}\n'.format(
                    object['IfcGlobalId'], bpy.context.scene.BIMProperties.qa_reject_element_reason))
        return {'FINISHED'}

class SelectAudited(bpy.types.Operator):
    bl_idname = 'bim.select_audited'
    bl_label = 'Select Audited'

    def execute(self, context):
        with open(bpy.context.scene.BIMProperties.data_dir + 'audit.txt') as file:
            for line in file:
                for object in bpy.context.visible_objects:
                    if 'IfcGlobalId' in object.keys() \
                        and object['IfcGlobalId'] == line.split(' ')[3]:
                        object.select_set(True)
        return {'FINISHED'}

class QuickProjectSetup(bpy.types.Operator):
    bl_idname = 'bim.quick_project_setup'
    bl_label = 'Quick Project Setup'

    def execute(self, context):
        project = bpy.data.collections.new('IfcProject/My Project')
        bpy.context.scene.collection.children.link(project)
        site = bpy.data.collections.new('IfcSite/My Site')
        project.children.link(site)
        building = bpy.data.collections.new('IfcBuilding/My Building')
        site.children.link(building)
        building_storey = bpy.data.collections.new('IfcBuildingStorey/Ground Floor')
        building.children.link(building_storey)
        return {'FINISHED'}

class AssignPset(bpy.types.Operator):
    bl_idname = 'bim.assign_pset'
    bl_label = 'Assign Pset'

    def execute(self, context):
        for object in bpy.context.selected_objects:
            index = object.BIMObjectProperties.psets.find(bpy.context.scene.BIMProperties.pset_name)
            if index >= 0:
                global_id = object.BIMObjectProperties.psets[index]
            else:
                global_id = object.BIMObjectProperties.psets.add()
            global_id.name = bpy.context.scene.BIMProperties.pset_name
            global_id.file = bpy.context.scene.BIMProperties.pset_file
        return {'FINISHED'}

class UnassignPset(bpy.types.Operator):
    bl_idname = 'bim.unassign_pset'
    bl_label = 'Unassign Pset'

    def execute(self, context):
        for object in bpy.context.selected_objects:
            index = object.BIMObjectProperties.psets.find(bpy.context.scene.BIMProperties.pset_name)
            if index != -1:
                object.BIMObjectProperties.psets.remove(index)
        return {'FINISHED'}

class AddPset(bpy.types.Operator):
    bl_idname = 'bim.add_pset'
    bl_label = 'Add Pset'

    # This is a temporary measure until we get a better UI
    def execute(self, context):
        bpy.context.active_object.BIMObjectProperties.psets.add()
        return {'FINISHED'}

class RemovePset(bpy.types.Operator):
    bl_idname = 'bim.remove_pset'
    bl_label = 'Remove Pset'
    pset_index: bpy.props.IntProperty()

    def execute(self, context):
        bpy.context.active_object.BIMObjectProperties.psets.remove(self.pset_index)
        return {'FINISHED'}

class GenerateGlobalId(bpy.types.Operator):
    bl_idname = 'bim.generate_global_id'
    bl_label = 'Generate GlobalId'

    def execute(self, context):
        index = bpy.context.active_object.BIMObjectProperties.attributes.find('GlobalId')
        if index >= 0:
            global_id = bpy.context.active_object.BIMObjectProperties.attributes[index]
        else:
            global_id = bpy.context.active_object.BIMObjectProperties.attributes.add()
        global_id.name = 'GlobalId'
        global_id.data_type = 'string'
        global_id.string_value = ifcopenshell.guid.new()
        return {'FINISHED'}

class AddAttribute(bpy.types.Operator):
    bl_idname = 'bim.add_attribute'
    bl_label = 'Add Attribute'

    def execute(self, context):
        if bpy.context.active_object.BIMObjectProperties.applicable_attributes:
            attribute = bpy.context.active_object.BIMObjectProperties.attributes.add()
            attribute.name = bpy.context.active_object.BIMObjectProperties.applicable_attributes
        return {'FINISHED'}

class RemoveAttribute(bpy.types.Operator):
    bl_idname = 'bim.remove_attribute'
    bl_label = 'Remove Attribute'
    attribute_index: bpy.props.IntProperty()

    def execute(self, context):
        bpy.context.active_object.BIMObjectProperties.attributes.remove(self.attribute_index)
        return {'FINISHED'}

class AssignSweptSolidProfile(bpy.types.Operator):
    bl_idname = 'bim.assign_swept_solid_profile'
    bl_label = 'Assign Profile'

    def execute(self, context):
        if bpy.context.mode != 'EDIT_MESH':
            return {'FINISHED'}
        for vg in bpy.context.active_object.vertex_groups:
            if vg.name == 'profile':
                bpy.ops.object.vertex_group_set_active(group=vg.name)
                bpy.ops.object.vertex_group_remove()
                break
        bpy.ops.object.vertex_group_assign_new()
        bpy.context.active_object.vertex_groups[bpy.context.active_object.vertex_groups[-1].name].name = 'profile'
        return {'FINISHED'}

class AssignSweptSolidExtrusion(bpy.types.Operator):
    bl_idname = 'bim.assign_swept_solid_extrusion'
    bl_label = 'Assign Extrusion'

    def execute(self, context):
        if bpy.context.mode != 'EDIT_MESH':
            return {'FINISHED'}
        for vg in bpy.context.active_object.vertex_groups:
            if vg.name == 'extrusion':
                bpy.ops.object.vertex_group_set_active(group=vg.name)
                bpy.ops.object.vertex_group_remove()
                break
        bpy.ops.object.vertex_group_assign_new()
        bpy.context.active_object.vertex_groups[bpy.context.active_object.vertex_groups[-1].name].name = 'extrusion'
        return {'FINISHED'}

class SelectExternalMaterialDir(bpy.types.Operator):
    bl_idname = "bim.select_external_material_dir"
    bl_label = "Select Material File"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        bpy.context.active_object.active_material.BIMMaterialProperties.location = self.filepath
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class SelectDataDir(bpy.types.Operator):
    bl_idname = "bim.select_data_dir"
    bl_label = "Select Data Directory"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        bpy.context.scene.BIMProperties.data_dir = self.filepath
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class SelectSchemaDir(bpy.types.Operator):
    bl_idname = "bim.select_schema_dir"
    bl_label = "Select Schema Directory"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        bpy.context.scene.BIMProperties.schema_dir = self.filepath
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}