from pathlib import Path
import sys


def run_snapshot_case(case):
    scripts = str(Path(__file__).resolve().parents[1] / 'tests/scripts')
    sys.path.insert(0, scripts)
    try:
        if case.get('method') == 'html_api_contract':
            import html_api_contract
            return html_api_contract.run(case)
        if case.get('method') == 'cross_project_undo_contract':
            import cross_project_undo_contract
            return cross_project_undo_contract.run(case)
        if case.get('method') == 'workflow_undo_contract':
            import workflow_undo_contract
            return workflow_undo_contract.run(case)
        if case.get('method') == 'workflow_project_contract':
            import workflow_project_contract
            return workflow_project_contract.run(case)
        if case.get('method') == 'user_workflow_contract':
            import user_workflow_contract
            return user_workflow_contract.run(case)
        if case.get('method') == 'user_status_contract':
            import user_status_contract
            return user_status_contract.run(case)
        if case.get('method') == 'compound_form_contract':
            import compound_form_contract
            return compound_form_contract.run(case)
        if case.get('method') == 'upload_form_contract':
            import upload_form_contract
            return upload_form_contract.run(case)
        if case.get('method') == 'workflow_form_contract':
            import workflow_form_contract
            return workflow_form_contract.run(case)
        if case.get('method') == 'calendar_form_contract':
            import calendar_form_contract
            return calendar_form_contract.run(case)
        if case.get('method') == 'edit_form_contract':
            import edit_form_contract
            return edit_form_contract.run(case)
        if case.get('method') == 'schema_template_contract':
            import schema_template_contract
            return schema_template_contract.run(case)
        if case.get('method') == 'schema_edit_contract':
            import schema_edit_contract
            return schema_edit_contract.run(case)
        if case.get('method') == 'collection_commands_contract':
            import collection_commands_contract
            return collection_commands_contract.run(case)
        if case.get('method') == 'collection_contract':
            import collection_contract
            return collection_contract.run(case)
        if case.get('method') == 'task_status_contract':
            import task_status_contract
            return task_status_contract.run(case)
        if case.get('method') == 'task_schedule_contract':
            import task_schedule_contract
            return task_schedule_contract.run(case)
        if case.get('method') == 'workflow_packages_contract':
            import workflow_packages_contract
            return workflow_packages_contract.run(case)
        if case.get('method') == 'process_type_contract':
            import process_type_contract
            return process_type_contract.run(case)
        if case.get('method') == 'process_delete_contract':
            import process_delete_contract
            return process_delete_contract.run(case)
        if case.get('method') == 'same_object_contract':
            import same_object_contract
            return same_object_contract.run(case)
        if case.get('method') == 'pipeline_versions_contract':
            import pipeline_versions_contract
            return pipeline_versions_contract.run(case)
        if case.get('method') == 'process_commands_contract':
            import process_commands_contract
            return process_commands_contract.run(case)
        if case.get('method') == 'dependency_contract':
            import dependency_contract
            return dependency_contract.run(case)
        if case.get('method') == 'workflow_nodes_contract':
            import workflow_nodes_contract
            return workflow_nodes_contract.run(case)
        if case.get('method') == 'directory_contract':
            import directory_contract
            return directory_contract.run(case)
        if case.get('method') == 'ingestion_contract':
            import ingestion_contract
            return ingestion_contract.run(case)
        if case.get('method') == 'command_listener_contract':
            import command_listener_contract
            return command_listener_contract.run(case)
        if case.get('method') == 'handoff_contract':
            import handoff_contract
            return handoff_contract.run(case)
        if case.get('method') == 'metadata_checkin_contract':
            import metadata_checkin_contract
            try:
                return metadata_checkin_contract.run(case)
            except Exception as error:
                if not case.get('hook'):
                    raise
                return {'error': type(error).__name__, 'message': str(error)}
        if case.get('method') == 'search_join_contract':
            import search_join_contract
            return search_join_contract.run(case)
        if case.get('method') == 'transaction_state_contract':
            import transaction_state_contract
            return transaction_state_contract.run(case)
        if case.get('method') == 'undo_contract':
            import undo_contract
            try:
                return undo_contract.run(case)
            except Exception as error:
                # Preserve observable original failures as comparison data.
                return {'error': type(error).__name__, 'message': str(error)}
        if case.get('method') == 'local_sobjects_contract':
            import local_sobjects_contract
            return local_sobjects_contract.run(case)
        if case.get('method') == 'widget_config_contract':
            import widget_config_contract
            return widget_config_contract.run(case)
        if case.get('method') == 'diagnostic_contract':
            import diagnostic_contract
            return diagnostic_contract.run(case)
        if case.get('method') == 'queue_contract':
            import queue_contract
            return queue_contract.run(case)
        if case.get('method') == 'command_api_contract':
            import command_api_contract
            return command_api_contract.run(case)
        if case.get('method') == 'config_api_contract':
            import config_api_contract
            return config_api_contract.run(case)
        if case.get('method') == 'template_export_contract':
            import template_export_contract
            return template_export_contract.run(case)
        if case.get('method') == 'template_check_contract':
            import template_check_contract
            return template_check_contract.run(case)
        if case.get('method') == 'uninstall_contract':
            import uninstall_contract
            return uninstall_contract.run(case)
        if case.get('method') == 'export_contract':
            import export_contract
            return export_contract.run(case)
        if case.get('method') == 'config_contract':
            import config_contract
            return config_contract.run(case)
        if case.get('method') == 'plugin_contract':
            import plugin_contract
            return plugin_contract.run(case)
        if case.get('method') == 'project_write_contract':
            import project_write_contract
            return project_write_contract.run(case)
        if case.get('method') == 'schema_api_contract':
            import schema_api_contract
            return schema_api_contract.run(case)
        if case.get('method') == 'self_instance_contract':
            import self_instance_contract
            return self_instance_contract.run(case)
        if case.get('method') == 'project_write_contract':
            import project_write_contract
            return project_write_contract.run(case)
        if case.get('method') == 'schema_replay_contract':
            import schema_replay_contract
            return schema_replay_contract.run(case)
        if case.get('method') == 'rest_contract':
            import rest_contract
            return rest_contract.run(case)
        if case.get('method') == 'workflow_api_contract':
            import workflow_api_contract
            return workflow_api_contract.run(case)
        if case.get('method') == 'file_api_contract':
            import file_api_contract
            return file_api_contract.run(case)
        if case.get('method') == 'snapshot_levels_contract':
            import snapshot_levels_contract
            return snapshot_levels_contract.run(case)
        if case.get('method') == 'batch_api_contract':
            import batch_api_contract
            return batch_api_contract.run(case)
        if case.get('method') == 'icon_contract':
            import icon_contract
            return icon_contract.run(case)
        if case.get('method') == 'upload_checkin_contract':
            import upload_checkin_contract
            return upload_checkin_contract.run(case)
        if case.get('method') == 'preallocation_contract':
            import preallocation_contract
            return preallocation_contract.run(case)
        if case.get('method') == 'append_group_contract':
            import append_group_contract
            return append_group_contract.run(case)
        if case.get('method') == 'delete_contract':
            import delete_contract
            return delete_contract.run(case)
        if case.get('method') == 'versionless_contract':
            import versionless_contract
            return versionless_contract.run(case)
        if case.get('method') == 'checkin_contract':
            import checkin_contract
            return checkin_contract.run(case)
        if case.get('method') == 'repository_contract':
            import repository_contract
            return repository_contract.run(case)
        if case.get('method') == 'file_contract':
            import file_contract
            return file_contract.run(case)
        if case.get('method') == 'expression_write_contract':
            import expression_write_contract
            return expression_write_contract.run(case)
        if case.get('method') == 'expression_contract':
            import expression_contract
            return expression_contract.run(case)
        if case.get('method') == 'naming_contract':
            import naming_contract
            return naming_contract.run(case)
        if case.get('method') == 'snapshot_write_contract':
            import snapshot_write_contract
            return snapshot_write_contract.run(case)
        import snapshot_contract
        return snapshot_contract.run(case)
    finally:
        sys.path.remove(scripts)
