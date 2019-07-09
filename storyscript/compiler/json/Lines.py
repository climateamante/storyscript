# -*- coding: utf-8 -*-
from storyscript.exceptions import StorySyntaxError


class Lines:
    """
    Holds compiled lines and provides methods for operation on lines.
    """
    def __init__(self, story):
        self.story = story
        self.lines = {}
        self._lines = []  # sorted line nr (by insertion)
        self.variables = []
        self.services = []
        self.functions = {}
        self.output_scopes = {}
        self.finished_scopes = []

    def entrypoint(self):
        """
        Returns the first line number or None
        """
        # empty files are allowed
        if len(self._lines) == 0:
            return None
        return self._lines[0]

    def first(self):
        """
        Gets the first line.
        """
        if len(self._lines) == 0:
            return None
        return self.lines[self._lines[0]]

    def last(self):
        """
        Gets the last line
        """
        if len(self._lines) == 0:
            return None
        return self.lines[self._lines[-1]]

    def set_name(self, name):
        """
        Sets the name of the previous line
        """
        previous_line = self.last()
        if previous_line is not None:
            previous_line['name'] = name

        self.variables.append(name)

    def set_next(self, line_number):
        """
        Finds the previous line, and set the current as its next line
        """
        previous_line = self.last()
        if previous_line is not None:
            previous_line['next'] = line_number

    def set_exit(self, line):
        """
        Sets the current line as the exit line for a previous one, as needed
        in if/elif/else and try/catch/finally blocks.
        """
        methods = ['if', 'elif', 'try', 'catch']
        for line_number in self._lines[::-1]:
            if self.lines[line_number]['method'] in methods:
                self.finished_scopes = []
                self.lines[line_number]['exit'] = line
                break

    def set_scope(self, line, parent, output=[]):
        """
        Keeps track of output scopes so that defined outputs are recognized for
        nested children.
        """
        self.output_scopes[line] = {'parent': parent, 'output': output}

    def finish_scope(self, line):
        """
        Finishes an output scope and prepares 'exit' adjustment for the scope
        when the next line gets added.
        """
        self.finished_scopes.append(line)

    def is_output(self, parent, service):
        """
        Checks whether a service has been defined as output for this block
        or for its parents.
        """
        if parent in self.output_scopes:
            scope = self.output_scopes[parent]
            if service in scope['output']:
                return True
            if scope['parent']:
                assert scope['parent'] != parent
                return self.is_output(scope['parent'], service)
        return False

    def make(self, method, line, name=None, args=None, service=None,
             command=None, function=None, output=None, enter=None, exit=None,
             parent=None):
        """
        Creates the base dictionary for a given line.
        """
        assert line not in self.lines, 'Line numbers must be unique'
        raw_line = self.story.line(line)
        self.lines[line] = {
            'method': method,
            'ln': line,
            'output': output,
            'name': name,
            'service': service,
            'command': command,
            'function': function,
            'args': args,
            'enter': enter,
            'exit': exit,
            'parent': parent,
            'src': raw_line,
        }
        # save insertion order
        self._lines.append(line)

    def check_service_name(self, service, line):
        """
        Checks whether a service name is valid
        """
        if '.' in service:
            raise StorySyntaxError('service_name')

    def append(self, method, line, **kwargs):
        for scope in self.finished_scopes:
            self.lines[scope]['exit'] = line
        self.finished_scopes = []
        if 'service' in kwargs:
            self.check_service_name(kwargs['service'], line)

        if method == 'function':
            self.functions[kwargs['function']] = line
        elif method == 'execute':
            if self.is_output(kwargs['parent'], kwargs['service']) is False:
                self.services.append(kwargs['service'])
        self.set_next(line)
        self.make(method, line, **kwargs)

    def execute(self, line, service, command, arguments, output, enter,
                parent):
        kwargs = {'service': service, 'command': command, 'args': arguments,
                  'output': output, 'enter': enter, 'parent': parent}
        self.append('execute', line, **kwargs)

    def get_services(self):
        """
        Get the services and remove duplicates.
        """
        return list(sorted(set(self.services)))

    def is_variable_defined(self, variable_name):
        """
        Checks whether a variable has been defined so far
        """
        for vs in self.variables:
            if variable_name in vs:
                return True
        return False
