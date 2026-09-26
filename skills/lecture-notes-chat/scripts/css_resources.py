"""Shared local CSS reference parser for renderer and publication ZIPs."""
def css_resources(text):
    import tinycss2
    def walk(tokens):
        for token in tokens:
            if token.type == 'url':
                yield token.value
            elif token.type == 'function' and token.lower_name == 'url':
                values = [t for t in token.arguments if t.type not in ('whitespace', 'comment')]
                if len(values) != 1 or values[0].type != 'string':
                    raise ValueError('Malformed CSS url()')
                yield values[0].value
            elif hasattr(token, 'content') and token.content is not None:
                yield from walk(token.content)
            elif hasattr(token, 'arguments'):
                yield from walk(token.arguments)
    rules = tinycss2.parse_stylesheet(text, skip_comments=True, skip_whitespace=True)
    for rule in rules:
        if rule.type == 'at-rule' and rule.lower_at_keyword == 'import':
            values = [t for t in rule.prelude if t.type not in ('whitespace', 'comment')]
            if values and values[0].type == 'string':
                yield values[0].value
        yield from walk(getattr(rule, 'prelude', []))
        yield from walk(getattr(rule, 'content', None) or [])
    # Inline declarations also appear as parser error tokens; scan their components.
    yield from walk(tinycss2.parse_component_value_list(text))

