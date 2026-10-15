###########################################################
#
# Copyright (c) 2005-2008, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

"""Original workflow save command with native process-property commands."""
from pyasm.command import Command
from pyasm.common.errors import UnsupportedContract
from tactic.command.python_cmd import check_script_execution
import re
from pyasm.common import jsonloads
from pyasm.search import Search, SearchType, SearchKey, SObject
from pyasm.biz import Pipeline
from tactic_client_lib import TacticServerStub

class PipelineSaveCbk(Command):
    '''Callback executed when the Save button or other Save menu items are pressed in Project Workflow'''
    def get_title(self):
        return "Save a pipeline"

    def execute(self):
        check_script_execution()
        pipeline_sk = self.kwargs.get('search_key')

        pipeline_xml = self.kwargs.get('pipeline')
        pipeline_name = self.kwargs.get('name')
        pipeline_color = self.kwargs.get('color')
        pipeline_desc = self.kwargs.get('description')
        project_code = self.kwargs.get('project_code')
        timestamp = self.kwargs.get("timestamp")

        default_template = self.kwargs.get("default_template")
        pipeline_data = self.kwargs.get("pipeline_data") or {}

        from pyasm.common import Xml
        xml = Xml()
        if not self.kwargs.get("xml_is_escaped"):
            pipeline_xml = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)", "&amp;", pipeline_xml)
        xml.read_string(pipeline_xml)
        process_nodes = xml.get_nodes("pipeline/process")
        settings_list = []

        for node in process_nodes:
            settings_str = xml.get_attribute(node, "settings")

            settings = {}
            if settings_str:
                try:
                    settings = jsonloads(settings_str)
                    if isinstance(settings, str):
                        settings = jsonloads(settings)
                except (ValueError, TypeError) as error:
                    raise ValueError("Invalid settings for process [%s]" % xml.get_attribute(node, "name")) from error
                if not isinstance(settings, dict):
                    raise ValueError("Process settings must be a dictionary")

            settings_list.append(settings)

            xml.del_attribute(node, "settings")

        self.check_duplicates(process_nodes, xml)
        for node in process_nodes:
            code = xml.get_attribute(node, "process_code")
            if code:
                existing = Search.get_by_code("config/process", code)
                owner = SearchKey.get_by_search_key(pipeline_sk)
                if existing is None or owner is None or existing.get_value("pipeline_code") != owner.get_code():
                    raise ValueError("Process code does not belong to this pipeline: %s" % code)
                if existing.get_value('process') != xml.get_attribute(node, 'name'):
                    raise UnsupportedContract('Renaming a process requires migrating its tasks and references')
        pipeline_xml = xml.to_string()
        server = TacticServerStub.get(protocol='local')
        data = {'pipeline': pipeline_xml}
        if pipeline_color is not None:
            data['color'] = pipeline_color
        if pipeline_name:
            data['name'] = pipeline_name
        if pipeline_desc is not None:
            data['description'] = pipeline_desc
        if project_code:
            # force a pipeline to become site-wide
            if project_code == '__SITE_WIDE__':
                project_code = ''
            data['project_code'] = project_code
        if timestamp:
            data['timestamp'] = timestamp

        if SearchType.column_exists("sthpw/pipeline", "data"):
            data['data'] = pipeline_data

        server.insert_update(pipeline_sk, data = data)

        Pipeline.clear_cache(search_key=pipeline_sk)
        pipeline = SearchKey.get_by_search_key(pipeline_sk)
        pipeline_code = pipeline.get_code()

        # make sure to update process table
        """
        process_names = pipeline.get_process_names()
        search = Search("config/process")
        search.add_filter("pipeline_code", pipeline_code)
        process_sobjs = search.get_sobjects()
        existing_names = SObject.get_values(process_sobjs, 'process')
        """

        pipeline.update_dependencies()


        self.description = "Updated workflow [%s]" % pipeline_code

        node_kwargs = self.kwargs.get("node_kwargs") or {}


        default_workflow = {
            'version': 2
        }


        for i in range(len(process_nodes)):
            node = process_nodes[i]

            process = None
            process_code = xml.get_attribute(node, "process_code")
            process_name = xml.get_attribute(node, "name")

            if process_code:
                process = Search.get_by_code("config/process", process_code)


            # try to find it by name
            if not process:
                search = Search("config/process")
                search.add_filter("process", process_name)
                search.add_filter("pipeline_code", pipeline_code)
                process = search.get_sobject()


            # else create a new one
            if not process:
                process = SearchType.create("config/process")
                process.set_value("process", process_name)
                process.set_value("pipeline_code", pipeline_code)
                process.set_json_value("workflow", default_workflow)

            # set the process code
            xml.set_attribute(node, "process_code", process.get_code())

            curr_settings = settings_list[i]

            subpipeline_code = None
            if curr_settings:
                subpipeline_code = curr_settings.pop("subpipeline_code", None)
            if subpipeline_code or subpipeline_code == "":
                process.set_value("subpipeline_code", subpipeline_code)

            node_type = pipeline.get_process(process_name).get_type()

            if curr_settings:
                workflow = process.get_json_value("workflow", default=default_workflow)

                # On change of node type, clear the workflow data
                orig_node_type = workflow.get("node_type")
                if orig_node_type and orig_node_type != node_type:
                    workflow = curr_settings
                else:
                    workflow.update(curr_settings)
                workflow['node_type'] = node_type
                process.set_value("workflow", workflow)

            process.commit()

            if node_type:
                kwargs = dict(node_kwargs.get(process_name.replace(" ", "%20")) or {})
                if len(kwargs) > 0:
                    kwargs['process'] = process_name
                    kwargs['node_type'] = node_type
                    kwargs['pipeline_code'] = pipeline_code

                    version_str = kwargs.get('version') or 2
                    version = int(version_str)

                    if version == 1:
                        from tactic.core.process_commands import ProcessInfoCmd
                        cmd = ProcessInfoCmd(**kwargs)
                        cmd.execute()
                    elif version == 2:
                        from tactic.core.process_commands import NewProcessInfoCmd
                        cmd = NewProcessInfoCmd(**kwargs)
                        cmd.execute()
                    else:
                        raise ValueError("Unsupported process settings version: %s" % version)

        # update_dependencies may have applied template attributes to the graph.
        saved_xml = pipeline.get_pipeline_xml()
        for node in saved_xml.get_nodes('pipeline/process'):
            name = saved_xml.get_attribute(node, 'name')
            process = pipeline.get_process_sobject(name)
            saved_xml.set_attribute(node, 'process_code', process.get_code())
        pipeline.set_value('pipeline', saved_xml.to_string())
        pipeline.commit()

    def check_duplicates(self, nodes, xml):
        process_set = set()

        for node in nodes:
            process_name = xml.get_attribute(node, "name")
            if process_name in process_set:
                raise ValueError('The workflow cannot have duplicate process names.')
            else:
                process_set.add(process_name)


class PipelinePropertyCbk(Command):
    def execute(self):
        check_script_execution()
        if self.kwargs.get('version') == 2:
            return
        search = Search('config/process')
        search.add_filter('pipeline_code', self.kwargs.get('pipeline_code'))
        search.add_filter('process', self.kwargs.get('process'))
        process_sobj = search.get_sobject()
        if process_sobj is None:
            raise LookupError('Process does not exist in the specified pipeline')
        workflow = process_sobj.get_json_value('workflow') or {}
        for name, value in self.kwargs.items():
            workflow[name] = value
        process_sobj.set_json_value('workflow', workflow)
        process_sobj.commit()


class PipelineSaveCmd(Command):
    def execute(self):
        check_script_execution()
        pipeline = SearchType.create('sthpw/pipeline')
        pipeline.set_value('name', self.kwargs.get('name'))
        pipeline.set_value('category', self.kwargs.get('category'))
        pipeline.commit()
        self.info['search_key'] = pipeline.get_search_key()

