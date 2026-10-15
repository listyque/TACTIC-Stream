"""The same native HTML operations in both kernels; no source monkey-patches."""
def run(case):
    from pyasm.web import HtmlElement, DivWdg, Table, Palette, WebContainer
    from tactic.ui.common import BaseRefreshWdg
    from pyasm.common import Common
    WebContainer.get_buffer()
    class NativeWdg(BaseRefreshWdg):
        def get_display(self):
            div = DivWdg()
            div.add_style('color', Palette.get().color('color'))
            div.add(HtmlElement('span', child=self.kwargs['text']))
            return div
    results = {}
    for palette in ('DEFAULT', 'DARK', 'LIGHT'):
        Palette.push_palette(palette)
        results[palette] = NativeWdg(text='Hello Тест').get_buffer_display()
        Palette.pop_palette()
    table = Table()
    table.add_row()
    table.add_cell('one')
    table.add_cell('two').add_attr('data-key', 'A')
    results['table'] = table.get_buffer_display()
    results['empty_span'] = HtmlElement('span').get_buffer_display()
    results['color'] = Common.modify_color('#123456', 10)
    results['buffers'] = WebContainer.get_num_buffers()
    return results
