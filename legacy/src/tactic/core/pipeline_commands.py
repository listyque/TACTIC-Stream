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

"""Original workflow save command, moved out of its visual editor.
Advanced process-property commands remain lazy legacy dependencies.
"""
from pyasm.command import Command
from pyasm.common import jsonloads
from pyasm.search import Search, SearchType, SearchKey, SObject
from pyasm.biz import Pipeline
from tactic_client_lib import TacticServerStub

class PipelineSaveCbk(Command):
    '''Callback executed when the Save button or other Save menu items are pressed in Project Workflow'''
    def get_title(self):
        return "Save a pipeline"

    def execute(self):
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
            pipeline_xml = pipeline_xml.replace("&", "&amp;")
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
                except:
                    process_name = xml.get_attribute(node, "name")
                    print("WARNING: Setting for process %s not saved." % process_name )

            settings_list.append(settings)

            xml.del_attribute(node, "settings")

        pipeline_xml = xml.to_string()
        server = TacticServerStub.get(protocol='local')
        data =  {'pipeline':pipeline_xml, 'color':pipeline_color}
        if pipeline_name:
            data['name'] = pipeline_name
        if pipeline_desc:
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


        self.check_duplicates(process_nodes, xml)

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

            node_type = xml.get_attribute(node, "type")

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
                kwargs = node_kwargs.get(process_name.replace(" ", "%20")) or {}
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



    def check_duplicates(self, nodes, xml):
        process_set = set()

        for node in nodes:
            process_name = xml.get_attribute(node, "name")
            if process_name in process_set:
                raise ValueError('The workflow cannot have duplicate process names.')
            else:
                process_set.add(process_name)

