// Shared native EditWdg input resolution for forms and table cells.
export function fieldKind(field) {
      if (field.class_name === 'tactic.ui.input.color_input_wdg.ColorInputWdg') return 'ColorInputWdg'
      if (field.class_name === 'tactic.ui.input.task_input_wdg.TaskSObjectInputWdg') return 'ParentInput'
      if (field.class_name === 'tactic.ui.widget.upload_wdg.SimpleUploadWdg') return 'FileInput'
      if (field.class_name === 'pyasm.widget.input_wdg.UploadWdg') return 'MultiUpload'
      if (field.class_name === 'tactic.ui.widget.upload_wdg.UploadWdg') return 'MultiUpload'
      if (field.class_name === 'tactic.ui.widget.calendar_wdg.CalendarInputWdg') return 'CalendarInputWdg'
      if (field.class_name === 'tactic.ui.widget.calendar_wdg.TimeInputWdg') return 'TimeInputWdg'
      const selectors = ['tactic.ui.input.pipeline_input_wdg.PipelineInputWdg',
        'tactic.ui.input.project_user_select_wdg.ProjectSelectWdg',
        'tactic.ui.input.process_context_wdg.ProcessInputWdg', 'tactic.ui.input.process_context_wdg.ReviewProcessInputWdg',
        'tactic.ui.input.search_type_input_wdg.SearchTypeInputWdg', 'tactic.ui.input.search_type_input_wdg.SearchTypeWithPipelineInputWdg',
        'tactic.ui.input.process_group_select_wdg.ProcessGroupSelectWdg', 'tactic.ui.widget.misc_input_wdg.TaskStatusSelectWdg']
      if (selectors.includes(field.class_name)) return field.input?.type === 'select' ? 'SelectWdg' : field.input?.type === 'text' ? 'TextWdg' : null
      if (field.class_name === 'tactic.ui.input.process_context_wdg.SubContextInputWdg') return 'TextWdg'
      const classes = ['TextWdg', 'TextAreaWdg', 'CheckboxWdg', 'SelectWdg', 'MultiSelectWdg', 'HiddenWdg', 'ThumbInputWdg']
      return classes.find(name => field.class_name === `pyasm.widget.input_wdg.${name}`)
    }

export function unsupportedField(field) {
        const options = field.options
        const allowed = ['hint', 'hint_text', 'default', 'value', 'column', 'read_only', 'required', 'size', 'rows', 'cols', 'parent_key',
          'values', 'labels', 'query', 'query_filter', 'query_limit', 'values_expr', 'labels_expr',
          'mode_expr', 'setting', 'extra_values', 'extra_labels', 'empty', 'empty_label', 'persist']
        if (fieldKind(field) === 'CalendarInputWdg') allowed.push('show_time', 'show_activator', 'display_mode')
        if (fieldKind(field) === 'TimeInputWdg') allowed.push('time')
        // The inherited color definition uses this value binding for its swatch.
        if (fieldKind(field) === 'ColorInputWdg') allowed.push('start_color', 'css_background')
        if (field.class_name === 'tactic.ui.input.pipeline_input_wdg.PipelineInputWdg') allowed.push('use_code')
        if (field.class_name === 'tactic.ui.input.process_context_wdg.ProcessInputWdg') allowed.push('context')
        if (field.class_name === 'tactic.ui.input.process_context_wdg.ReviewProcessInputWdg') allowed.push('context', 'pipeline_code')
        if (field.class_name === 'tactic.ui.input.process_group_select_wdg.ProcessGroupSelectWdg') allowed.push('label_attr')
        if (fieldKind(field) === 'FileInput') allowed.push('context', 'client_action')
        if (fieldKind(field) === 'MultiUpload') allowed.push('names', 'upload_type', 'context', 'pipeline', 'context_option', 'subcontext')
        if (field.class_name === 'tactic.ui.widget.upload_wdg.UploadWdg') allowed.push('context_expr', 'client_action')
        const multiActions = ['MultiUploadAction', 'pyasm.command.MultiUploadAction', 'pyasm.command.edit_wdg_action.MultiUploadAction',
          'MultiZipUploadAction', 'pyasm.command.MultiZipUploadAction', 'pyasm.command.edit_wdg_action.MultiZipUploadAction']
        const uploadActions = ['UploadAction', 'pyasm.command.UploadAction', 'pyasm.command.edit_wdg_action.UploadAction']
        const nullActions = ['', 'NullAction', 'pyasm.command.NullAction', 'pyasm.command.edit_wdg_action.NullAction']
        return !fieldKind(field) || (field.values.length > 1 && fieldKind(field) !== 'MultiSelectWdg') ||
          field.values.some(value => value !== null && typeof value === 'object') ||
          Object.keys(options).some(key => !allowed.includes(key)) ||
          (fieldKind(field) === 'CheckboxWdg' && options.value) ||
          (fieldKind(field) === 'ColorInputWdg' && options.css_background && options.css_background !== '{$VALUE}') ||
          (fieldKind(field) === 'CalendarInputWdg' && field.input?.display_mode !== 'browser') ||
          (fieldKind(field) === 'ThumbInputWdg' && !nullActions.includes(field.action.handler || '')) ||
          (['TimeAction', 'pyasm.command.TimeAction', 'pyasm.command.edit_wdg_action.TimeAction'].includes(field.action.handler) && fieldKind(field) !== 'TimeInputWdg') ||
          (fieldKind(field) === 'FileInput' && (!uploadActions.includes(field.action.handler || '') || options.client_action)) ||
          (fieldKind(field) === 'MultiUpload' && (field.class_name === 'tactic.ui.widget.upload_wdg.UploadWdg'
            ? (![...uploadActions, ...multiActions, ...nullActions].includes(field.action.handler || '') || options.client_action || options.upload_type ||
              (options.names && ![...multiActions, ...nullActions].includes(field.action.handler || '')) ||
              field.input.fields.map(item => item.name).join('|') !== (field.action.options.names || options.names || field.name))
            : (![...multiActions, ...nullActions].includes(field.action.handler || '') ||
              field.input.arbitrary !== (field.action.options.upload_type === 'arbitrary') || (field.input.arbitrary && field.input.fields.length !== 1) ||
              (!field.input.arbitrary && field.input.fields.map(item => item.name).join('|') !== (field.action.options.names || field.name))))) ||
          (fieldKind(field) === 'MultiSelectWdg' && !['MultiDatabaseAction', 'pyasm.command.MultiDatabaseAction', 'pyasm.command.edit_wdg_action.MultiDatabaseAction'].includes(field.action.handler)) ||
          (fieldKind(field) === 'TimeInputWdg' && !['TimeDatabaseAction', 'tactic.ui.widget.TimeDatabaseAction', 'tactic.ui.widget.calendar_wdg.TimeDatabaseAction',
            'TimeAction', 'pyasm.command.TimeAction', 'pyasm.command.edit_wdg_action.TimeAction'].includes(field.action.handler))

}
