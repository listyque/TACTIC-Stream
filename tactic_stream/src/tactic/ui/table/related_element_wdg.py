"""Native related-record join selection from the original RelatedElementWdg."""

from pyasm.search import Search
from tactic.ui.common import BaseTableElementWdg


class RelatedElementWdg(BaseTableElementWdg):
    def preprocess(self):
        self.data = self.get_data()

    def get_cell_value(self):
        result = self.data.get(self.get_current_sobject().get_id())
        if not result:
            return {"text": ""}
        expression = self.get_option("expression")
        value = (
            Search.eval(expression, result)
            if expression
            else result.get_value(
                self.get_option("column") or self.get_name(), no_exception=True
            )
        )
        return {"text": "" if value is None else str(value)}

    def get_data(self):
        """
        <element name='work_location' title='Originating Site'>
          <display class='tactic.ui.table.ExpressionElementWdg'>
            <expression>@GET(MMS/work_location.location)</expression>
            <alt_expression>@GET(MMS/work_location.id)</alt_expression>
            <order_by>work_location.location</order_by>
          </display>
        </element>
        """

        data = {}

        sobjects = self.sobjects
        if not sobjects:
            return data

        # template = "MMS/subtask.MMS/job.MMS/request.MMS/security_classification"
        template = self.get_option("template")
        keys = template.split(".")

        # get the sobjects (main search)
        search_type_obj = sobjects[0].get_search_type_obj()
        join_table = search_type_obj.get_table()
        search_type = search_type_obj.get_value("search_type")

        if keys[0] != search_type:
            keys.insert(0, search_type)

        search_ids = []
        for sobject in sobjects:
            search_id = sobject.get_id()
            search_ids.append(search_id)

        keys.reverse()

        # create main search
        search = Search(keys[0])
        table = search.get_table()

        # add the columns
        search.add_column("*", table=table)

        current_key = None
        for i in range(1, len(keys)):
            key = keys[i]
            namespace, table = key.split("/")
            search.add_join(key, current_key)

            current_key = key

        # The migrated Search validates column ownership when it is projected.
        search.add_column("id", table=join_table, as_column="%s_id" % join_table)
        search.add_filters("id", search_ids, table=table)
        search.set_show_retired(True)

        results = search.get_sobjects()

        # make into a dictionary based on search id
        for result in results:
            id = result.get_value("%s_id" % join_table)
            data[id] = result

        return data
